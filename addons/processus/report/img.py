import Image
import ImageDraw
import ImageFont

ROUNDED = 30
BGCOLOR = (228,233,237)
TITLECOLOR = (253,171,44)
FONT = 'sb.ttf'
BOXSIZE = (300,140)

size = 800,600
img = Image.new('RGB',size,'#ffffff')

class draw(object):
	def rounding_box(self, x, y, width, height, title=None, bgcolor=BGCOLOR):
		d = ImageDraw.Draw(self.img)

		DR = ROUNDED/2
		d.polygon( (x+DR,y,x+width-DR,y,x+width,y+DR,x+width,y+height-DR,x+width-DR,y+height,x+DR,y+height,x,y+height-DR,x,y+DR), fill=bgcolor)
		if title:
			d.polygon( (x+width/3, y, x+width-DR, y, x+width, y+DR, x+width, y+30, x+width/3+30, y+30), fill=TITLECOLOR)
			self.draw_text(x+width/3+30, y+3, 20, title, (255,255,255), width*2/3-40)

		d.pieslice((x,y,x+ROUNDED,y+ROUNDED),180,270,fill=bgcolor)
		d.pieslice((x+width-ROUNDED,y,x+width,y+ROUNDED),270,0,fill=title and TITLECOLOR or bgcolor)
		d.pieslice((x+width-ROUNDED,y+height-ROUNDED,x+width,y+height),0,90,fill=bgcolor)
		d.pieslice((x,y+height-ROUNDED,x+ROUNDED,y+height),90,180,fill=bgcolor)

	def intersect(self, start, stop):
		x1 = start[0] + BOXSIZE[0]/2
		y1 = start[1] - (start[1] - stop[1]) * (start[0]-x1) / (start[0] - stop[0])
		return (x1,y1,stop[0],stop[1])

	def arrow(self, start, stop):
		d = ImageDraw.Draw(self.img)
		start = (start[0]+BOXSIZE[0]/2, start[1]+BOXSIZE[1]/2)
		stop = (stop[0]+BOXSIZE[0]/2, stop[1]+BOXSIZE[1]/2)
		arrow = self.intersect(start,stop)

		d.line(arrow, width=10, fill=(100,0,0))

	def draw_text(self, x, y, size, title, color=(155,255,255), maxlength=None, font_name=FONT):
		d = ImageDraw.Draw(self.img)
		font = ImageFont.truetype(font_name, size)
		d.setfont(font)
		size2 = d.textsize(title)
		fontsize = min(size, size * maxlength / size2[0])
		font = ImageFont.truetype(font_name, fontsize)
		d.setfont(font)
		size = d.textsize(title)
		d.text( (x, y+(size2[1]-size[1])/2), title, color)

	def __init__(self, img):
		self.img = img

class graph(object):
	def __init__(self, img):
		self.draw = draw(img)

	def node(self, x, y, data, start_color=BGCOLOR):
		self.draw.rounding_box(x-20,y,BOXSIZE[0],BOXSIZE[1], bgcolor=start_color)
		self.draw.rounding_box(x-4,y,BOXSIZE[0],BOXSIZE[1], bgcolor=(255,255,255))
		self.draw.rounding_box(x,y,BOXSIZE[0],BOXSIZE[1],data.get('title','Unknown'))

	def arrow(self, node_from, node_to):
		self.draw.arrow(node_from,node_to)

g = graph(img)
g.node(50,50,{'title':'SALE AZER ORDER'}, start_color=(200,100,100))
g.node(450,150,{'title':'SALE AZER AZE ORDER'})
g.arrow((50,50),(450,150))

img.show()
