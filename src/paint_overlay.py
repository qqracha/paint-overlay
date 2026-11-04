import sys, ctypes, json, os, math
from PIL import Image, ImageDraw
from pathlib import Path
from brushes import BRUSHES, brush_icon, draw_segment as brush_segment
from PySide6 import QtCore as C, QtGui as G, QtWidgets as W

APP = 'Paint Overlay'
RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent)) / 'assets'
SETTINGS = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / APP / 'settings.json'
SETTINGS.parent.mkdir(parents=True, exist_ok=True)
legacy_settings=SETTINGS.parent.parent/'Just Pointer'/'settings.json'
if not SETTINGS.exists() and legacy_settings.exists():
    SETTINGS.write_text(legacy_settings.read_text())
u = ctypes.windll.user32
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass
COLORS = ['#ff3434', '#ffbd2e', '#43d886', '#44aaff', '#c279ff', '#202b3a', '#ffffff', '#f27832']
STYLE = '''
QWidget {color:#344054;font:10pt Segoe UI;}
QFrame#card {background:transparent;border:0;border-radius:12px;}
QLabel {background:transparent;border:0;}
QPushButton {background:#edf2f8;border:1px solid #d9e2ed;border-radius:8px;padding:6px;}
QPushButton:hover {background:#dce9fa;}
QComboBox {background:white;border:1px solid #d6deea;border-radius:6px;padding:4px;}
QSlider::groove:horizontal {height:4px;background:#dce3ed;border-radius:2px;}
QSlider::sub-page:horizontal {background:#6297dc;border-radius:2px;}
QSlider::handle:horizontal {background:white;border:2px solid #6297dc;width:12px;margin:-5px 0;border-radius:7px;}
'''

class Overlay(W.QWidget):
    def __init__(self):
        super().__init__(None, C.Qt.FramelessWindowHint | C.Qt.WindowStaysOnTopHint | C.Qt.Tool | C.Qt.WindowTransparentForInput | C.Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(C.Qt.WA_TranslucentBackground)
        self.setGeometry(G.QGuiApplication.primaryScreen().virtualGeometry())
        self.image=G.QImage(self.size(),G.QImage.Format_ARGB32_Premultiplied)
        self.image.fill(C.Qt.transparent)
        self.history=[]; self.future=[]
        self.selection=None
        self.shield=False
        self.show()
    def segment(self,a,b,color,width,erase=False):
        p=G.QPainter(self.image); p.setRenderHint(G.QPainter.Antialiasing)
        if erase:p.setCompositionMode(G.QPainter.CompositionMode_Clear)
        p.setPen(G.QPen(G.QColor(color),width,C.Qt.SolidLine,C.Qt.RoundCap,C.Qt.RoundJoin))
        if a==b:p.drawPoint(b)
        else:p.drawLine(a,b)
        p.end()
        margin=int(width/2)+3
        self.update(C.QRectF(a,b).normalized().adjusted(-margin,-margin,margin,margin).toAlignedRect())
    def checkpoint(self):
        # QImage shares pixels until the next draw; cap retained pixel memory.
        limit=max(1,min(20,(128*1024*1024)//max(1,self.image.sizeInBytes())))
        self.future.clear()
        self.history.append(G.QImage(self.image))
        self.history=self.history[-limit:]
    def undo(self):
        if self.history:
            self.future.append(G.QImage(self.image)); self.image=self.history.pop(); self.update()
    def redo(self):
        if self.future:
            self.history.append(G.QImage(self.image)); self.image=self.future.pop(); self.update()
    def clear(self):self.image.fill(C.Qt.transparent); self.update()
    def paintEvent(self,event):
        p=G.QPainter(self)
        if self.shield:p.fillRect(self.rect(),G.QColor(255,255,255,2))
        p.drawImage(0,0,self.image)
        if self.selection:
            rect=self.selection
            p.setPen(G.QPen(G.QColor('#ffffff'),3)); p.drawRect(rect)
            p.setPen(G.QPen(G.QColor('#287ce0'),1.5,C.Qt.DashLine)); p.drawRect(rect)
            p.setBrush(G.QColor('white')); p.setPen(G.QPen(G.QColor('#287ce0'),1))
            for point in (rect.topLeft(),rect.topRight(),rect.bottomLeft(),rect.bottomRight(),C.QPointF(rect.center().x(),rect.top()),C.QPointF(rect.center().x(),rect.bottom()),C.QPointF(rect.left(),rect.center().y()),C.QPointF(rect.right(),rect.center().y())):p.drawRect(C.QRectF(point.x()-3,point.y()-3,6,6))

class SizeSlider(W.QSlider):
    sizeChanged=C.Signal(int)
    def __init__(self,values):
        super().__init__(C.Qt.Horizontal)
        self.steps=values; self.setRange(0,len(values)-1)
        self.setSingleStep(1); self.setPageStep(1); self.setTickInterval(1); self.setTickPosition(W.QSlider.TicksBelow)
        self.setFixedSize(78,28)
        self.valueChanged.connect(lambda i:self.sizeChanged.emit(self.steps[i]))
    def set_size(self,value):
        self.blockSignals(True); self.setValue(min(range(len(self.steps)),key=lambda i:abs(self.steps[i]-value))); self.blockSignals(False)


def draw_action(p,kind):
    p.save(); p.setRenderHint(G.QPainter.Antialiasing); p.setBrush(C.Qt.NoBrush)
    p.setPen(G.QPen(G.QColor('#263b50'),1.15,C.Qt.SolidLine,C.Qt.RoundCap,C.Qt.RoundJoin))
    if kind=='paste':
        p.setBrush(G.QColor('#e4edf8')); p.drawRoundedRect(C.QRectF(5,5,14,17),2,2)
        p.setBrush(G.QColor('#ffffff')); p.drawRoundedRect(C.QRectF(8,2,8,5),1,1)
        p.drawLine(8,12,16,12); p.drawLine(8,16,16,16)
    elif kind=='copy':
        p.drawRoundedRect(C.QRectF(3,3,12,15),1,1); p.setBrush(G.QColor('#fafcff')); p.drawRoundedRect(C.QRectF(9,7,12,15),1,1)
    elif kind=='cut':
        p.drawEllipse(C.QPointF(6,18),3,3); p.drawEllipse(C.QPointF(17,18),3,3)
        p.drawLine(8,16,18,3); p.drawLine(15,16,5,3)
    elif kind=='brush':
        p.setBrush(C.Qt.NoBrush)
        p.drawPolygon(G.QPolygonF([C.QPointF(9,15),C.QPointF(18,3),C.QPointF(21,5),C.QPointF(12,17)]))
        path=G.QPainterPath(); path.moveTo(9,14); path.cubicTo(4,14,7,19,3,21); path.cubicTo(11,22,14,17,12,16)
        p.drawPath(path)
    elif kind=='fill':
        p.setBrush(G.QColor('#dce8f6')); p.drawPolygon(G.QPolygonF([C.QPointF(4,10),C.QPointF(11,3),C.QPointF(20,12),C.QPointF(13,19)]))
        p.drawLine(6,8,9,4); p.setBrush(G.QColor('#49a5e6')); p.drawEllipse(C.QPointF(20,19),2,3)
    elif kind=='eraser':
        p.setBrush(C.Qt.NoBrush); p.drawPolygon(G.QPolygonF([C.QPointF(4,15),C.QPointF(13,4),C.QPointF(21,11),C.QPointF(13,21),C.QPointF(10,21)])); p.drawLine(9,10,17,17)
    elif kind=='picker':
        p.drawPolygon(G.QPolygonF([C.QPointF(4,17),C.QPointF(16,5),C.QPointF(19,8),C.QPointF(7,20),C.QPointF(3,21)])); p.drawLine(13,4,20,11)
    elif kind=='select':
        p.setPen(G.QPen(G.QColor('#263b50'),1.0,C.Qt.DashLine)); p.drawRect(C.QRectF(3,4,18,16))
    elif kind=='line':p.drawLine(3,20,21,3)
    elif kind=='rect':p.drawRect(C.QRectF(3,5,18,14))
    elif kind=='ellipse':p.drawEllipse(C.QRectF(3,4,18,16))
    elif kind=='triangle':p.drawPolygon(G.QPolygonF([C.QPointF(12,3),C.QPointF(22,20),C.QPointF(2,20)]))
    elif kind=='clear':
        p.drawLine(5,7,19,7); p.drawRoundedRect(C.QRectF(7,7,10,14),1.5,1.5)
        p.drawLine(9,4,15,4); p.drawLine(9,4,9,7); p.drawLine(15,4,15,7)
        p.drawLine(10,10,10,17); p.drawLine(14,10,14,17)
    elif kind=='camera':
        p.drawRoundedRect(C.QRectF(3,7,18,13),2,2); p.drawEllipse(C.QPointF(12,13),4,4)
        p.drawLine(7,7,9,4); p.drawLine(9,4,15,4); p.drawLine(15,4,17,7)
    else:
        if kind=='redo':p.translate(24,0); p.scale(-1,1)
        path=G.QPainterPath(); path.moveTo(5,9); path.cubicTo(20,3,23,20,11,20); p.drawPath(path)
        p.drawPolyline(G.QPolygonF([C.QPointF(5,4),C.QPointF(5,9),C.QPointF(10,10)]))
    p.restore()

class VectorIcon(G.QIconEngine):
    def __init__(self,kind):super().__init__(); self.kind=kind
    def clone(self):return VectorIcon(self.kind)
    def paint(self,painter,rect,mode,state):
        painter.save(); painter.translate(rect.x(),rect.y()); painter.scale(rect.width()/24,rect.height()/24); draw_action(painter,self.kind); painter.restore()
    def pixmap(self,size,mode,state):
        pix=G.QPixmap(size); pix.fill(C.Qt.transparent); painter=G.QPainter(pix); self.paint(painter,pix.rect(),mode,state); painter.end(); return pix

def action_icon(kind):return G.QIcon(VectorIcon(kind))


def paint_glass(p,rect,highlight=None):
    p.setRenderHint(G.QPainter.Antialiasing)
    p.setBrush(G.QColor('#fafcff')); p.setPen(G.QPen(G.QColor('#d9e2ed'),1))
    p.drawRoundedRect(C.QRectF(rect).adjusted(.5,.5,-.5,-.5),12,12)

class GlassPanel(W.QWidget):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.setAttribute(C.Qt.WA_TranslucentBackground); self.setAutoFillBackground(False)
        self.glass_backend='solid-white'; self.glass_light=None
    def paintEvent(self,event):
        p=G.QPainter(self); p.setCompositionMode(G.QPainter.CompositionMode_Source); p.fillRect(self.rect(),C.Qt.transparent); p.setCompositionMode(G.QPainter.CompositionMode_SourceOver)
        paint_glass(p,self.rect())

class PalettePanelBase(GlassPanel):
    def refresh(self):
        for key,button in getattr(self,'tool_buttons',{}).items():button.setChecked(key==self.owner.drawing_tool)
        for color,button in self.colors.items():
            selected=color==self.owner.cfg['color']; button.setText('✓' if selected else '')
            ink='#202b3a' if color in ('#ffffff','#ffbd2e','#43d886') else 'white'
            button.setStyleSheet(f'background:{color};color:{ink};font-weight:bold;border:{3 if selected else 1}px solid {"#3479d0" if selected else "#d9e1ed"};border-radius:7px;padding:0;')
        for key,slider in self.sliders.items():
            size=self.owner.cfg[key]; slider.set_size(size); self.values[key].setText(str(size))
            self.values[key].setToolTip(str(size)+' px')
            pix=G.QPixmap(28,32); pix.fill(C.Qt.transparent); p=G.QPainter(pix); p.setRenderHint(G.QPainter.Antialiasing)
            if key=='width':
                diameter=3+21*(size-1)/39; p.setPen(C.Qt.NoPen); p.setBrush(G.QColor(self.owner.cfg['color'])); p.drawEllipse(C.QPointF(14,16),diameter/2,diameter/2)
            else:
                scale=6+15*(size-4)/96
                p.translate(14,16); p.rotate(-30); p.setPen(G.QPen(G.QColor('#768ba8'),1.2)); p.setBrush(G.QColor('#dce6f4'))
                p.drawRoundedRect(C.QRectF(-scale*.35,-scale*.5,scale*.7,scale),2,2)
                p.drawLine(C.QPointF(-scale*.35,scale*.18),C.QPointF(scale*.35,scale*.18))
            p.end(); self.previews[key].setPixmap(pix)
    def open(self):
        self.animation.stop(); target=self.pos(); start=target+C.QPoint(0,-6)
        self.move(start); self.show(); self.raise_()
        self.animation=C.QPropertyAnimation(self,b'pos'); self.animation.setDuration(180); self.animation.setEasingCurve(C.QEasingCurve.OutCubic)
        self.animation.setStartValue(start); self.animation.setEndValue(target); self.animation.start()
    def dismiss(self):self.animation.stop(); self.hide()

class CursorPalette(PalettePanelBase):
    def __init__(self,owner):
        GlassPanel.__init__(self,None,C.Qt.Tool|C.Qt.FramelessWindowHint|C.Qt.WindowStaysOnTopHint|C.Qt.WindowDoesNotAcceptFocus)
        self.owner=owner
        self.setStyleSheet(STYLE)
        outer=W.QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        card=W.QFrame(); card.setObjectName('card'); outer.addWidget(card)
        layout=W.QVBoxLayout(card); layout.setContentsMargins(8,8,8,8); layout.setSpacing(5)
        grid=W.QGridLayout(); grid.setSpacing(5); layout.addLayout(grid)
        self.colors={}; self.sliders={}; self.previews={}; self.values={}
        for i,color in enumerate(COLORS[:6]):
            button=W.QPushButton(); button.setFixedSize(57,24)
            button.clicked.connect(lambda checked=False,c=color:owner.set_value('color',c)); grid.addWidget(button,i//2,i%2); self.colors[color]=button
        for key,steps in [('width',[1,2,3,5,8,12,16,24,32,40]),('eraser',[4,8,12,20,28,40,56,72,88,100])]:
            row=W.QHBoxLayout(); row.setSpacing(4); layout.addLayout(row)
            preview=W.QLabel(); preview.setFixedSize(28,32); row.addWidget(preview); self.previews[key]=preview
            slider=SizeSlider(steps); slider.setFixedWidth(86); slider.setAccessibleName('Кисть' if key=='width' else 'Ластик')
            slider.sizeChanged.connect(lambda v,k=key:owner.set_value(k,v)); row.addWidget(slider); self.sliders[key]=slider
            value=W.QLabel(self); value.hide(); self.values[key]=value
        self.setFixedWidth(138); self.adjustSize()
        self.animation=C.QPropertyAnimation(self,b'windowOpacity'); self.animation.setDuration(160); self.animation.setEasingCurve(C.QEasingCurve.OutCubic)
        self.refresh()

class BrushChooser(GlassPanel):
    def __init__(self,owner):
        super().__init__(None,C.Qt.Tool|C.Qt.FramelessWindowHint|C.Qt.WindowStaysOnTopHint|C.Qt.WindowDoesNotAcceptFocus)
        self.owner=owner; self.buttons={}
        self.setStyleSheet(STYLE+'QToolButton {border:1px solid transparent;border-radius:7px;background:transparent;} QToolButton:hover {background:rgba(30,65,110,18);border:1px solid #9bb9d8;} QToolButton:checked {background:rgba(80,150,235,65);border:1px solid #6e9fd6;}')
        grid=W.QGridLayout(self); grid.setContentsMargins(9,9,9,9); grid.setSpacing(4)
        for i,(kind,title) in enumerate(BRUSHES):
            button=W.QToolButton(); button.setIcon(brush_icon(kind)); button.setIconSize(C.QSize(56,36)); button.setFixedSize(62,44); button.setCheckable(True); button.setToolTip(title)
            button.clicked.connect(lambda checked=False,k=kind:self.choose(k)); grid.addWidget(button,i//3,i%3); self.buttons[kind]=button
        self.adjustSize()
    def choose(self,kind):
        self.owner.set_value('brush_kind',kind); self.owner.select_tool('brush'); self.hide()
    def reveal(self,position):
        for kind,button in self.buttons.items():button.setChecked(kind==self.owner.cfg['brush_kind'])
        screen=G.QGuiApplication.screenAt(position) or G.QGuiApplication.primaryScreen(); area=screen.availableGeometry()
        self.move(max(area.left(),min(position.x(),area.right()-self.width())),max(area.top(),min(position.y(),area.bottom()-self.height())))
        self.show(); self.raise_()

class TextEditor(GlassPanel):
    def __init__(self,owner,anchor):
        super().__init__(None,C.Qt.Tool|C.Qt.FramelessWindowHint|C.Qt.WindowStaysOnTopHint)
        self.owner=owner; self.anchor=anchor; self.setStyleSheet(STYLE)
        layout=W.QVBoxLayout(self); layout.setContentsMargins(9,9,9,9); layout.setSpacing(6)
        row=W.QHBoxLayout(); layout.addLayout(row)
        self.family=W.QFontComboBox(); self.family.setCurrentFont(G.QFont('Segoe UI')); self.family.setFixedWidth(170); row.addWidget(self.family)
        self.size=W.QSpinBox(); self.size.setRange(6,144); self.size.setValue(20); self.size.setSuffix(' pt'); row.addWidget(self.size)
        self.bold=W.QPushButton('B'); self.bold.setCheckable(True); self.bold.setFixedWidth(32); row.addWidget(self.bold)
        self.edit=W.QTextEdit(); self.edit.setAcceptRichText(False); self.edit.setPlaceholderText('Введите текст…'); self.edit.setStyleSheet('background:rgba(255,255,255,110);border:1px solid #a7bbd4;border-radius:5px;color:'+owner.cfg['color']+';'); self.edit.setMinimumSize(350,140); layout.addWidget(self.edit)
        row=W.QHBoxLayout(); layout.addLayout(row)
        label=W.QLabel('Ctrl+Enter — готово · Esc — отмена'); label.setStyleSheet('font-size:9pt;'); row.addWidget(label)
        done=W.QPushButton('Готово'); done.clicked.connect(lambda:owner.finish_text(True)); row.addWidget(done)
        for signal in (self.family.currentFontChanged,self.size.valueChanged,self.bold.toggled):signal.connect(self.update_font)
        self.update_font()
        self.accept_key=G.QShortcut(G.QKeySequence('Ctrl+Return'),self); self.accept_key.activated.connect(lambda:owner.finish_text(True))
        self.cancel_key=G.QShortcut(G.QKeySequence('Escape'),self); self.cancel_key.activated.connect(lambda:owner.finish_text(False))
        self.capture_key=G.QShortcut(G.QKeySequence('Ctrl+Alt+S'),self); self.capture_key.activated.connect(owner.screenshot)
        self.adjustSize()
    def current_font(self):
        font=G.QFont(self.family.currentFont()); font.setPointSize(self.size.value()); font.setBold(self.bold.isChecked()); return font
    def update_font(self,*args):
        font=self.current_font(); self.edit.setFont(font); self.edit.document().setDefaultFont(font)
        cursor=G.QTextCursor(self.edit.document()); cursor.select(G.QTextCursor.Document)
        fmt=G.QTextCharFormat(); fmt.setFont(font); cursor.mergeCharFormat(fmt); self.edit.setCurrentFont(font)
    def closeEvent(self,event):
        event.ignore(); self.owner.finish_text(True)

class CaptureToast(GlassPanel):
    def __init__(self):
        super().__init__(None,C.Qt.Tool|C.Qt.FramelessWindowHint|C.Qt.WindowStaysOnTopHint|C.Qt.WindowDoesNotAcceptFocus)
        self.title_text='Скриншот сохранён'; self.detail_text='Скопирован в буфер обмена'
        self.setFixedSize(380,88)
        self.timer=C.QTimer(self); self.timer.setSingleShot(True); self.timer.timeout.connect(self.hide)
    def paintEvent(self,event):
        super().paintEvent(event)
        p=G.QPainter(self); p.setRenderHint(G.QPainter.TextAntialiasing)
        font=G.QFont('Segoe UI'); font.setPixelSize(20); font.setWeight(G.QFont.DemiBold); p.setFont(font); p.setPen(G.QColor('#10273f'))
        p.drawText(C.QRectF(20,13,self.width()-40,28),C.Qt.AlignLeft|C.Qt.AlignVCenter,self.title_text)
        font.setPixelSize(15); font.setWeight(G.QFont.Normal); p.setFont(font); p.setPen(G.QColor('#243e58'))
        p.drawText(C.QRectF(20,45,self.width()-40,25),C.Qt.AlignLeft|C.Qt.AlignVCenter,self.detail_text)
    def notify(self,screen):
        number=G.QGuiApplication.screens().index(screen)+1
        self.detail_text='Скопирован в буфер · Монитор '+str(number); self.update()
        area=screen.availableGeometry(); self.move(area.right()-self.width()-18,area.bottom()-self.height()-18); self.show(); self.raise_(); self.timer.start(3300)

class HUD(PalettePanelBase):
    def __init__(self,owner):
        super().__init__(None,C.Qt.Tool|C.Qt.FramelessWindowHint|C.Qt.WindowStaysOnTopHint|C.Qt.WindowDoesNotAcceptFocus)
        self.owner=owner; self.setStyleSheet(STYLE)
        self.colors={}; self.sliders={}; self.previews={}; self.values={}; self.actions={}; self.tool_buttons={}
        row=W.QHBoxLayout(self); row.setContentsMargins(10,7,10,7); row.setSpacing(5)
        for color in COLORS:
            button=W.QPushButton(); button.setFixedSize(23,23); button.clicked.connect(lambda checked=False,c=color:owner.set_value('color',c)); row.addWidget(button); self.colors[color]=button
        for key,steps in [('width',[1,2,3,5,8,12,16,24,32,40]),('eraser',[4,8,12,20,28,40,56,72,88,100])]:
            preview=W.QLabel(); preview.setFixedSize(28,32); row.addWidget(preview); self.previews[key]=preview
            slider=SizeSlider(steps); slider.setFixedWidth(72); slider.setToolTip('Кисть' if key=='width' else 'Ластик'); slider.sizeChanged.connect(lambda v,k=key:owner.set_value(k,v)); row.addWidget(slider); self.sliders[key]=slider
            value=W.QLabel(); value.setFixedWidth(24); value.setAlignment(C.Qt.AlignCenter); row.addWidget(value); self.values[key]=value
        for kind,tip,callback in [('undo','Отменить · Ctrl+Z',owner.undo),('redo','Повторить · Ctrl+Shift+Z',owner.redo),('clear','Очистить · Ctrl+Alt+E',owner.clear),('camera','Снимок · Ctrl+Alt+S',owner.screenshot)]:
            button=W.QPushButton(); button.setIcon(action_icon(kind)); button.setIconSize(C.QSize(21,21)); button.setFixedSize(30,30); button.setStyleSheet('padding:0;'); button.setToolTip(tip); button.clicked.connect(callback); row.addWidget(button); self.actions[kind]=button
        tools=W.QPushButton('⋯'); tools.setFixedSize(30,30); tools.setToolTip('Инструменты'); tools.clicked.connect(self.tool_menu); row.addWidget(tools)
        self.brush_popup=BrushChooser(owner)
        self.animation=C.QPropertyAnimation(self,b'pos'); self.setFixedHeight(54); self.adjustSize(); self.refresh()
    def refresh(self):
        PalettePanelBase.refresh(self)
        for key,slider in self.sliders.items():
            slider.set_size(self.owner.cfg[key]); self.values[key].setText(str(self.owner.cfg[key]))
    def fit_to_screen(self,area):pass
    def tool_menu(self):
        menu=W.QMenu(self)
        for title,key in [('Кисть · B','brush'),('Ластик · E','eraser'),('Выделение · S','select'),('Текст · T','text'),('Линия','line'),('Прямоугольник','rect'),('Эллипс','ellipse'),('Треугольник','triangle'),('Заливка','fill'),('Пипетка','picker')]:
            action=menu.addAction(title); action.setCheckable(True); action.setChecked(self.owner.drawing_tool==key); action.triggered.connect(lambda checked=False,k=key:self.owner.select_tool(k))
        menu.addSeparator(); menu.addAction('Тип кисти',self.brush_menu); menu.addAction('Другой цвет',self.choose_color)
        menu.exec(self.mapToGlobal(C.QPoint(self.width()-30,self.height()+4)))
    def brush_menu(self):self.brush_popup.reveal(self.mapToGlobal(C.QPoint(self.width()-210,self.height()+4)))
    def choose_color(self):
        self.owner.set_layer_shortcuts(False)
        try:
            color=W.QColorDialog.getColor(G.QColor(self.owner.cfg['color']),self)
            if color.isValid():self.owner.set_value('color',color.name())
        finally:self.owner.set_layer_shortcuts(self.owner.overlay.shield and self.owner.text_editor is None)

class HotkeyFilter(C.QAbstractNativeEventFilter):
    def __init__(self,owner):super().__init__(); self.owner=owner
    def nativeEventFilter(self,event_type,message):
        from ctypes import wintypes
        msg=wintypes.MSG.from_address(int(message))
        if msg.message==0x0312 and 712<=msg.wParam<=724:
            if msg.wParam==712:self.owner.toggle_mode()
            return True,0
        return False,0

class App:
    def __init__(self):
        self.cfg=dict(color='#ff3434',width=5,eraser=28,shield=False,brush_kind='round')
        try:self.cfg.update({k:v for k,v in json.loads(SETTINGS.read_text()).items() if k in self.cfg})
        except (OSError,ValueError):pass
        self.moving=False; self.resizing=False; self.resize_anchor=None; self.move_image=None; self.move_rect=None
        self.shape_filled=False; self.drawing_tool='brush'; self.anchor=None; self.base_image=None
        self.gesture=None; self.last_draw_global=None; self.last_canvas_point=None; self.text_editor=None; self.editor_wait_release=False; self.brush_points=[]
        self.enabled=True; self.previous=None; self.tool=None; self.capturing=False; self.last_screenshot=None
        self.overlay=Overlay(); self.panel=CursorPalette(self); self.dock=HUD(self); self.capture_toast=CaptureToast()
        icon=G.QIcon(str(RESOURCE_DIR/'app.ico'))
        W.QApplication.instance().setWindowIcon(icon)
        self.tray=W.QSystemTrayIcon(icon); self.tray.setToolTip(APP)
        menu=W.QMenu(); menu.addAction('Палитра',self.toggle_panel); menu.addAction('Слой',self.toggle_mode)
        toggle=menu.addAction('Рисование'); toggle.setCheckable(True); toggle.setChecked(True); toggle.toggled.connect(self.enable)
        menu.addAction('Отменить',self.undo); menu.addAction('Повторить',self.redo); menu.addAction('Скриншот',self.screenshot)
        menu.addAction('Очистить',self.clear); menu.addSeparator(); menu.addAction('Выход',W.QApplication.quit)
        self.tray.setContextMenu(menu); self.tray.activated.connect(lambda r:self.toggle_panel() if r==W.QSystemTrayIcon.Trigger else None); self.tray.show()
        self.keys={}; self.repeat_kind=None; self.repeat_at=0
        self.history_clock=C.QElapsedTimer(); self.history_clock.start()
        self.apply_mode()
        self.native_filter=HotkeyFilter(self)
        W.QApplication.instance().installNativeEventFilter(self.native_filter)
        self.hotkey_registered=bool(u.RegisterHotKey(None,712,0x4002,0x44))
        W.QApplication.instance().aboutToQuit.connect(lambda:(u.UnregisterHotKey(None,713),u.UnregisterHotKey(None,714)))
        W.QApplication.instance().aboutToQuit.connect(lambda:u.UnregisterHotKey(None,712) if self.hotkey_registered else None)
        self.timer=C.QTimer(); self.timer.timeout.connect(self.tick); self.timer.start(8)
    def set_value(self,key,value):
        self.cfg[key]=value
        try:SETTINGS.write_text(json.dumps(self.cfg))
        except OSError:pass
        if hasattr(self,'panel'):self.panel.refresh(); self.dock.refresh()
    def clear(self):
        self.gesture=None; self.moving=False; self.base_image=None
        self.overlay.selection=None
        self.overlay.checkpoint(); self.overlay.clear(); self.previous=None; self.tool=None
    def undo(self):
        self.gesture=None; self.base_image=None
        self.overlay.selection=None; self.moving=False
        self.overlay.undo(); self.previous=None; self.tool=None
    def redo(self):
        self.gesture=None; self.base_image=None
        self.overlay.selection=None; self.moving=False
        self.overlay.redo(); self.previous=None; self.tool=None
    def capture_target(self):
        point=self.last_draw_global or G.QCursor.pos()
        screens=G.QGuiApplication.screens()
        return self.choose_capture_screen(screens,point)
    @staticmethod
    def choose_capture_screen(screens,point):
        return next((screen for screen in screens if screen.geometry().contains(point)),screens[0])
    def capture_screen_image(self,screen):
        shot=screen.grabWindow(0)
        if shot.isNull():raise RuntimeError('Не удалось захватить экран')
        result=shot.toImage().convertToFormat(G.QImage.Format_ARGB32_Premultiplied); result.setDevicePixelRatio(1.)
        rect=screen.geometry().translated(-self.overlay.geometry().topLeft())
        ink=self.overlay.image.copy(rect)
        painter=G.QPainter(result); painter.setRenderHint(G.QPainter.SmoothPixmapTransform); painter.drawImage(C.QRectF(result.rect()),ink,C.QRectF(ink.rect())); painter.end()
        return result
    @staticmethod
    def exclude_capture_windows(windows):
        changes=[]
        if W.QApplication.platformName()!='windows' or sys.getwindowsversion().build<19041:return changes
        from ctypes import wintypes
        u.SetWindowDisplayAffinity.argtypes=[wintypes.HWND,wintypes.DWORD]; u.SetWindowDisplayAffinity.restype=wintypes.BOOL
        u.GetWindowDisplayAffinity.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]; u.GetWindowDisplayAffinity.restype=wintypes.BOOL
        for widget in windows:
            hwnd=wintypes.HWND(int(widget.winId())); old=wintypes.DWORD(0)
            u.GetWindowDisplayAffinity(hwnd,ctypes.byref(old))
            if u.SetWindowDisplayAffinity(hwnd,0x11):changes.append((int(widget.winId()),old.value))
        return changes
    @staticmethod
    def restore_capture_windows(changes):
        restored=set()
        for hwnd,old in changes:
            if hwnd in restored:continue
            restored.add(hwnd)
            if u.IsWindow(ctypes.c_void_p(hwnd)):u.SetWindowDisplayAffinity(ctypes.c_void_p(hwnd),old)
    def screenshot(self):
        if self.capturing:return
        if self.text_editor is not None:self.finish_text(True)
        self.capturing=True; target=self.capture_target()
        persistent=(self.panel,self.dock,self.dock.brush_popup,self.overlay)
        restore=[w for w in persistent if w.isVisible()]
        visible=[w for w in W.QApplication.topLevelWidgets() if w.isVisible()]
        affinities=self.exclude_capture_windows(visible)
        for widget in visible:widget.hide()
        def capture():
            filename=None
            try:
                # Catch tooltips or flyouts that were queued before the click.
                late=[w for w in W.QApplication.topLevelWidgets() if w.isVisible()]
                affinities.extend(self.exclude_capture_windows(late))
                for widget in late:widget.hide()
                W.QApplication.processEvents(C.QEventLoop.ExcludeUserInputEvents)
                if W.QApplication.platformName()=='windows':ctypes.windll.dwmapi.DwmFlush()
                result=self.capture_screen_image(target)
                W.QApplication.clipboard().setImage(result)
                folder=Path(C.QStandardPaths.writableLocation(C.QStandardPaths.PicturesLocation))/APP; folder.mkdir(parents=True,exist_ok=True)
                filename=folder/('Paint Overlay '+C.QDateTime.currentDateTime().toString('yyyy-MM-dd HH-mm-ss-zzz')+'.png')
                if not result.save(str(filename),'PNG'):raise RuntimeError('Не удалось сохранить файл')
                self.last_screenshot=filename
            except Exception as error:W.QMessageBox.warning(None,APP,str(error))
            finally:
                self.restore_capture_windows(affinities)
                for widget in reversed(restore):widget.show(); widget.raise_()
                self.capturing=False
            if filename is not None and self.last_screenshot==filename:self.capture_toast.notify(target)
        C.QTimer.singleShot(300,capture)
    def enable(self,value):self.enabled=value; self.previous=None; self.apply_mode()
    def set_layer_shortcuts(self,active):
        self.layer_shortcuts_active=active
        for ident in range(713,725):u.UnregisterHotKey(None,ident)
        if active:
            for ident,vk,mods in ((713,0x5A,0x4002),(714,0x5A,0x4006),(715,0x43,0x4002),(716,0x56,0x4002),(717,0x58,0x4002),(718,0x2E,0x4000),(719,0x1B,0x4000),(720,0x42,0x4000),(721,0x45,0x4000),(722,0x53,0x4000),(723,0x54,0x4000),(724,0x41,0x4002)):u.RegisterHotKey(None,ident,mods,vk)
    def apply_mode(self):
        shield=self.cfg['shield'] and self.enabled
        if not shield and self.text_editor is not None:self.finish_text(True,refresh=False)
        self.set_layer_shortcuts(shield and self.text_editor is None)
        self.previous=None; self.tool=None
        self.overlay.setWindowFlag(C.Qt.WindowTransparentForInput,not shield); self.overlay.shield=shield
        self.overlay.setCursor(C.Qt.CrossCursor if shield else C.Qt.ArrowCursor); self.overlay.show(); self.overlay.update()
        if shield:
            area=(G.QGuiApplication.screenAt(G.QCursor.pos()) or G.QGuiApplication.primaryScreen()).availableGeometry()
            self.dock.fit_to_screen(area)
            self.dock.move(area.center().x()-self.dock.width()//2,area.top()+14); self.dock.open()
        else:self.dock.dismiss(); self.panel.dismiss(); self.dock.brush_popup.hide(); self.overlay.selection=None; self.overlay.update()
        if self.panel.isVisible():self.panel.raise_()
    def toggle_mode(self):
        if self.capturing:return
        self.set_value('shield',not self.cfg['shield']); self.panel.dismiss(); self.apply_mode()
    def leave_layer(self):
        if self.cfg['shield']:self.toggle_mode()
    def toggle_panel(self):
        if not self.overlay.shield:return
        if self.panel.isVisible():self.panel.dismiss(); return
        pos=G.QCursor.pos(); area=(G.QGuiApplication.screenAt(pos) or G.QGuiApplication.primaryScreen()).availableGeometry()
        self.panel.move(max(area.left(),min(pos.x()+14,area.right()-self.panel.width())),max(area.top(),min(pos.y()+14,area.bottom()-self.panel.height())))
        self.dock.brush_popup.hide(); self.panel.open()
    def edge(self,name,value):
        old=self.keys.get(name,False); self.keys[name]=value
        return value and not old
    def repeat_history(self,kind,held):
        if not held or not self.overlay.shield:
            self.repeat_kind=None
            return
        now=self.history_clock.elapsed()
        if self.repeat_kind!=kind:
            (self.redo if kind=='redo' else self.undo)()
            self.repeat_kind=kind; self.repeat_at=now+350
        elif now>=self.repeat_at:
            (self.redo if kind=='redo' else self.undo)()
            self.repeat_at=now+60
    def set_shape_fill(self,value):self.shape_filled=value
    def pick_color(self):
        self.select_tool('picker')
    def select_tool(self,key):
        if self.text_editor is not None:self.finish_text(True)
        if key!='select':self.overlay.selection=None; self.overlay.update()
        self.drawing_tool=key; self.previous=None; self.anchor=None; self.gesture=None
        self.overlay.setCursor(C.Qt.IBeamCursor if key=='text' else C.Qt.CrossCursor)
        self.dock.refresh()
    def select_all(self):
        self.select_tool('select'); self.overlay.selection=C.QRectF(self.overlay.image.rect()); self.overlay.update()
    def prepare_paste(self):
        image=W.QApplication.clipboard().image()
        if image.isNull():return
        if image.width()>self.overlay.width() or image.height()>self.overlay.height():image=image.scaled(self.overlay.size(),C.Qt.KeepAspectRatio,C.Qt.SmoothTransformation)
        cursor=C.QPointF(self.overlay.mapFromGlobal(G.QCursor.pos()))
        if any(w.isVisible() and w.frameGeometry().contains(G.QCursor.pos()) for w in (self.panel,self.dock)):
            cursor=self.last_canvas_point or C.QPointF(40,100)
        cursor=C.QPointF(max(0,min(cursor.x(),self.overlay.width()-image.width())),max(0,min(cursor.y(),self.overlay.height()-image.height())))
        self.overlay.checkpoint(); painter=G.QPainter(self.overlay.image); painter.drawImage(cursor,image); painter.end()
        self.select_tool('select'); self.overlay.selection=C.QRectF(cursor,C.QSizeF(image.size())); self.overlay.update(); self.last_draw_global=self.overlay.mapToGlobal(cursor.toPoint())
    def copy_selection(self,cut=False):
        if not self.overlay.selection:return
        rect=self.overlay.selection.toAlignedRect().intersected(self.overlay.image.rect())
        W.QApplication.clipboard().setImage(self.overlay.image.copy(rect))
        if cut:
            self.delete_selection()
    def delete_selection(self):
        if not self.overlay.selection:return
        self.gesture=None; self.previous=None; self.moving=False
        self.last_draw_global=self.overlay.mapToGlobal(self.overlay.selection.center().toPoint())
        self.overlay.checkpoint()
        painter=G.QPainter(self.overlay.image); painter.setCompositionMode(G.QPainter.CompositionMode_Clear); painter.fillRect(self.overlay.selection,C.Qt.transparent); painter.end()
        self.overlay.selection=None; self.overlay.update()
    def shape(self,start,end,shift):
        if self.moving:
            delta=end-start; rect=C.QRectF(self.resize_anchor,end).normalized() if self.resizing else self.move_rect.translated(delta)
            painter=G.QPainter(self.overlay.image); painter.drawImage(rect,self.move_image); painter.end()
            self.overlay.selection=rect; self.overlay.update(); return
        dx=end.x()-start.x(); dy=end.y()-start.y()
        if shift:
            if self.drawing_tool=='line':
                length=math.hypot(dx,dy); angle=round(math.atan2(dy,dx)/(math.pi/4))*math.pi/4; dx=length*math.cos(angle); dy=length*math.sin(angle)
            else:
                size=max(abs(dx),abs(dy)); dx=math.copysign(size,dx); dy=math.copysign(size,dy)
        end=start+C.QPointF(dx,dy); rect=C.QRectF(start,end).normalized()
        if self.drawing_tool=='select':self.overlay.selection=rect; self.overlay.update(); return
        painter=G.QPainter(self.overlay.image); painter.setRenderHint(G.QPainter.Antialiasing); painter.setPen(G.QPen(G.QColor(self.cfg['color']),self.cfg['width'],C.Qt.SolidLine,C.Qt.RoundCap,C.Qt.RoundJoin))
        if self.shape_filled:painter.setBrush(G.QColor(self.cfg['color']))
        if self.drawing_tool=='line':painter.drawLine(start,end)
        elif self.drawing_tool=='rect':painter.drawRect(rect)
        elif self.drawing_tool=='ellipse':painter.drawEllipse(rect)
        elif self.drawing_tool=='triangle':painter.drawPolygon(G.QPolygonF([C.QPointF(rect.center().x(),rect.top()),rect.bottomLeft(),rect.bottomRight()]))
        painter.end(); self.overlay.update()
    def bucket(self,point):
        image=self.overlay.image.convertToFormat(G.QImage.Format_RGBA8888)
        pil=Image.frombytes('RGBA',(image.width(),image.height()),bytes(image.constBits()),'raw','RGBA',image.bytesPerLine())
        ImageDraw.floodfill(pil,(int(point.x()),int(point.y())),G.QColor(self.cfg['color']).getRgb(),thresh=32)
        raw=pil.tobytes(); self.overlay.image=G.QImage(raw,pil.width,pil.height,pil.width*4,G.QImage.Format_RGBA8888).convertToFormat(G.QImage.Format_ARGB32_Premultiplied)
        self.overlay.update()
    def open_text(self,point):
        self.panel.dismiss(); self.dock.brush_popup.hide()
        self.text_editor=TextEditor(self,point); self.editor_wait_release=True
        self.apply_mode()
        position=self.overlay.mapToGlobal(point.toPoint()); screen=G.QGuiApplication.screenAt(position) or G.QGuiApplication.primaryScreen(); area=screen.availableGeometry()
        editor=self.text_editor
        editor.move(max(area.left(),min(position.x(),area.right()-editor.width())),max(area.top(),min(position.y(),area.bottom()-editor.height())))
        editor.show(); editor.raise_(); editor.activateWindow(); editor.edit.setFocus()
    def finish_text(self,commit,refresh=True):
        editor=self.text_editor
        if editor is None:return
        self.text_editor=None; editor.hide()
        editor.size.interpretText()
        text=editor.edit.toPlainText()
        if commit and text.strip():
            document=G.QTextDocument(); document.setDocumentMargin(0); document.setDefaultFont(editor.current_font()); document.setPlainText(text); document.setTextWidth(editor.edit.viewport().width())
            cursor=G.QTextCursor(document); cursor.select(G.QTextCursor.Document); fmt=G.QTextCharFormat(); fmt.setForeground(G.QColor(self.cfg['color'])); cursor.mergeCharFormat(fmt)
            self.overlay.checkpoint(); painter=G.QPainter(self.overlay.image); painter.translate(editor.anchor); document.drawContents(painter); painter.end()
            self.drawing_tool='select'; self.overlay.selection=C.QRectF(editor.anchor,document.size()); self.last_draw_global=self.overlay.mapToGlobal(editor.anchor.toPoint()); self.overlay.update()
        editor.deleteLater(); self.gesture=None; self.previous=None
        self.keys['esc']=True
        self.dock.refresh()
        if refresh:self.apply_mode()
    def selection_hit(self,point):
        rect=self.overlay.selection
        if not rect:return None
        points={'nw':rect.topLeft(),'ne':rect.topRight(),'sw':rect.bottomLeft(),'se':rect.bottomRight(),'n':C.QPointF(rect.center().x(),rect.top()),'s':C.QPointF(rect.center().x(),rect.bottom()),'w':C.QPointF(rect.left(),rect.center().y()),'e':C.QPointF(rect.right(),rect.center().y())}
        for name,handle in points.items():
            if abs(point.x()-handle.x())<=6 and abs(point.y()-handle.y())<=6:return name
        return 'move' if rect.contains(point) else None
    def canvas_input(self,point,down,right=False,shift=False):
        if not down:
            if self.gesture=='select' and self.overlay.selection is not None and (self.overlay.selection.width()<3 or self.overlay.selection.height()<3):self.overlay.selection=None; self.overlay.update()
            self.gesture=None; self.previous=None; self.moving=False
            return
        point=C.QPointF(max(0,min(point.x(),self.overlay.width()-1)),max(0,min(point.y(),self.overlay.height()-1)))
        self.last_canvas_point=point
        wanted='eraser' if right or self.drawing_tool=='eraser' else self.drawing_tool
        fresh=self.gesture is None
        if fresh:
            self.panel.dismiss(); self.dock.brush_popup.hide(); self.anchor=point; self.previous=point; self.moving=False; self.brush_points=[point]
            if wanted=='text':self.open_text(point); return
            if wanted=='select':
                hit=self.selection_hit(point)
                if hit:
                    self.gesture=hit; self.overlay.checkpoint(); self.move_rect=C.QRectF(self.overlay.selection.toAlignedRect()); self.move_image=self.overlay.image.copy(self.move_rect.toAlignedRect()); self.base_image=G.QImage(self.overlay.image)
                    painter=G.QPainter(self.base_image); painter.setCompositionMode(G.QPainter.CompositionMode_Clear); painter.fillRect(self.move_rect,C.Qt.transparent); painter.end()
                else:self.gesture='select'; self.overlay.selection=None
            else:
                self.overlay.selection=None; self.gesture=wanted
                if wanted!='picker':self.overlay.checkpoint()
                self.base_image=G.QImage(self.overlay.image)
        gesture=self.gesture
        if gesture=='select':
            delta=point-self.anchor
            if shift:
                size=max(abs(delta.x()),abs(delta.y())); delta=C.QPointF(math.copysign(size,delta.x()),math.copysign(size,delta.y()))
            self.overlay.selection=C.QRectF(self.anchor,self.anchor+delta).normalized().intersected(C.QRectF(self.overlay.rect())); self.overlay.update()
        elif gesture in ('move','nw','ne','sw','se','n','s','w','e'):
            if gesture=='move':
                target=self.move_rect.translated(point-self.anchor)
                target.moveLeft(max(0,min(target.left(),self.overlay.width()-target.width()))); target.moveTop(max(0,min(target.top(),self.overlay.height()-target.height())))
            else:
                target=C.QRectF(self.move_rect)
                if 'w' in gesture:target.setLeft(point.x())
                if 'e' in gesture:target.setRight(point.x())
                if 'n' in gesture:target.setTop(point.y())
                if 's' in gesture:target.setBottom(point.y())
                target=target.normalized()
                if target.width()<1 or target.height()<1:return
            self.overlay.image=G.QImage(self.base_image); painter=G.QPainter(self.overlay.image); painter.setRenderHint(G.QPainter.SmoothPixmapTransform); painter.drawImage(target,self.move_image); painter.end()
            self.overlay.selection=target; self.overlay.update(); self.last_draw_global=self.overlay.mapToGlobal(point.toPoint())
        elif gesture=='brush':
            if fresh or point!=self.previous:
                kind=self.cfg['brush_kind']
                if kind in ('marker','watercolor'):
                    if not fresh:self.brush_points.append(point)
                    self.overlay.image=G.QImage(self.base_image)
                    points=self.brush_points
                    if len(points)==1:brush_segment(self.overlay.image,point,point,self.cfg['color'],self.cfg['width'],kind)
                    for a,b in zip(points,points[1:]):brush_segment(self.overlay.image,a,b,self.cfg['color'],self.cfg['width'],kind)
                else:brush_segment(self.overlay.image,self.previous,point,self.cfg['color'],self.cfg['width'],kind)
                self.overlay.update(); self.last_draw_global=self.overlay.mapToGlobal(point.toPoint())
        elif gesture=='eraser':
            self.overlay.segment(self.previous,point,self.cfg['color'],self.cfg['eraser'],True); self.last_draw_global=self.overlay.mapToGlobal(point.toPoint())
        elif gesture=='fill':
            if fresh:self.bucket(point); self.last_draw_global=self.overlay.mapToGlobal(point.toPoint())
        elif gesture=='picker':
            if fresh:
                color=self.overlay.image.pixelColor(point.toPoint())
                if color.alpha():self.set_value('color',color.name())
                self.drawing_tool='brush'; self.dock.refresh()
        else:
            self.overlay.image=G.QImage(self.base_image); self.shape(self.anchor,point,shift); self.last_draw_global=self.overlay.mapToGlobal(point.toPoint())
        self.previous=point
    def tick(self):
        if self.capturing or W.QApplication.activeModalWidget() is not None:return
        key=lambda k:bool(u.GetAsyncKeyState(k)&0x8000)
        if self.text_editor is not None:
            if W.QApplication.activePopupWidget() is not None:return
            if not key(1):self.editor_wait_release=False
            if key(1) and not self.editor_wait_release and not self.text_editor.frameGeometry().contains(G.QCursor.pos()):self.finish_text(True)
            return
        modifier=key(0x11) and key(0x12)
        self.repeat_history('redo' if key(0x10) else 'undo',key(0x11) and key(0x5A))
        if self.edge('clear',modifier and key(0x08)):self.clear()
        if self.edge('clear_layer',modifier and key(0x45)) and self.overlay.shield:self.clear()
        if self.edge('shot',modifier and key(0x53)):self.screenshot(); return
        if self.edge('panel',key(4)) and self.overlay.shield:self.toggle_panel()
        if self.edge('mode',modifier and key(0x44)):self.toggle_mode()
        if self.edge('esc',key(0x1b)):
            if self.dock.brush_popup.isVisible():self.dock.brush_popup.hide()
            elif self.panel.isVisible():self.panel.dismiss()
            elif self.overlay.selection:self.overlay.selection=None; self.overlay.update()
            else:self.leave_layer()
        if self.overlay.shield:
            bare=not key(0x11) and not key(0x12)
            for vk,tool in ((0x42,'brush'),(0x45,'eraser'),(0x53,'select'),(0x54,'text')):
                if self.edge('tool'+str(vk),bare and key(vk)):self.select_tool(tool)
            if self.edge('all',key(0x11) and key(0x41)):self.select_all()
            if self.edge('delete',key(0x2E)):self.delete_selection()
            if self.edge('copy',key(0x11) and key(0x43)):self.copy_selection()
            if self.edge('cut',key(0x11) and key(0x58)):self.copy_selection(True)
            if self.edge('paste',key(0x11) and key(0x56)):self.prepare_paste()
        pos=G.QCursor.pos(); surfaces=(self.panel,self.dock,self.dock.brush_popup,self.capture_toast)
        over_ui=any(w.isVisible() and w.frameGeometry().contains(pos) for w in surfaces)
        if not self.overlay.shield or not self.enabled or over_ui or W.QWidget.mouseGrabber() is not None:
            self.canvas_input(C.QPointF(),False); return
        local=C.QPointF(self.overlay.mapFromGlobal(pos)); self.canvas_input(local,key(1) or key(2),key(2),key(0x10))
        if self.drawing_tool=='select':
            hit=self.selection_hit(local)
            cursor={'move':C.Qt.SizeAllCursor,'nw':C.Qt.SizeFDiagCursor,'se':C.Qt.SizeFDiagCursor,'ne':C.Qt.SizeBDiagCursor,'sw':C.Qt.SizeBDiagCursor,'n':C.Qt.SizeVerCursor,'s':C.Qt.SizeVerCursor,'w':C.Qt.SizeHorCursor,'e':C.Qt.SizeHorCursor}.get(hit,C.Qt.CrossCursor)
            self.overlay.setCursor(cursor)


if __name__=='__main__':
    kernel=ctypes.windll.kernel32; kernel.CreateMutexW.restype=ctypes.c_void_p
    mutex=kernel.CreateMutexW(None,False,'Local\\PaintOverlay.App')
    if kernel.GetLastError()==183 and '--self-test' not in sys.argv:sys.exit(0)
    app=W.QApplication(sys.argv); app.setApplicationName(APP); app.setQuitOnLastWindowClosed(False)
    instance=App()
    if '--self-test' in sys.argv:
        instance.cfg['shield']=True; instance.apply_mode(); instance.toggle_panel()
        def finish():
            Path(sys.argv[sys.argv.index('--self-test')+1]).write_text('OK: Qt, overlay, tray, compact palette')
            app.quit()
        C.QTimer.singleShot(500,finish)
    sys.exit(app.exec())
