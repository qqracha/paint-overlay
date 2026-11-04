import sys, ctypes, json, os, math
from PIL import Image, ImageDraw
from pathlib import Path
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
QFrame#card {background:transparent;border:0;border-radius:20px;}
QLabel {background:transparent;border:0;}
QPushButton {background:rgba(255,255,255,65);border:1px solid rgba(255,255,255,135);border-radius:10px;padding:6px;}
QPushButton:hover {background:rgba(255,255,255,150);}
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
            for point in (rect.topLeft(),rect.topRight(),rect.bottomLeft(),rect.bottomRight()):p.drawRect(C.QRectF(point.x()-3,point.y()-3,6,6))
            caption='Перетащите · Ctrl+C / Ctrl+V · Delete'
            label=C.QRectF(max(2,min(rect.left(),self.width()-290)),max(2,rect.top()-27),286,23)
            p.setPen(C.Qt.NoPen); p.setBrush(G.QColor('#eaf3ff')); p.drawRoundedRect(label,4,4)
            p.setPen(G.QColor('#24588d')); p.drawText(label,C.Qt.AlignCenter,caption)

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
    p.save(); p.setRenderHint(G.QPainter.Antialiasing)
    p.setPen(G.QPen(G.QColor('#20354d'),1.8,C.Qt.SolidLine,C.Qt.RoundCap,C.Qt.RoundJoin))
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
        p.setBrush(G.QColor('#d8b17a')); p.drawPolygon(G.QPolygonF([C.QPointF(8,13),C.QPointF(17,2),C.QPointF(21,5),C.QPointF(12,17)]))
        p.setBrush(G.QColor('#568fc9')); path=G.QPainterPath(); path.moveTo(8,12); path.cubicTo(3,12,7,19,2,22); path.cubicTo(13,23,15,16,12,15); path.closeSubpath(); p.drawPath(path)
    elif kind=='fill':
        p.setBrush(G.QColor('#dce8f6')); p.drawPolygon(G.QPolygonF([C.QPointF(4,10),C.QPointF(11,3),C.QPointF(20,12),C.QPointF(13,19)]))
        p.drawLine(6,8,9,4); p.setBrush(G.QColor('#49a5e6')); p.drawEllipse(C.QPointF(20,19),2,3)
    elif kind=='select':
        p.setPen(G.QPen(G.QColor('#20354d'),1.5,C.Qt.DashLine)); p.drawRect(C.QRectF(3,4,18,16))
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
    bounds=C.QRectF(rect).adjusted(.8,.8,-.8,-.8)
    radius=min(22.,bounds.height()/2)
    path=G.QPainterPath(); path.addRoundedRect(bounds,radius,radius)
    p.save(); p.setClipPath(path)
    gradient=G.QLinearGradient(bounds.topLeft(),bounds.bottomLeft())
    gradient.setColorAt(0,G.QColor(255,255,255,90)); gradient.setColorAt(.44,G.QColor(246,251,255,28)); gradient.setColorAt(1,G.QColor(228,240,255,52))
    p.fillPath(path,gradient)
    glow=G.QRadialGradient(highlight or C.QPointF(bounds.width()*.23,0),max(90.,bounds.height()*2))
    glow.setColorAt(0,G.QColor(255,255,255,75)); glow.setColorAt(1,G.QColor(255,255,255,0)); p.fillPath(path,glow)
    p.restore()
    rim=G.QLinearGradient(bounds.topLeft(),bounds.bottomLeft()); rim.setColorAt(0,G.QColor(255,255,255,235)); rim.setColorAt(.5,G.QColor(255,255,255,100)); rim.setColorAt(1,G.QColor(167,199,231,160))
    p.setBrush(C.Qt.NoBrush); p.setPen(G.QPen(G.QBrush(rim),1.1)); p.drawPath(path)
    p.setPen(G.QPen(G.QColor(255,255,255,95),.6)); p.drawRoundedRect(bounds.adjusted(1.6,1.6,-1.6,-1.6),max(1,radius-1.6),max(1,radius-1.6))

class GlassPanel(W.QWidget):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.setAttribute(C.Qt.WA_TranslucentBackground,W.QApplication.platformName()!='windows'); self.setAttribute(C.Qt.WA_NoSystemBackground,True); self.setAutoFillBackground(False)
        self.glass_backend='pending'; self.glass_light=None; self.setMouseTracking(True)
    def showEvent(self,event):
        super().showEvent(event)
        if W.QApplication.platformName()!='windows':self.glass_backend='translucent'; return
        try:
            from ctypes import wintypes
            hwnd=wintypes.HWND(int(self.winId())); dwm=ctypes.windll.dwmapi
            class Margins(ctypes.Structure):_fields_=[('left',ctypes.c_int),('right',ctypes.c_int),('top',ctypes.c_int),('bottom',ctypes.c_int)]
            margins=Margins(-1,-1,-1,-1); dwm.DwmExtendFrameIntoClientArea(hwnd,ctypes.byref(margins))
            class Blur(ctypes.Structure):_fields_=[('flags',wintypes.DWORD),('enabled',wintypes.BOOL),('region',wintypes.HRGN),('transition',wintypes.BOOL)]
            blur=Blur(1,True,None,False); dwm.DwmEnableBlurBehindWindow(hwnd,ctypes.byref(blur))
            corner=ctypes.c_int(2); dwm.DwmSetWindowAttribute(hwnd,33,ctypes.byref(corner),4)
            backdrop=ctypes.c_int(3)
            result=dwm.DwmSetWindowAttribute(hwnd,38,ctypes.byref(backdrop),4)
            self.glass_backend='desktop-acrylic' if result==0 else 'translucent'
            # Transparent blur works for non-activating tool windows where
            # the system backdrop otherwise resolves to an opaque tint.
            try:
                class Accent(ctypes.Structure):_fields_=[('state',ctypes.c_int),('flags',ctypes.c_int),('color',wintypes.DWORD),('animation',ctypes.c_int)]
                class CompositionData(ctypes.Structure):_fields_=[('attribute',ctypes.c_int),('data',ctypes.c_void_p),('size',ctypes.c_size_t)]
                accent=Accent(3,0,0,0)
                data=CompositionData(19,ctypes.cast(ctypes.pointer(accent),ctypes.c_void_p),ctypes.sizeof(accent))
                apply=u.SetWindowCompositionAttribute
                apply.argtypes=[wintypes.HWND,ctypes.POINTER(CompositionData)]; apply.restype=wintypes.BOOL
                no_backdrop=ctypes.c_int(1); dwm.DwmSetWindowAttribute(hwnd,38,ctypes.byref(no_backdrop),4)
                if apply(hwnd,ctypes.byref(data)):self.glass_backend='windows-blur'
                else:dwm.DwmSetWindowAttribute(hwnd,38,ctypes.byref(backdrop),4)
            except (OSError,AttributeError):pass
        except (OSError,AttributeError):self.glass_backend='translucent'
        for child in self.findChildren(W.QWidget):child.setMouseTracking(True); child.installEventFilter(self)
    def eventFilter(self,obj,event):
        if event.type()==C.QEvent.MouseMove:
            self.glass_light=C.QPointF(self.mapFromGlobal(event.globalPosition().toPoint())); self.update()
        return super().eventFilter(obj,event)
    def mouseMoveEvent(self,event):self.glass_light=event.position(); self.update(); super().mouseMoveEvent(event)
    def paintEvent(self,event):
        painter=G.QPainter(self); paint_glass(painter,self.rect(),getattr(self,'glass_light',None))

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

class HUD(GlassPanel):
    def __init__(self,owner):
        super().__init__(None,C.Qt.Tool|C.Qt.FramelessWindowHint|C.Qt.WindowStaysOnTopHint|C.Qt.WindowDoesNotAcceptFocus)
        self.owner=owner
        self.ui_scale=1.6
        self.setFixedSize(round(675*self.ui_scale),round(48*self.ui_scale))
        self.swatches=[['#000000','#7f7f7f','#880015','#ed1c24','#ff7f27','#fff200','#22b14c','#00a2e8','#3f48cc','#a349a4'],['#ffffff','#c3c3c3','#b97a57','#ffaec9','#ffc90e','#efe4b0','#b5e61d','#99d9ea','#7092be','#c8bfe7'],['#24334c','#476385','#6b91b8','#77bfa3','#e47856','#e7b66a','#8e78bb','#78b6c8','#b6c4d8','#e6ebf2']]
        self.tool_buttons={}; self.colors={}; self.hotspots=[]
        self.setStyleSheet('QPushButton {border:0;background:transparent;padding:0;border-radius:8px;} QPushButton:hover {background:rgba(255,255,255,130);border:1px solid rgba(255,255,255,220);} QPushButton:pressed {background:rgba(130,190,250,100);}')
        def hit(rect,tip,callback=None,key=None):
            button=W.QPushButton(self); button.setGeometry(*(round((v+12 if i==0 else v)*self.ui_scale) for i,v in enumerate(rect))); button.setToolTip(tip); button.setAccessibleName(tip)
            if callback:button.clicked.connect(callback)
            else:button.setToolTip(tip+' — пока недоступно'); button.setProperty('unavailable',True)
            if key:
                button.setCheckable(True); self.tool_buttons[key]=button
            self.hotspots.append(button)
            return button
        hit((1,1,23,33),'Вставить · Ctrl+V',owner.prepare_paste)
        hit((25,1,26,11),'Вырезать · Ctrl+X',lambda:owner.copy_selection(True))
        hit((25,13,26,11),'Копировать · Ctrl+C',owner.copy_selection)
        hit((55,1,22,33),'Выделение',lambda:owner.select_tool('select'),'select')
        for rect,title in [((78,1,34,11),'Обрезать'),((78,12,34,11),'Изменить размер'),((78,23,34,11),'Повернуть')]:hit(rect,title)
        hit((118,2,13,16),'Кисть',lambda:owner.select_tool('brush'),'brush')
        hit((131,2,13,16),'Заливка',lambda:owner.select_tool('fill'),'fill')
        hit((144,2,12,16),'Текст')
        hit((118,18,13,15),'Ластик',lambda:owner.select_tool('eraser'),'eraser')
        hit((131,18,13,15),'Пипетка',owner.pick_color)
        hit((144,18,12,15),'Масштаб')
        hit((159,1,24,33),'Кисть',lambda:owner.select_tool('brush'))
        for i in range(7):
            for j in range(3):
                tools={(0,0):('line','Линия'),(2,0):('ellipse','Эллипс'),(3,0):('rect','Прямоугольник'),(6,0):('triangle','Треугольник')}
                pair=tools.get((i,j))
                hit((188+i*10,2+j*10,10,10),pair[1] if pair else 'Фигура', (lambda checked=False,k=pair[0]:owner.select_tool(k)) if pair else None,pair[0] if pair else None)
        hit((273,1,38,12),'Контур',lambda:owner.set_shape_fill(False))
        hit((273,14,38,13),'Заливка фигуры',lambda:owner.set_shape_fill(True))
        hit((313,1,24,33),'Размер кисти / ластика',self.size_menu)
        hit((340,1,21,34),'Основной цвет',self.choose_color)
        hit((362,1,20,34),'Дополнительный цвет',self.choose_color)
        for col in range(10):
            for row in range(3):
                x,y=384+col*11,2+row*11
                color=self.swatches[row][col]
                b=hit((x,y,11,11),color,lambda checked=False,c=color:owner.set_value('color',c)); self.colors[color]=b
        hit((496,1,22,34),'Изменить цвет',self.choose_color)
        hit((520,1,29,34),'Скриншот · Ctrl+Alt+S',owner.screenshot)
        self.animation=C.QPropertyAnimation(self,b'windowOpacity'); self.animation.setDuration(160); self.animation.setEasingCurve(C.QEasingCurve.OutCubic)
    def size_menu(self):
        menu=W.QMenu(self)
        for key,title,values in [('width','Кисть',[1,2,3,5,8,12,16,24,32,40]),('eraser','Ластик',[4,8,12,20,28,40,56,72,88,100])]:
            sub=menu.addMenu(title)
            for value in values:
                action=sub.addAction(str(value)+' px'); action.setCheckable(True); action.setChecked(value==self.owner.cfg[key]); action.triggered.connect(lambda checked=False,k=key,v=value:self.owner.set_value(k,v))
        menu.exec(self.mapToGlobal(C.QPoint(round(325*self.ui_scale),round(34*self.ui_scale))))
    def choose_color(self):
        color=W.QColorDialog.getColor(G.QColor(self.owner.cfg['color']),self)
        if color.isValid():self.owner.set_value('color',color.name())
    def refresh(self):
        for key,b in self.tool_buttons.items():b.setChecked(key==self.owner.drawing_tool)
        self.update()
    def paintEvent(self,event):
        p=G.QPainter(self); p.setRenderHint(G.QPainter.Antialiasing); p.setRenderHint(G.QPainter.TextAntialiasing)
        p.scale(self.ui_scale,self.ui_scale)
        light=getattr(self,'glass_light',None)
        paint_glass(p,C.QRectF(0,0,675,48),light/self.ui_scale if light else None)
        p.translate(12,0)
        font=G.QFont('Segoe UI'); font.setPixelSize(6); p.setFont(font)
        def text(rect,title,color='#17273d'):
            p.setPen(G.QColor(color)); p.drawText(C.QRectF(*rect),C.Qt.AlignCenter,title)
        def icon(kind,x,y,w=12,h=12):
            p.save(); p.translate(x,y); p.scale(w/24,h/24); draw_action(p,kind); p.restore()
        for x in (53,115,157,185,311,338,383,495,519,550):
            p.setPen(G.QPen(G.QColor(255,255,255,120),.5)); p.drawLine(C.QPointF(x,1),C.QPointF(x,44))
        for x,w,title in [(1,51,'Clipboard'),(54,60,'Image'),(116,41,'Tools'),(158,27,'Brushes'),(186,125,'Shapes'),(312,26,'Size'),(339,180,'Colors')]:text((x,36,w,9),title,'#43566f')
        # Highlight follows the selected tool, rather than a baked-in screenshot.
        selected=self.tool_buttons.get(self.owner.drawing_tool)
        if selected:
            r=selected.geometry(); r=C.QRectF(r.x()/self.ui_scale,r.y()/self.ui_scale,r.width()/self.ui_scale,r.height()/self.ui_scale)
            p.setBrush(G.QColor(90,170,255,65)); p.setPen(G.QPen(G.QColor(255,255,255,210),.7)); p.drawRoundedRect(r.adjusted(.7,.7,-.7,-.7),4,4)
        icon('paste',5,2,15,18); text((1,22,23,8),'Paste'); text((7,29,10,5),'▾')
        icon('cut',25,2,7,8); text((32,1,19,10),'Cut')
        icon('copy',25,14,7,8); text((32,13,19,10),'Copy')
        icon('select',57,2,17,15); text((55,20,22,10),'Select'); text((61,28,10,5),'▾')
        for y,title,glyph in [(1,'Crop','⌗'),(12,'Resize','▱'),(23,'Rotate','↶')]:
            text((78,y,9,10),glyph,'#a4aab3'); text((86,y,28,10),title,'#9aa3ae')
        for kind,x,y in [('brush',119,3),('fill',132,3),('select',119,20)]:icon(kind,x,y,10,10)
        text((144,3,11,11),'A','#9aa3ae'); text((132,20,10,10),'⌖'); text((144,20,11,10),'⌕','#9aa3ae')
        icon('brush',162,2,18,19); text((159,22,24,9),'Brushes'); text((166,30,10,5),'▾')
        for i in range(7):
            for j in range(3):
                rect=C.QRectF(190+i*10,4+j*10,7,6)
                supported={(0,0):'line',(2,0):'ellipse',(3,0):'rect',(6,0):'triangle'}
                kind=supported.get((i,j)); p.setBrush(C.Qt.NoBrush); p.setPen(G.QPen(G.QColor('#243e60' if kind else '#b6c1cd'),.65))
                if kind=='line':p.drawLine(rect.topLeft(),rect.bottomRight())
                elif kind=='ellipse':p.drawEllipse(rect)
                elif kind=='triangle':p.drawPolygon(G.QPolygonF([C.QPointF(rect.center().x(),rect.top()),rect.bottomLeft(),rect.bottomRight()]))
                elif kind=='rect':p.drawRect(rect)
                elif j==1:p.drawPolygon(G.QPolygonF([C.QPointF(rect.center().x(),rect.top()),C.QPointF(rect.right(),rect.center().y()),C.QPointF(rect.center().x(),rect.bottom()),C.QPointF(rect.left(),rect.center().y())]))
                else:p.drawRoundedRect(rect,1.5,1.5)
        icon('rect',274,3,8,8); text((283,1,27,11),'Outline ▾')
        icon('fill',274,15,8,8); text((283,14,27,11),'Fill ▾')
        for i,width in enumerate((.7,1.2,2,3)):
            p.setPen(G.QPen(G.QColor('#32465e'),width)); p.drawLine(C.QPointF(316,4+i*5),C.QPointF(334,4+i*5))
        text((315,25,22,8),'Size ▾')
        for x,title,color in [(340,'Color 1',self.owner.cfg['color']),(362,'Color 2','#ffffff')]:
            p.setPen(G.QPen(G.QColor('#9aaabf'),.6)); p.setBrush(G.QColor(color)); p.drawRect(C.QRectF(x+3,3,15,15)); text((x,20,21,13),title.replace(' ','\n'))
        p.setBrush(C.Qt.NoBrush)
        for row,colors in enumerate(self.swatches):
            for col,color in enumerate(colors):
                rect=C.QRectF(385+col*11,3+row*11,9,9); p.setPen(G.QPen(G.QColor(255,255,255,170),.55)); p.setBrush(G.QColor(color)); p.drawRoundedRect(rect,2,2); p.setBrush(C.Qt.NoBrush)
                if color.lower()==self.owner.cfg['color'].lower():p.setPen(G.QPen(G.QColor('#2684e3'),1)); p.drawRoundedRect(rect.adjusted(-.8,-.8,.8,.8),2.5,2.5)
        gradient=G.QLinearGradient(497,3,514,18)
        for at,color in [(0,'#ff5252'),(.25,'#ffdf4b'),(.5,'#4ad687'),(.75,'#45b8ed'),(1,'#ab68dd')]:gradient.setColorAt(at,G.QColor(color))
        p.fillRect(C.QRectF(499,3,15,15),gradient); text((496,20,22,14),'Edit\ncolors')
        icon('camera',525,3,18,18); text((520,22,29,11),'Capture')
        font.setPixelSize(9); font.setBold(True); p.setFont(font); text((556,7,90,16),'Paint Overlay','#193c5d')
        font.setPixelSize(6); font.setBold(False); p.setFont(font); text((556,25,90,10),'Ctrl+D · Mouse3','#7b8b9e')
    def open(self):PalettePanelBase.open(self)
    def dismiss(self):PalettePanelBase.dismiss(self)

class HotkeyFilter(C.QAbstractNativeEventFilter):
    def __init__(self,owner):super().__init__(); self.owner=owner
    def nativeEventFilter(self,event_type,message):
        from ctypes import wintypes
        msg=wintypes.MSG.from_address(int(message))
        if msg.message==0x0312 and msg.wParam in (712,713,714,715,716,717,718,719):
            if msg.wParam==712:self.owner.toggle_mode()
            return True,0
        return False,0

class App:
    def __init__(self):
        self.cfg=dict(color='#ff3434',width=5,eraser=28,shield=False)
        try:self.cfg.update({k:v for k,v in json.loads(SETTINGS.read_text()).items() if k in self.cfg})
        except (OSError,ValueError):pass
        self.moving=False; self.resizing=False; self.resize_anchor=None; self.move_image=None; self.move_rect=None
        self.shape_filled=False; self.drawing_tool='brush'; self.anchor=None; self.base_image=None; self.paste_image=None
        self.enabled=True; self.previous=None; self.tool=None; self.capturing=False; self.last_screenshot=None
        self.overlay=Overlay(); self.panel=CursorPalette(self); self.dock=HUD(self)
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
        self.overlay.selection=None
        self.overlay.checkpoint(); self.overlay.clear(); self.previous=None; self.tool=None
    def undo(self):
        self.overlay.selection=None; self.moving=False
        self.overlay.undo(); self.previous=None; self.tool=None
    def redo(self):
        self.overlay.selection=None; self.moving=False
        self.overlay.redo(); self.previous=None; self.tool=None
    def screenshot(self):
        if self.capturing:return
        self.capturing=True
        visible=[w for w in (self.panel,self.dock,self.overlay) if w.isVisible()]
        for widget in visible:widget.hide()
        def capture():
            try:
                result=G.QImage(self.overlay.size(),G.QImage.Format_ARGB32_Premultiplied); result.fill(C.Qt.black)
                painter=G.QPainter(result)
                for screen in G.QGuiApplication.screens():
                    shot=screen.grabWindow(0)
                    if shot.isNull():raise RuntimeError('Не удалось захватить экран')
                    rect=screen.geometry().translated(-self.overlay.geometry().topLeft())
                    painter.drawPixmap(rect,shot)
                painter.drawImage(0,0,self.overlay.image); painter.end()
                folder=Path(C.QStandardPaths.writableLocation(C.QStandardPaths.PicturesLocation))/APP
                folder.mkdir(parents=True,exist_ok=True)
                filename=folder/('Paint Overlay '+C.QDateTime.currentDateTime().toString('yyyy-MM-dd HH-mm-ss-zzz')+'.png')
                if not result.save(str(filename),'PNG'):raise RuntimeError('Не удалось сохранить файл')
                self.last_screenshot=filename
                self.tray.showMessage(APP,'Скриншот сохранён: '+str(filename),W.QSystemTrayIcon.Information,5000)
            except Exception as error:W.QMessageBox.warning(None,APP,str(error))
            finally:
                for widget in reversed(visible):widget.show(); widget.raise_()
                self.capturing=False
        C.QTimer.singleShot(150,capture)
    def enable(self,value):self.enabled=value; self.previous=None; self.apply_mode()
    def apply_mode(self):
        shield=self.cfg['shield'] and self.enabled
        for ident in (715,716,717,718,719):u.UnregisterHotKey(None,ident)
        u.UnregisterHotKey(None,713); u.UnregisterHotKey(None,714)
        if shield:
            for ident,vk in ((715,0x43),(716,0x56),(717,0x58)):u.RegisterHotKey(None,ident,0x4002,vk)
            u.RegisterHotKey(None,718,0x4000,0x2E)
            u.RegisterHotKey(None,719,0x4000,0x1B)
            u.RegisterHotKey(None,713,0x4002,0x5A)
            u.RegisterHotKey(None,714,0x4006,0x5A)
        self.previous=None; self.tool=None
        self.overlay.setWindowFlag(C.Qt.WindowTransparentForInput,not shield); self.overlay.shield=shield
        self.overlay.setCursor(C.Qt.CrossCursor if shield else C.Qt.ArrowCursor); self.overlay.show(); self.overlay.update()
        if shield:
            area=(G.QGuiApplication.screenAt(G.QCursor.pos()) or G.QGuiApplication.primaryScreen()).availableGeometry()
            self.dock.move(area.center().x()-self.dock.width()//2,area.top()+14); self.dock.open()
        else:self.dock.dismiss(); self.panel.dismiss()
        if self.panel.isVisible():self.panel.raise_()
    def toggle_mode(self):self.set_value('shield',not self.cfg['shield']); self.panel.dismiss(); self.apply_mode()
    def leave_layer(self):
        if self.cfg['shield']:self.toggle_mode()
    def toggle_panel(self):
        if not self.overlay.shield:return
        if self.panel.isVisible():self.panel.dismiss(); return
        pos=G.QCursor.pos(); area=(G.QGuiApplication.screenAt(pos) or G.QGuiApplication.primaryScreen()).availableGeometry()
        self.panel.move(max(area.left(),min(pos.x()+14,area.right()-self.panel.width())),max(area.top(),min(pos.y()+14,area.bottom()-self.panel.height())))
        self.panel.open()
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
        self.drawing_tool='picker'
    def select_tool(self,key):
        self.drawing_tool=key; self.previous=None; self.anchor=None
        self.dock.refresh()
    def prepare_paste(self):
        image=W.QApplication.clipboard().image()
        if not image.isNull():self.paste_image=image
    def copy_selection(self,cut=False):
        if not self.overlay.selection:return
        rect=self.overlay.selection.toAlignedRect().intersected(self.overlay.image.rect())
        W.QApplication.clipboard().setImage(self.overlay.image.copy(rect))
        if cut:
            self.overlay.checkpoint(); painter=G.QPainter(self.overlay.image); painter.setCompositionMode(G.QPainter.CompositionMode_Clear); painter.fillRect(rect,C.Qt.transparent); painter.end(); self.overlay.update()
    def delete_selection(self):
        if not self.overlay.selection:return
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
    def tick(self):
        if self.capturing:return
        key=lambda k:bool(u.GetAsyncKeyState(k)&0x8000)
        modifier=key(0x11) and key(0x12)
        self.repeat_history('redo' if key(0x10) else 'undo', key(0x11) and key(0x5A))
        if self.edge('clear',modifier and key(0x08)):self.clear()
        if self.edge('clear_layer',modifier and key(0x45)) and self.overlay.shield:self.clear()
        if self.edge('shot',modifier and key(0x53)):self.screenshot(); return
        if self.edge('panel',key(4)) and self.overlay.shield:self.toggle_panel()
        if self.edge('mode',modifier and key(0x44)):self.toggle_mode()
        if self.edge('esc',key(0x1b)):
            self.panel.dismiss()
            if self.overlay.selection:self.overlay.selection=None; self.overlay.update()
            else:self.leave_layer()
        if self.overlay.shield:
            if self.edge('delete',key(0x2E)):self.delete_selection()
            if self.edge('copy',key(0x11) and key(0x43)):self.copy_selection()
            if self.edge('cut',key(0x11) and key(0x58)):self.copy_selection(True)
            if self.edge('paste',key(0x11) and key(0x56)):
                image=W.QApplication.clipboard().image()
                if not image.isNull():self.paste_image=image
        pos=G.QCursor.pos()
        over_ui=any(w.isVisible() and w.frameGeometry().contains(pos) for w in (self.panel,self.dock))
        shield=self.overlay.shield
        tool=('eraser' if key(2) else (('eraser' if self.drawing_tool=='eraser' else 'brush') if key(1) else None)) if shield else None
        if self.tool=='paste' and key(1):return
        if not self.enabled or over_ui or W.QWidget.mouseGrabber() is not None:tool=None
        if tool:
            point=C.QPointF(self.overlay.mapFromGlobal(pos))
            fresh=self.previous is None or self.tool!=tool
            if fresh:
                self.panel.dismiss(); self.overlay.checkpoint(); self.anchor=point; self.base_image=G.QImage(self.overlay.image)
                self.moving=False; self.resizing=False
                corner=None
                if self.drawing_tool=='select' and self.overlay.selection:
                    r=self.overlay.selection
                    for near,opposite in [(r.topLeft(),r.bottomRight()),(r.topRight(),r.bottomLeft()),(r.bottomLeft(),r.topRight()),(r.bottomRight(),r.topLeft())]:
                        if abs(point.x()-near.x())<=8 and abs(point.y()-near.y())<=8:corner=opposite; break
                if self.drawing_tool=='select' and self.overlay.selection and (corner is not None or self.overlay.selection.contains(point)):
                    self.resizing=corner is not None; self.resize_anchor=corner
                    self.moving=True; self.move_rect=self.overlay.selection.toAlignedRect(); self.move_rect=C.QRectF(self.move_rect)
                    self.move_image=self.overlay.image.copy(self.move_rect.toAlignedRect())
                    painter=G.QPainter(self.base_image); painter.setCompositionMode(G.QPainter.CompositionMode_Clear); painter.fillRect(self.move_rect,C.Qt.transparent); painter.end()
                elif self.drawing_tool=='select':self.overlay.selection=None
                if self.paste_image is not None:
                    painter=G.QPainter(self.overlay.image); painter.drawImage(point,self.paste_image); painter.end(); self.overlay.selection=C.QRectF(point,C.QSizeF(self.paste_image.size())); self.drawing_tool='select'; self.paste_image=None; self.overlay.update(); self.previous=point; self.tool='paste'; return
            prev=self.previous if self.tool==tool and self.previous is not None else point
            if tool=='eraser' or self.drawing_tool=='brush':self.overlay.segment(prev,point,self.cfg['color'],self.cfg['eraser'] if tool=='eraser' else self.cfg['width'],tool=='eraser')
            elif self.drawing_tool=='picker':
                if fresh:
                    color=self.overlay.image.pixelColor(point.toPoint())
                    if color.alpha():self.set_value('color',color.name())
                    self.select_tool('brush')
            elif self.drawing_tool=='fill':
                if fresh:self.bucket(point)
            else:
                self.overlay.image=G.QImage(self.base_image); self.shape(self.anchor,point,key(0x10))
            self.previous=point
        else:
            self.previous=None; self.moving=False
        if shield and self.drawing_tool=='select':
            local=C.QPointF(self.overlay.mapFromGlobal(pos)); self.overlay.setCursor(C.Qt.SizeAllCursor if self.overlay.selection and self.overlay.selection.contains(local) else C.Qt.CrossCursor)
        self.tool=tool

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
