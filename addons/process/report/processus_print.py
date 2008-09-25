# -*- encoding: utf-8 -*-
import Image
import ImageDraw
import ImageFont
import math

import addons

ROUNDED = 30
BGCOLOR = (228,233,237)
TITLECOLOR = (150,70,70)
FONT = addons.get_module_resource('processus', 'report/sb.ttf')
BOXSIZE = (160,120)

size = 800,600

class draw(object):
    def _rounding_box(self, x, y, width, height, title=None, bgcolor=BGCOLOR):
        d = ImageDraw.Draw(self.img)
        DR = ROUNDED/2
        d.polygon( (x+DR,y,x+width-DR,y,x+width,y+DR,x+width,y+height-DR,x+width-DR,y+height,x+DR,y+height,x,y+height-DR,x,y+DR), fill=bgcolor)
        d.pieslice((x,y,x+ROUNDED,y+ROUNDED),180,270,fill=bgcolor)
        d.pieslice((x+width-ROUNDED,y,x+width,y+ROUNDED),270,0,fill=title and TITLECOLOR or bgcolor)
        d.pieslice((x+width-ROUNDED,y+height-ROUNDED,x+width,y+height),0,90,fill=bgcolor)
        d.pieslice((x,y+height-ROUNDED,x+ROUNDED,y+height),90,180,fill=bgcolor)
        if title:
            d.polygon( (x+width/5, y, x+width-DR, y, x+width, y+DR, x+width, y+20, x+width/5+15, y+20), fill=TITLECOLOR)
            self.draw_text(x+width/5+13, y+4, 10, title, (255,255,255), width*4/5-14)

    def node(self, x, y, width, height, title=None, start_color=BGCOLOR):
        self._rounding_box(x,y,BOXSIZE[0]-16,BOXSIZE[1], bgcolor=start_color)
        self._rounding_box(x+12,y,BOXSIZE[0]-16,BOXSIZE[1], bgcolor=(255,255,255))
        self._rounding_box(x+16,y,BOXSIZE[0]-16,BOXSIZE[1], title)

    def angle(self, arrow):
        if not arrow[1]-arrow[3]:
            angle = 180
        else:
            angle = math.atan(-(arrow[2]-arrow[0]) / (arrow[1]-arrow[3])) * 180 / math.pi
            angle = 270 - angle
            if arrow[3]<arrow[1]:
                angle = 180 + angle
        return int(angle)

    def arrow(self, arrow):
        d = ImageDraw.Draw(self.img)
        d.line(arrow, width=1, fill=(0,0,0))
        angle = self.angle(arrow)
        d.pieslice((arrow[2]-14,arrow[3]-14,arrow[2]+14,arrow[3]+14),angle-18,angle+18,fill=(0,0,0))

    def draw_text(self, x, y, size, title, color=(155,255,255), maxlength=None, font_name=FONT, center=False):
        d = ImageDraw.Draw(self.img)
        font = ImageFont.truetype(font_name, size)
        d.setfont(font)
        size2 = d.textsize(title)
        if maxlength:
            fontsize = min(size, size * maxlength / size2[0])
            font = ImageFont.truetype(font_name, fontsize)
            d.setfont(font)
        size = d.textsize(title)
        if center:
            x = x-size[0]/2
        d.text( (x, y+(size2[1]-size[1])/2), title, color)

    def arrow_role(self, node_from, node_to, role='Hello'):
        d = ImageDraw.Draw(self.img)
        x = (node_from[0] + node_to[0]) /2
        y = (node_from[1] + node_to[1]) /2
        angle = self.angle(node_from+node_to) + 105
        d.pieslice((x-40,y-40,x+40,y+40),angle-5,angle+5,fill=(100,0,0))
        d.pieslice((x-6,y-6,x+6,y+6),angle-7,angle+7,fill=(255,255,255))

        print -180 + angle - 90
        x = x + math.cos(angle * math.pi / 180) * 40
        y = y + math.sin(angle * math.pi / 180) * 40
        a,b = x,y
        angle -= 120

        x = x + math.cos(angle * math.pi / 180) * 20
        y = y + math.sin(angle * math.pi / 180) * 20

        d.line((a,b,x,y), width=5, fill=(100,0,0))
        angle += 125
        d.pieslice((x-30,y-30,x+30,y+30),angle-7,angle+7,fill=(100,0,0))

        x = x + math.cos(angle * math.pi / 180) * 50
        y = y + math.sin(angle * math.pi / 180) * 50
        return (x,y)

    def picture(self, x, y, fname):
        img = Image.open(fname)
        img2 = img.convert('RGBA')
        self.img.paste(img2, (max(0,x-img.size[0]/2), max(0,y-img.size[1])), mask=img2)

    def __init__(self, img):
        self.img = img

class graph(object):
    def __init__(self, img):
        self.draw = draw(img)

    def intersect_one(self, start, stop):
        if start[0] < stop[0]:
            x1 = start[0] + BOXSIZE[0]/2 + 3
        else:
            x1 = start[0] - BOXSIZE[0]/2 - 3
        if not start[0]-stop[0]:
            y1 = 99999999999999
        else:
            y1 = start[1] - (start[1] - stop[1]) * (start[0]-x1) / (start[0] - stop[0])

        if start[1] < stop[1]:
            y2 = start[1] + BOXSIZE[1]/2 + 3
        else:
            y2 = start[1] - BOXSIZE[1]/2 - 3
        if not start[1]-stop[1]:
            x2 = 99999999999999
        else:
            x2 = start[0] - (start[0] - stop[0]) * (start[1]-y2) / (start[1] - stop[1])

        if abs(start[0]-x1)+abs(start[1]-y1)<abs(start[0]-x2)+abs(y2-start[1]):
            return (x1,y1)
        return (x2,y2)

    def intersect(self, start, stop):
        s = self.intersect_one(start,stop)
        s2 = self.intersect_one(stop,start)
        return s+s2

    def node(self, x, y, data, start_color=False):
        self.draw.node(x,y,BOXSIZE[0], BOXSIZE[1], data.get('title','Unknown'), start_color and (255,125,125) or BGCOLOR)
        self.draw.picture(x+35, y+BOXSIZE[1]-5, addons.get_module_resource('processus', 'report/gtk-help.png'))
        if start_color:
            self.draw.picture(x+65, y+BOXSIZE[1]-5, addons.get_module_resource('processus', 'report/gtk-open.png'))
            self.draw.picture(x+95, y+BOXSIZE[1]-5, addons.get_module_resource('processus', 'report/gtk-print.png'))
        y = y+25
        menus = data.get('menu','').split('/')
        while menus:
            menu = menus.pop(0)
            if menu:
                if menus: menu=menu+' /'
                self.draw.draw_text(x+23, y, 10, menu, color=(0,0,0), maxlength=BOXSIZE[0] - 25, 
                    font_name=addons.get_module_resource('processus', 'report/ds.ttf'))
                y+=15

    def arrow_role(self, node_from, node_to, role='Hello'):
        start = (node_from[0]+BOXSIZE[0]/2, node_from[1]+BOXSIZE[1]/2)
        stop = (node_to[0]+BOXSIZE[0]/2, node_to[1]+BOXSIZE[1]/2)
        (x,y) = self.draw.arrow_role(start, stop, role)
        self.draw.picture(x, y-3, addons.get_module_resource('processus', 'report/role.png'))
        self.draw.draw_text(x,y-3, 12, 'Salesman', color=(0,0,0), center=True)

    def arrow(self, node_from, node_to):
        start = (node_from[0]+BOXSIZE[0]/2, node_from[1]+BOXSIZE[1]/2)
        stop = (node_to[0]+BOXSIZE[0]/2, node_to[1]+BOXSIZE[1]/2)
        arrow = self.intersect(start,stop)
        self.draw.arrow(arrow)

if __name__=='__main__':
    img = Image.new('RGB',size,'#ffffff')
    g = graph(img)
    g.node(50,100,{'title':'SALE AZER ORDER', 'menu':'Sales Management/Sales Orders/My Sales Order/My Open Sales Order'}, start_color=(200,100,100))
    g.node(350,150,{'title':'SALE AZER AZE ORDER', 'menu':'Sales Management/Sales Orders/My Quotations'})
    g.arrow((50,100),(350,150))

    g.arrow_role((50,100),(350,150))

    #img.show()
    img.save('a.pdf')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

