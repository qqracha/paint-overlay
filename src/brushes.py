"""Vector and raster brush primitives shared by canvas and brush chooser."""
import math
import random
from PySide6 import QtCore as C, QtGui as G

BRUSHES = (
    ('round', 'Кисть'), ('calligraphy', 'Каллиграфия I'),
    ('calligraphy_reverse', 'Каллиграфия II'), ('airbrush', 'Аэрограф'),
    ('oil', 'Масло'), ('crayon', 'Мелок'), ('marker', 'Маркер'),
    ('pencil', 'Карандаш'), ('watercolor', 'Акварель'),
)

def draw_segment(image, start, end, color, width, kind='round'):
    p=G.QPainter(image); p.setRenderHint(G.QPainter.Antialiasing)
    color=G.QColor(color); distance=math.hypot(end.x()-start.x(),end.y()-start.y())
    if kind in ('round','pencil','oil','marker'):
        actual=max(1.,width*.24) if kind=='pencil' else width
        if kind=='marker':color.setAlpha(92)
        cap=C.Qt.SquareCap if kind=='marker' else C.Qt.RoundCap
        p.setPen(G.QPen(color,actual,C.Qt.SolidLine,cap,C.Qt.RoundJoin))
        if start==end:p.drawPoint(start)
        else:p.drawLine(start,end)
        if kind=='oil':
            thin=color.lighter(125); thin.setAlpha(105); p.setPen(G.QPen(thin,max(.5,width*.07),C.Qt.SolidLine,C.Qt.RoundCap))
            for offset in (-.28,-.08,.2):p.drawLine(start+C.QPointF(0,width*offset),end+C.QPointF(0,width*offset))
    else:
        steps=max(1,min(2000,math.ceil(distance/max(1,width*.17))))
        for i in range(steps+1):
            pos=start+(end-start)*(i/steps)
            if kind.startswith('calligraphy'):
                p.save(); p.translate(pos); p.rotate(40 if kind=='calligraphy' else -40)
                p.setPen(C.Qt.NoPen); p.setBrush(color); p.drawEllipse(C.QRectF(-width*.5,-max(1,width*.12),width,max(2,width*.24))); p.restore()
            elif kind=='crayon':
                seed=int(pos.x()*73856093)^int(pos.y()*19349663)
                rng=random.Random(seed); grain=G.QColor(color); grain.setAlpha(150); p.setPen(C.Qt.NoPen); p.setBrush(grain)
                for _ in range(max(3,min(25,int(width)))):
                    dx=rng.uniform(-width/2,width/2); dy=rng.uniform(-width/2,width/2)
                    if dx*dx+dy*dy<=width*width/4:p.drawEllipse(pos+C.QPointF(dx,dy),.65,.65)
            else:
                radius=max(2,width*(1.1 if kind=='airbrush' else .7))
                center=G.QColor(color); center.setAlpha(36 if kind=='airbrush' else 23)
                edge=G.QColor(color); edge.setAlpha(0)
                gradient=G.QRadialGradient(pos,radius); gradient.setColorAt(0,center); gradient.setColorAt(1,edge)
                p.setPen(C.Qt.NoPen); p.setBrush(gradient); p.drawEllipse(pos,radius,radius)
    p.end()

def brush_icon(kind):
    image=G.QImage(112,72,G.QImage.Format_ARGB32_Premultiplied); image.fill(C.Qt.transparent)
    points=[C.QPointF(12+i*4,36+math.sin(i/5)*10) for i in range(23)]
    for start,end in zip(points,points[1:]):draw_segment(image,start,end,'#304c69',10,kind)
    return G.QIcon(G.QPixmap.fromImage(image))
