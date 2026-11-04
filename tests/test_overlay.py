import os
import sys
import tempfile
import unittest
from pathlib import Path

sandbox = tempfile.TemporaryDirectory()
os.environ['LOCALAPPDATA'] = sandbox.name
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import paint_overlay as m

class OverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = m.W.QApplication.instance() or m.W.QApplication([])
        cls.app = m.App()
        cls.app.timer.stop()
    @classmethod
    def tearDownClass(cls):
        cls.app.tray.hide()
        for key in range(712,720):m.u.UnregisterHotKey(None,key)
        for widget in (cls.app.panel,cls.app.dock,cls.app.overlay):widget.close()
        sandbox.cleanup()
    def setUp(self):
        self.app.overlay.clear()
        self.app.overlay.history=[]
        self.app.overlay.future=[]
        self.app.overlay.selection=None
        self.app.cfg['color']='#ff3434'
        self.app.shape_filled=False
        self.app.moving=False
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
        a.prepare_paste(); self.assertIsNotNone(a.paste_image)
    def test_shift_square_and_selection_delete(self):
        a=self.app; a.drawing_tool='rect'; a.shape(m.C.QPointF(30,30),m.C.QPointF(90,60),True)
        self.assertGreater(a.overlay.image.pixelColor(90,90).alpha(),0)
        a.overlay.selection=m.C.QRectF(20,20,100,100)
        a.delete_selection(); self.assertEqual(a.overlay.image.pixelColor(90,90).alpha(),0)
        a.undo(); self.assertGreater(a.overlay.image.pixelColor(90,90).alpha(),0)
    def test_native_ribbon_and_palette(self):
        a=self.app
        self.assertFalse(hasattr(a.dock,'background'))
        self.assertEqual(a.dock.size(),m.C.QSize(1080,77))
        self.assertEqual(len(a.panel.colors),6)
        self.assertTrue(all(s.orientation()==m.C.Qt.Horizontal for s in a.panel.sliders.values()))
        a.dock.tool_buttons['ellipse'].click()
        self.assertEqual(a.drawing_tool,'ellipse')
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

if __name__=='__main__':unittest.main()
