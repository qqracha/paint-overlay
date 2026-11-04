import os
import atexit
import sys
import tempfile
import unittest
from pathlib import Path

sandbox = tempfile.TemporaryDirectory()
atexit.register(sandbox.cleanup)
os.environ['LOCALAPPDATA'] = sandbox.name
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import paint_overlay as m

class BaseOverlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = m.W.QApplication.instance() or m.W.QApplication([])
        cls.app = m.App()
        cls.app.timer.stop()
    @classmethod
    def tearDownClass(cls):
        cls.app.tray.hide()
        for key in range(712,725):m.u.UnregisterHotKey(None,key)
        for widget in (cls.app.panel,cls.app.dock,cls.app.overlay):widget.close()
    def setUp(self):
        self.app.overlay.clear()
        self.app.overlay.history=[]
        self.app.overlay.future=[]
        self.app.overlay.selection=None
        self.app.cfg['color']='#ff3434'
        self.app.shape_filled=False
        self.app.moving=False

class OverlayTests(BaseOverlay):
    def test_undo_redo_and_partial_eraser(self):
        o=self.app.overlay
        o.checkpoint(); o.segment(m.C.QPointF(50,50),m.C.QPointF(100,50),'red',8)
        o.checkpoint(); o.segment(m.C.QPointF(75,40),m.C.QPointF(75,60),'white',12,True)
        self.assertEqual(o.image.pixelColor(75,50).alpha(),0)
        self.assertGreater(o.image.pixelColor(55,50).alpha(),0)
        o.undo(); self.assertGreater(o.image.pixelColor(75,50).alpha(),0)
        o.redo(); self.assertEqual(o.image.pixelColor(75,50).alpha(),0)
    def test_bounded_fill_and_clipboard(self):
        a=self.app; a.drawing_tool='rect'; a.shape(m.C.QPointF(40,40),m.C.QPointF(100,100),False)
        a.bucket(m.C.QPointF(70,70))
        self.assertEqual(a.overlay.image.pixelColor(70,70).name(),'#ff3434')
        self.assertEqual(a.overlay.image.pixelColor(20,20).alpha(),0)
        a.overlay.selection=m.C.QRectF(40,40,60,60)
        a.copy_selection()
        self.assertEqual(self.qt.clipboard().image().size(),m.C.QSize(60,60))
        a.copy_selection(True)
        self.assertEqual(a.overlay.image.pixelColor(70,70).alpha(),0)
        a.prepare_paste(); self.assertIsNotNone(a.overlay.selection)
    def test_shift_square_and_selection_delete(self):
        a=self.app; a.drawing_tool='rect'; a.shape(m.C.QPointF(30,30),m.C.QPointF(90,60),True)
        self.assertGreater(a.overlay.image.pixelColor(90,90).alpha(),0)
        a.overlay.selection=m.C.QRectF(20,20,100,100)
        a.delete_selection(); self.assertEqual(a.overlay.image.pixelColor(90,90).alpha(),0)
        a.undo(); self.assertGreater(a.overlay.image.pixelColor(90,90).alpha(),0)
    def test_native_ribbon_and_palette(self):
        a=self.app
        self.assertFalse(hasattr(a.dock,'background'))
        self.assertEqual(a.dock.height(),54)
        self.assertLess(a.dock.width(),900)
        self.assertEqual(len(a.panel.colors),6)
        self.assertTrue(all(s.orientation()==m.C.Qt.Horizontal for s in a.panel.sliders.values()))
        a.dock.tool_buttons['ellipse'].click()
        self.assertEqual(a.drawing_tool,'ellipse')
        self.assertTrue(a.dock.tool_buttons['ellipse'].isChecked())
    def test_history_hold_repeat(self):
        a=self.app; oldclock=a.history_clock; oldshield=a.overlay.shield
        class Clock:
            now=0
            def elapsed(self):return self.now
        clock=Clock(); a.history_clock=clock; a.overlay.shield=True; a.repeat_kind=None
        try:
            for i in range(5):
                a.overlay.checkpoint(); a.overlay.segment(m.C.QPointF(10+i*10,10),m.C.QPointF(10+i*10,20),'red',2)
            count=len(a.overlay.history)
            a.repeat_history('undo',True); self.assertEqual(len(a.overlay.history),count-1)
            clock.now=200; a.repeat_history('undo',True); self.assertEqual(len(a.overlay.history),count-1)
            clock.now=350; a.repeat_history('undo',True); self.assertEqual(len(a.overlay.history),count-2)
            a.repeat_history(None,False); a.repeat_history('redo',True); self.assertEqual(len(a.overlay.history),count-1)
        finally:a.history_clock=oldclock; a.overlay.shield=oldshield; a.repeat_kind=None

class PaintWorkflowTests(BaseOverlay):
    def tearDown(self):
        a=self.app
        if a.text_editor is not None:a.finish_text(False,refresh=False)
        a.cfg['shield']=False; a.overlay.shield=False; a.set_layer_shortcuts(False)
        a.gesture=None; a.previous=None; a.moving=False; a.last_draw_global=None
        a.dock.brush_popup.hide(); a.capture_toast.hide()
    def test_canvas_selection_move_resize_and_outside_click(self):
        a=self.app; a.overlay.clear(); a.gesture=None
        p=m.G.QPainter(a.overlay.image); p.fillRect(60,60,40,40,m.G.QColor('red')); p.end()
        a.select_tool('select'); before=len(a.overlay.history)
        a.canvas_input(m.C.QPointF(50,50),True); a.canvas_input(m.C.QPointF(110,110),True); a.canvas_input(m.C.QPointF(),False)
        self.assertEqual(len(a.overlay.history),before)
        a.canvas_input(m.C.QPointF(80,80),True); a.canvas_input(m.C.QPointF(180,80),True); a.canvas_input(m.C.QPointF(),False)
        self.assertEqual(a.overlay.image.pixelColor(80,80).alpha(),0)
        self.assertEqual(a.overlay.image.pixelColor(180,80).name(),'#ff0000')
        a.canvas_input(m.C.QPointF(210,80),True); a.canvas_input(m.C.QPointF(250,80),True); a.canvas_input(m.C.QPointF(),False)
        self.assertEqual(a.overlay.selection.width(),100)
        a.canvas_input(m.C.QPointF(10,180),True); a.canvas_input(m.C.QPointF(),False)
        self.assertIsNone(a.overlay.selection)
        self.assertGreater(a.overlay.image.pixelColor(180,80).alpha(),0)
    def test_paste_is_immediate_and_selected(self):
        a=self.app; image=m.G.QImage(16,12,m.G.QImage.Format_ARGB32_Premultiplied); image.fill(m.G.QColor('red'))
        self.qt.clipboard().setImage(image); a.prepare_paste()
        self.assertIsNotNone(a.overlay.selection)
        rect=a.overlay.selection.toAlignedRect()
        self.assertEqual(rect.size(),m.C.QSize(16,12))
        self.assertEqual(a.overlay.image.pixelColor(rect.center()).name(),'#ff0000')
        self.assertEqual(a.drawing_tool,'select')
    def test_nine_brushes_have_distinct_rendering(self):
        from brushes import BRUSHES, draw_segment
        renders=set()
        for kind,title in BRUSHES:
            image=m.G.QImage(120,80,m.G.QImage.Format_ARGB32_Premultiplied); image.fill(m.C.Qt.transparent)
            draw_segment(image,m.C.QPointF(20,20),m.C.QPointF(90,55),'#ff3434',12,kind)
            pixels=bytes(image.constBits()); self.assertTrue(any(pixels),title); renders.add(pixels)
        self.assertEqual(len(renders),9)
        a=self.app; a.dock.brush_popup.choose('marker')
        self.assertEqual(a.cfg['brush_kind'],'marker'); self.assertEqual(a.drawing_tool,'brush')
        a.cfg['brush_kind']='round'
    def test_tool_keys_and_editor_suspend_shortcuts(self):
        a=self.app; real=m.u
        class Keys:
            held=set()
            @staticmethod
            def GetAsyncKeyState(key):return 0x8000 if key in Keys.held else 0
        try:
            m.u=Keys; a.overlay.shield=True
            for vk,tool in ((0x42,'brush'),(0x45,'eraser'),(0x53,'select'),(0x54,'text')):
                Keys.held=set(); a.tick(); Keys.held={vk}; a.tick(); self.assertEqual(a.drawing_tool,tool)
        finally:m.u=real
        a.cfg['shield']=True; a.open_text(m.C.QPointF(30,40))
        self.assertFalse(a.layer_shortcuts_active)
        a.text_editor.edit.setPlainText('BES Текст')
        a.finish_text(True)
        self.assertIsNone(a.text_editor); self.assertTrue(a.layer_shortcuts_active)
        rect=a.overlay.selection.toAlignedRect()
        self.assertTrue(any(bytes(a.overlay.image.copy(rect).constBits())))
    def test_escape_cancels_text_without_leaving_layer(self):
        a=self.app; a.cfg['shield']=True; a.open_text(m.C.QPointF(30,40))
        a.text_editor.edit.setPlainText('Cancel'); a.text_editor.cancel_key.activated.emit()
        self.assertIsNone(a.text_editor)
        real=m.u; original_leave=a.leave_layer; exits=[]
        class Keys:
            @staticmethod
            def GetAsyncKeyState(key):return 0x8000 if key==0x1B else 0
        try:
            m.u=Keys; a.leave_layer=lambda:exits.append(True)
            a.tick(); self.assertFalse(exits); self.assertTrue(a.overlay.shield)
        finally:m.u=real; a.leave_layer=original_leave
    def test_toast_draws_readable_title_and_details(self):
        toast=self.app.capture_toast
        image=toast.grab().toImage()
        for area in (m.C.QRect(20,13,340,28),m.C.QRect(20,45,340,25)):
            dark=sum(1 for y in range(area.top(),area.bottom()) for x in range(area.left(),area.right()) if image.pixelColor(x,y).red()<90 and image.pixelColor(x,y).green()<110 and image.pixelColor(x,y).alpha()>100)
            self.assertGreater(dark,150)
    def test_hud_fits_smaller_displays(self):
        dock=self.app.dock
        try:
            dock.fit_to_screen(m.C.QRect(0,0,1024,768))
            self.assertLessEqual(dock.width(),992)
            self.assertEqual(dock.height(),54)
        finally:dock.fit_to_screen(m.C.QRect(0,0,1920,1080))
    def test_font_popup_does_not_commit_text_prematurely(self):
        a=self.app; a.cfg['shield']=True; a.open_text(m.C.QPointF(30,40)); editor=a.text_editor; a.editor_wait_release=False
        real=m.u; original_popup=m.W.QApplication.activePopupWidget; original_pos=m.G.QCursor.pos
        class Keys:
            @staticmethod
            def GetAsyncKeyState(key):return 0x8000 if key==1 else 0
        try:
            m.u=Keys; m.W.QApplication.activePopupWidget=lambda:editor
            m.G.QCursor.pos=lambda:m.C.QPoint(2000,2000)
            a.tick(); self.assertIs(a.text_editor,editor)
        finally:
            m.u=real; m.W.QApplication.activePopupWidget=original_popup; m.G.QCursor.pos=original_pos
            a.finish_text(False)
    def test_capture_is_single_monitor_at_native_resolution(self):
        a=self.app
        class Screen:
            def __init__(self,x,ratio):self.x=x; self.ratio=ratio
            def geometry(self):return m.C.QRect(self.x,0,400,400)
            def grabWindow(self,window):
                image=m.G.QImage(400*self.ratio,400*self.ratio,m.G.QImage.Format_ARGB32_Premultiplied); image.fill(m.G.QColor('#335577'))
                pix=m.G.QPixmap.fromImage(image); pix.setDevicePixelRatio(self.ratio); return pix
        first=Screen(0,1); second=Screen(400,2)
        p=m.G.QPainter(a.overlay.image); p.fillRect(440,40,30,30,m.G.QColor('red')); p.end()
        self.assertIs(a.choose_capture_screen([first,second],m.C.QPoint(450,50)),second)
        result=a.capture_screen_image(second)
        self.assertEqual(result.size(),m.C.QSize(800,800))
        self.assertEqual(result.pixelColor(100,100).name(),'#ff0000')
        self.assertEqual(a.capture_screen_image(first).pixelColor(50,50).name(),'#335577')
    def test_capture_copies_png_and_notifies(self):
        a=self.app; case=self
        probe=m.W.QWidget(None,m.C.Qt.Tool); probe.setFixedSize(60,40); probe.show()
        a.dock.show(); a.capture_toast.show()
        class Screen:
            def geometry(self):return m.C.QRect(0,0,400,400)
            def grabWindow(self,window):
                case.assertFalse(any(w.isVisible() for w in m.W.QApplication.topLevelWidgets()))
                pix=m.G.QPixmap(400,400); pix.fill(m.G.QColor('#335577')); return pix
        screen=Screen(); original_target=a.capture_target; original_notify=a.capture_toast.notify
        original_path=m.C.QStandardPaths.writableLocation; original_warning=m.W.QMessageBox.warning
        notifications=[]; errors=[]
        try:
            a.capture_target=lambda:screen; a.capture_toast.notify=lambda target:notifications.append(target)
            m.C.QStandardPaths.writableLocation=lambda location:sandbox.name
            m.W.QMessageBox.warning=lambda *args:errors.append(args)
            a.screenshot(); loop=m.C.QEventLoop(); m.C.QTimer.singleShot(600,loop.quit); loop.exec()
            self.assertFalse(errors); self.assertFalse(a.capturing)
            self.assertTrue(a.last_screenshot.exists()); self.assertEqual(self.qt.clipboard().image().size(),m.C.QSize(400,400)); self.assertEqual(notifications,[screen])
        finally:
            probe.close()
            a.capture_target=original_target; a.capture_toast.notify=original_notify
            m.C.QStandardPaths.writableLocation=original_path; m.W.QMessageBox.warning=original_warning
    def test_no_pointer_glow_and_aligned_active_tool(self):
        first=m.G.QImage(300,80,m.G.QImage.Format_ARGB32_Premultiplied); first.fill(m.C.Qt.transparent)
        second=first.copy()
        for image,point in ((first,m.C.QPointF(30,10)),(second,m.C.QPointF(260,60))):
            p=m.G.QPainter(image); m.paint_glass(p,image.rect(),point); p.end()
        self.assertEqual(bytes(first.constBits()),bytes(second.constBits()))
        image=self.app.dock.grab().toImage()
        self.assertGreater(image.pixelColor(image.width()//2,2).red(),230)

if __name__=='__main__':unittest.main()
