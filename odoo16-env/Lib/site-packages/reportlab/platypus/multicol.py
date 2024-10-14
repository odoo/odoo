__all__ = '''MultiCol'''.split()
from reportlab.lib.utils import strTypes
from .flowables import Flowable, _Container, _FindSplitterMixin, _listWrapOn

class MultiCol(_Container,_FindSplitterMixin,Flowable):
	def __init__(self,contents,widths, minHeightNeeded=36, spaceBefore=None, spaceAfter=None):
		if len(contents)!=len(widths):
			raise ValueError('%r len(contents)=%d not the same as len(widths)=%d' % (self,len(contents),len(widths)))
		self.contents = contents
		self.widths = widths
		self.minHeightNeeded = minHeightNeeded
		self._spaceBefore = spaceBefore
		self._spaceAfter = spaceAfter
		self._naW = None

	def nWidths(self,aW):
		if aW==self._naW: return self._nW
		nW = [].append
		widths = self.widths
		s = 0.0
		for i,w in enumerate(widths):
			if isinstance(w,strTypes):
				w=w.strip()
				pc = w.endswith('%')
				if pc: w=w[:-1]
				try:
					w = float(w)
				except:
					raise ValueError('%s: nWidths failed with value %r' % (self,widths[i]))
				if pc: w = w*0.01*aW
			elif not isinstance(w,(float,int)):
				raise ValueError('%s: nWidths failed with value %r' % (self,widths[i]))

			s += w
			nW(w)

		self._naW = aW
		s = aW / s
		self._nW = [w*s for w in nW.__self__]
		return self._nW

	def wrap(self,aW,aH):
		widths = self.nWidths(aW)
		w = h = 0.0
		canv = self.canv
		h = 0
		for faW,F in zip(widths,self.contents):
			if not F:
				fW = faW
				fH = 0
			else:
				fW,fH = _listWrapOn(F,faW,canv)
			h = max(h,fH)
			w += fW
		self.width = w
		self.height = h
		return w, h

	def split(self,aW,aH):
		if aH<self.minHeightNeeded:
			return []
		widths = self.nWidths(aW)
		S = [[],[]]
		canv = self.canv
		for faW,F in zip(widths,self.contents):
			if not F:
				fW = faW
				fH0 = 0
				S0 = []
				S1 = []
			else:
				fW,fH0,S0,S1 = self._findSplit(canv,faW,aH,content=F,paraFix=False)
				if S0 is F: return [] #we failed to find a split
			S[0].append(S0)
			S[1].append(S1)

		return	[
				MultiCol(S[0],
					self.widths,
					minHeightNeeded=self.minHeightNeeded,
					spaceBefore=self._spaceBefore,
					spaceAfter=self._spaceAfter),
				MultiCol(S[1],
					self.widths,
					minHeightNeeded=self.minHeightNeeded,
					spaceBefore=self._spaceBefore,
					spaceAfter=self._spaceAfter),
				]

	def getSpaceAfter(self):
		m = self._spaceAfter
		if m is None:
			m = 0
			for F in self.contents:
				m = max(m,_Container.getSpaceAfter(self,F))
		return m

	def getSpaceBefore(self):
		m = self._spaceBefore
		if m is None:
			m = 0
			for F in self.contents:
				m = max(m,_Container.getSpaceBefore(self,F))
		return m

	def drawOn(self, canv, x, y, _sW=0):
		widths = self._nW
		xOffs = 0
		for faW,F in zip(widths,self.contents):
			_Container.drawOn(self, canv, x+xOffs, y, content=F, aW=faW)
			xOffs += faW
