from reportlab.lib import colors
from reportlab.lib.validators import *
from reportlab.lib.attrmap import *
from reportlab.graphics.shapes import Drawing, _DrawingEditorMixin, Group, Polygon
from reportlab.graphics.widgetbase import Widget

class AdjustableArrow(Widget):
	"""This widget draws an arrow (style one).

		possible attributes:
		'x', 'y', 'size', 'fillColor'

		"""
	_attrMap = AttrMap(
		x = AttrMapValue(isNumber,desc='symbol x coordinate'),
		y = AttrMapValue(isNumber,desc='symbol y coordinate'),
		dx = AttrMapValue(isNumber,desc='symbol x coordinate adjustment'),
		dy = AttrMapValue(isNumber,desc='symbol x coordinate adjustment'),
		stemThickness = AttrMapValue(isNumber, 'width of the stem'),
		stemLength = AttrMapValue(isNumber, 'length of the stem'),
		headProjection = AttrMapValue(isNumber, 'how much the head projects from the stem'),
		headLength = AttrMapValue(isNumber, 'length of the head'),
		headSweep = AttrMapValue(isNumber, 'howmuch the head sweeps back (-ve) or forwards (+ve)'),
		scale = AttrMapValue(isNumber, 'scaling factor'),
		fillColor = AttrMapValue(isColorOrNone),
		strokeColor = AttrMapValue(isColorOrNone),
		strokeWidth = AttrMapValue(isNumber),
		boxAnchor = AttrMapValue(isBoxAnchor,desc='anchoring point of the label'),
		right =AttrMapValue(isBoolean,desc='If True (default) the arrow is horizontal pointing right\nFalse means it points up'),
		angle = AttrMapValue(isNumber, desc='angle of arrow default (0), right True 0 is horizontal to right else vertical up'),
		)
	def __init__(self,**kwds):
		self._setKeywords(**kwds)
		self._setKeywords(**dict(
				x = 0,
				y = 0,
				fillColor = colors.red,
				strokeWidth = 0,
				strokeColor = None,
				boxAnchor = 'c',
				angle = 0,
				stemThickness = 33,
				stemLength = 50,
				headProjection = 15,
				headLength = 50,
				headSweep = 0,
				scale = 1.,
				right=True,
				))

	def draw(self):
		# general widget bits
		g = Group()

		x = self.x
		y = self.y
		scale = self.scale
		stemThickness = self.stemThickness*scale
		stemLength = self.stemLength*scale
		headProjection = self.headProjection*scale
		headLength = self.headLength*scale
		headSweep = self.headSweep*scale
		w = stemLength+headLength
		h = 2*headProjection+stemThickness
		# shift to the boxAnchor
		boxAnchor = self.boxAnchor
		if self.right:
			if boxAnchor in ('sw','w','nw'):
				dy = -h
			elif boxAnchor in ('s','c','n'):
				dy = -h*0.5
			else:
				dy = 0
			if boxAnchor in ('w','c','e'):
				dx = -w*0.5
			elif boxAnchor in ('nw','n','ne'):
				dx = -w
			else:
				dx = 0
			points = [
				dx, dy+headProjection+stemThickness,
				dx+stemLength, dy+headProjection+stemThickness,
				dx+stemLength+headSweep, dy+2*headProjection+stemThickness,
				dx+stemLength+headLength, dy+0.5*stemThickness+headProjection,
				dx+stemLength+headSweep, dy,
				dx+stemLength, dy+headProjection,
				dx, dy+headProjection,
				]
		else:
			w,h = h,w
			if boxAnchor in ('nw','n','ne'):
				dy = -h
			elif boxAnchor in ('w','c','e'):
				dy = -h*0.5
			else:
				dy = 0
			if boxAnchor in ('ne','e','se'):
				dx = -w
			elif boxAnchor in ('n','c','s'):
				dx = -w*0.5
			else:
				dx = 0
			points = [
				dx+headProjection, dy,	#sw
				dx+headProjection+stemThickness, dy,	#se
				dx+headProjection+stemThickness, dy+stemLength,
				dx+w, dy+stemLength+headSweep,
				dx+headProjection+0.5*stemThickness, dy+h,
				dx, dy+stemLength+headSweep,
				dx+headProjection, dy+stemLength,
				]

		g.add(Polygon(
				points = points,
				fillColor = self.fillColor,
				strokeColor = self.strokeColor,
				strokeWidth = self.strokeWidth,
				))
		g.translate(x,y)
		g.rotate(self.angle)
		return g

class AdjustableArrowDrawing(_DrawingEditorMixin,Drawing):
	def __init__(self,width=100,height=63,*args,**kw):
		Drawing.__init__(self,width,height,*args,**kw)
		self._add(self,AdjustableArrow(),name='adjustableArrow',validate=None,desc=None)
