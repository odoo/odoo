# coding=utf-8
# tk/latex/__init__.py
# Rushy Panchal
# v1.0

'''Provides Latex-type text editing, to be used in Tkinter Text widgets'''

try: from Tkinter import *
except ImportError: from tkinter import *
from latexConstants import *
from Symbols import *
	
__modules__ = {'base': [
		'__init__.py',
		'Symbols.py',
		'latexConstants.py',
		'LatexText.py',
		'ttkLatexText.py'
		]
	}

__author__ = "Rushy Panchal"

__version__ = 1.0

### Main Patterns
manifest
patterns = {
	r'_': Replace("\_ ?\{([^}]+)\}", r'<sub>\1</sub>'),
	r'^': Replace("\^ ?\{([^}]+)\}", r'<sup>\1</sup>'),
	r'%': Replace("\{([^}]+)\} ?% ?\{([^}]+)\}", r'<num>\1</num><div>\2</div>'),
	r'\pm': MathematicalSymbol(PLUS_OR_MINUS, r'\pm', r'\PM'),
	r'\le': MathematicalSymbol(LESS_OR_EQUAL, r'\le', r'\LE', '<='),
	r'\ge': MathematicalSymbol(GREATER_OR_EQUAL, r'\ge', r'\GE', '>='),
	r'\eq': MathematicalSymbol(EQUAL, r'\eq', r'\eq', '='),
	r'neq': MathematicalSymbol(NOT_EQUAL, r'\neq', r'\NEQ', '!='),
	r'\approx': MathematicalSymbol(APPROXIMATE, r'\approx', r'\APPROX', '~~'),
	r'\Alpha': GreekLetter(ALPHA, r'\Alpha', r'\ALPHA'),
	r'\alpha': GreekLetter(LOWER_ALPHA, r'\\alpha'),
	r'\Beta': GreekLetter(BETA, r'\Beta', r'\BETA'),
	r'\beta': GreekLetter(LOWER_BETA, r'\beta'),
	r'\Gamma': GreekLetter(GAMMA, r'\Gamma', r'\GAMMA'),
	r'\gamma': GreekLetter(LOWER_GAMMA, r'\gamma'),
	r'\Delta': GreekLetter(DELTA, r'\Delta', r'\DELTA'),
	r'\delta': GreekLetter(LOWER_DELTA, r'\delta'),
	r'\Epsilon': GreekLetter(EPSILON, r'\Epsilon', r'\EPSILON'),
	r'\epsilon': GreekLetter(LOWER_EPSILON, r'\epsilon'),
	r'\Zeta': GreekLetter(ZETA, r'\Zeta', r'\ZETA'),
	r'\zeta': GreekLetter(LOWER_ZETA, r'\zeta'),
	r'\Eta': GreekLetter(ETA, r'\Eta', r'\ETA'),
	r'\eta': GreekLetter(LOWER_ETA, r'\eta'),
	r'\Theta': GreekLetter(THETA, r'\Theta', r'\THETA'),
	r'\theta': GreekLetter(LOWER_THETA, r'\theta'),
	r'\Iota': GreekLetter(IOTA, r'\Iota', r'\IOTA'),
	r'\iota': GreekLetter(LOWER_IOTA, r'\iota'),
	r'\Kappa': GreekLetter(KAPPA, r'\Kappa', r'\KAPPA'),
	r'\kappa': GreekLetter(LOWER_KAPPA, r'\kappa'),
	r'\Lambda': GreekLetter(LAMBDA, r'\Lambda', r'\LAMBDA'),
	r'\lambda': GreekLetter(LOWER_LAMBDA, r'\lambda'),
	r'\Mu': GreekLetter(MU, r'\Mu', r'\MU'),
	r'\mu': GreekLetter(LOWER_MU, r'\mu'),
	r'\Nu': GreekLetter(NU, r'\Nu', r'\NU'),
	r'\nu': GreekLetter(LOWER_NU, r'\nu'),
	r'\Xi': GreekLetter(XI, r'\Xi', r'\XI'),
	r'\xi': GreekLetter(LOWER_XI, r'\xi'),
	r'\Omicron': GreekLetter(OMICRON, r'\Omicron', r'\OMICRON'),
	r'\omicron': GreekLetter(LOWER_OMICRON, r'\omicron'),
	r'\Pi': GreekLetter(PI, r'\Pi', r'\PI'),
	r'\pi': GreekLetter(LOWER_PI, r'\pi'),
	r'\Rho': GreekLetter(RHO, r'\Rho', r'\RHO'),
	r'\rho': GreekLetter(LOWER_RHO, r'\rho'),
	r'\Sigma': GreekLetter(SIGMA, r'\Sigma', r'\SIGMA'),
	r'\sigma': GreekLetter(LOWER_SIGMA, r'\sigma'),
	r'\Tau': GreekLetter(TAU, r'\Tau', r'\TAU'),
	r'\tau': GreekLetter(LOWER_TAU, r'\tau'),
	r'\Upsilon': GreekLetter(UPSILON, r'\Upsilon', r'\UPSILON'),
	r'\upsilon': GreekLetter(LOWER_UPSILON, r'\upsilon'),
	r'\Phi': GreekLetter(PHI, r'\Phi', r'\PHI'),
	r'\phi': GreekLetter(LOWER_PHI, r'\phi'),
	r'\Chi': GreekLetter(CHI, r'\Chi', r'\CHI'),
	r'\chi': GreekLetter(LOWER_CHI, r'\chi'),
	r'\Psi': GreekLetter(PSI, r'\Psi', '\PSI'),
	r'\psi': GreekLetter(LOWER_PSI, r'\psi'),
	r'\Omega': GreekLetter(OMEGA, r'\Omega', r'\OMEGA'),
	r'\omega': GreekLetter(LOWER_OMEGA, r'\omega')
	}
	
### Main functions
	
def latexHelp(cmd = None):
	'''Shows help on the given command, if any'''
	cmd_help = {
		'_': 'Subscript', 
		'^': 'Superscript',
		'%': 'Division/Fraction',
		'\pm': 'Plus or Minus: ' + PLUS_OR_MINUS,
		'\le': 'Less Than or Equal To: ' + LESS_OR_EQUAL,
		'\ge': 'Greater Than or Equal To: ' + GREATER_OR_EQUAL,
		'\eq': 'Equal To: ' + EQUAL,
		'\neq': 'Not Equal To: ' + NOT_EQUAL,
		'\approx': 'Approximately Equivalent To: ' + APPROXIMATE,
		}
	if cmd:
		try: print(cmd_help[cmd])
		except KeyError: print("Not a valid Latex command.")
	else:
		for cmd, help_text in cmd_help.items():
			print(cmd, help_text)

def getPatterns():
	'''Returns the Replace patterns'''
	return patterns

def isCompiled(text):
	'''Returns whether or not the text is Latex-compiled'''
	return isinstance(text, CompiledLatex)

### Main classes
	
class Latex(unicode):
	'''Basic latex editing class'''
	def __init__(self, text):
		self.text = text
		self.patterns = getPatterns()
		self.compiled = False
		str.__init__(self, text)

	def add(self, text):
		'''Adds text to the existing text'''
		self.text += text
		self.compiled = False

	def addLine(self, text):
		'''Adds text, on a new line, to the existing text'''
		self.add('\n' + text)
		self.compiled = False

	def isCompiled(self):
		'''Returns whether or not the current text is completely compiled'''
		return self.compiled
		
	def compile(self):
		'''Compiles the latex into a tk.LatexText readable format'''
		if not self.compiled:
			self.compiled_text = CompiledLatex.compile(self.text)
			self.compiled = True
		return self.compiled_text
		
class CompiledLatex(unicode):
	'''Internal class for a "compiled", tk.LatexText readable text'''
	def __init__(self, text):
		self.patterns = getPatterns()
		if not self.isCompiled(text): raise ValueError("Text was not compiled correctly.")
		self.text = text
		
	def isCompiled(self, text):
		'''Determines if the text is compiled'''
		for pattern, replacer in self.patterns.items():
			if pattern in text: return False
		return True
		
	@staticmethod
	def compile(text):
		'''Compiles the given text'''
		compiled_text = text
		patterns = getPatterns()
		for pattern, replacer in patterns.items():
			compiled_text = replacer(compiled_text)
		return CompiledLatex(compiled_text)

	def __repr__(self):
		'''String representation'''
		return self.text