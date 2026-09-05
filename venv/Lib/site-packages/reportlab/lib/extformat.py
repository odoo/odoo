#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
__version__='3.3.0'
__doc__='''Apparently not used anywhere, purpose unknown!'''
try:
	from tokenize import tokenprog
except ImportError:
	from tokenize import Token
	import re
	tokenprog = re.compile(Token)
	del Token, re
import sys

def _matchorfail(text, pos):
	match = tokenprog.match(text, pos)
	if match is None: raise ValueError(text, pos)
	return match, match.end()

'''
	Extended dictionary formatting
	We allow expressions in the parentheses instead of
	just a simple variable.
'''
def dictformat(_format, L={}, G={}):
	format = _format

	S = {}
	chunks = []
	pos = 0
	n = 0

	while 1:
		pc = format.find("%", pos)
		if pc < 0: break
		nextchar = format[pc+1]

		if nextchar == "(":
			chunks.append(format[pos:pc])
			pos, level = pc+2, 1
			while level:
				match, pos = _matchorfail(format, pos)
				tstart, tend = match.regs[3]
				token = format[tstart:tend]
				if token == "(": level = level+1
				elif token == ")": level = level-1
			vname = '__superformat_%d' % n
			n += 1
			S[vname] = eval(format[pc+2:pos-1],G,L)
			chunks.append('%%(%s)' % vname)
		else:
			nc = pc+1+(nextchar=="%")
			chunks.append(format[pos:nc])
			pos = nc

	if pos < len(format): chunks.append(format[pos:])
	return (''.join(chunks)) % S

def magicformat(format):
	"""Evaluate and substitute the appropriate parts of the string."""
	frame = sys._getframe(1)
	return dictformat(format,frame.f_locals, frame.f_globals)

if __name__=='__main__':
	from reportlab.lib.formatters import DecimalFormatter
	_DF={}
	def df(n,dp=2,ds='.',ts=','):
		try:
			_df = _DF[dp,ds]
		except KeyError:
			_df = _DF[dp,ds] = DecimalFormatter(places=dp,decimalSep=ds,thousandSep=ts)
		return _df(n)

	from reportlab.lib.extformat import magicformat

	Z={'abc': ('ab','c')}
	x = 300000.23
	percent=79.2
	class dingo:
		a=3
	print((magicformat('''
$%%(df(x,dp=3))s --> $%(df(x,dp=3))s
$%%(df(x,dp=2,ds=',',ts='.'))s --> $%(df(x,dp=2,ds=',',ts='.'))s
%%(percent).2f%%%% --> %(percent).2f%%
%%(dingo.a)s --> %(dingo.a)s
%%(Z['abc'][0])s --> %(Z['abc'][0])s
''')))
	def func0(aa=1):
		def func1(bb=2):
			print((magicformat('bb=%(bb)s Z=%(Z)r')))
		func1('BB')
	func0('AA')
