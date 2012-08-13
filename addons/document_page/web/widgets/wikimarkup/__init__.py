# coding: latin1
"""
MediaWiki-style markup

Copyright (C) 2008 David Cramer <dcramer@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import re, random, locale
from base64 import b64encode, b64decode

# a few patterns we use later

MW_COLON_STATE_TEXT = 0
MW_COLON_STATE_TAG = 1
MW_COLON_STATE_TAGSTART = 2
MW_COLON_STATE_CLOSETAG = 3
MW_COLON_STATE_TAGSLASH = 4
MW_COLON_STATE_COMMENT = 5
MW_COLON_STATE_COMMENTDASH = 6
MW_COLON_STATE_COMMENTDASHDASH = 7

_attributePat = re.compile(ur'''(?:^|\s)([A-Za-z0-9]+)(?:\s*=\s*(?:"([^<"]*)"|'([^<']*)'|([a-zA-Z0-9!#$%&()*,\-./:;<>?@[\]^_`{|}~]+)|#([0-9a-fA-F]+)))''', re.UNICODE)
_space = re.compile(ur'\s+', re.UNICODE)
_closePrePat = re.compile(u"</pre", re.UNICODE | re.IGNORECASE)
_openPrePat = re.compile(u"<pre", re.UNICODE | re.IGNORECASE)
_openMatchPat = re.compile(u"(<table|<blockquote|<h1|<h2|<h3|<h4|<h5|<h6|<pre|<tr|<p|<ul|<ol|<li|</center|</tr|</td|</th)", re.UNICODE | re.IGNORECASE)
_tagPattern = re.compile(ur'^(/?)(\w+)([^>]*?)(/?>)([^<]*)$', re.UNICODE)

_htmlpairs = ( # Tags that must be closed
	u'b', u'del', u'i', u'ins', u'u', u'font', u'big', u'small', u'sub', u'sup', u'h1',
	u'h2', u'h3', u'h4', u'h5', u'h6', u'cite', u'code', u'em', u's',
	u'strike', u'strong', u'tt', u'var', u'div', u'center',
	u'blockquote', u'ol', u'ul', u'dl', u'table', u'caption', u'pre',
	u'ruby', u'rt' , u'rb' , u'rp', u'p', u'span', u'u',
)
_htmlsingle = (
	u'br', u'hr', u'li', u'dt', u'dd', u'img',
)
_htmlsingleonly = ( # Elements that cannot have close tags
	u'br', u'hr', u'img',
)
_htmlnest = ( # Tags that can be nested--??
	u'table', u'tr', u'td', u'th', u'div', u'blockquote', u'ol', u'ul',
	u'dl', u'font', u'big', u'small', u'sub', u'sup', u'span', u'img',
)
_tabletags = ( # Can only appear inside table
	u'td', u'th', u'tr',
)
_htmllist = ( # Tags used by list
	u'ul', u'ol',
)
_listtags = ( # Tags that can appear in a list
	u'li',
)
_htmlsingleallowed = _htmlsingle + _tabletags
_htmlelements = _htmlsingle + _htmlpairs + _htmlnest

_htmlEntities = {
	u'Aacute': 193,	u'aacute': 225, u'Acirc': 194, u'acirc': 226, u'acute': 180,
	u'AElig': 198, u'aelig': 230, u'Agrave': 192, u'agrave': 224, u'alefsym': 8501,
	u'Alpha': 913, u'alpha': 945, u'amp': 38, u'and': 8743, u'ang': 8736, u'Aring': 197,
	u'aring':	  229,
	u'asymp':	  8776,
	u'Atilde':	 195,
	u'atilde':	 227,
	u'Auml':	   196,
	u'auml':	   228,
	u'bdquo':	  8222,
	u'Beta':	   914,
	u'beta':	   946,
	u'brvbar':	 166,
	u'bull':	   8226,
	u'cap':		8745,
	u'Ccedil':	 199,
	u'ccedil':	 231,
	u'cedil':	  184,
	u'cent':	   162,
	u'Chi':		935,
	u'chi':		967,
	u'circ':	   710,
	u'clubs':	  9827,
	u'cong':	   8773,
	u'copy':	   169,
	u'crarr':	  8629,
	u'cup':		8746,
	u'curren':	 164,
	u'dagger':	 8224,
	u'Dagger':	 8225,
	u'darr':	   8595,
	u'dArr':	   8659,
	u'deg':		176,
	u'Delta':	  916,
	u'delta':	  948,
	u'diams':	  9830,
	u'divide':	 247,
	u'Eacute':	 201,
	u'eacute':	 233,
	u'Ecirc':	  202,
	u'ecirc':	  234,
	u'Egrave':	 200,
	u'egrave':	 232,
	u'empty':	  8709,
	u'emsp':	   8195,
	u'ensp':	   8194,
	u'Epsilon':	917,
	u'epsilon':	949,
	u'equiv':	  8801,
	u'Eta':		919,
	u'eta':		951,
	u'ETH':		208,
	u'eth':		240,
	u'Euml':	   203,
	u'euml':	   235,
	u'euro':	   8364,
	u'exist':	  8707,
	u'fnof':	   402,
	u'forall':	 8704,
	u'frac12':	 189,
	u'frac14':	 188,
	u'frac34':	 190,
	u'frasl':	  8260,
	u'Gamma':	  915,
	u'gamma':	  947,
	u'ge':		 8805,
	u'gt':		 62,
	u'harr':	   8596,
	u'hArr':	   8660,
	u'hearts':	 9829,
	u'hellip':	 8230,
	u'Iacute':	 205,
	u'iacute':	 237,
	u'Icirc':	  206,
	u'icirc':	  238,
	u'iexcl':	  161,
	u'Igrave':	 204,
	u'igrave':	 236,
	u'image':	  8465,
	u'infin':	  8734,
	u'int':		8747,
	u'Iota':	   921,
	u'iota':	   953,
	u'iquest':	 191,
	u'isin':	   8712,
	u'Iuml':	   207,
	u'iuml':	   239,
	u'Kappa':	  922,
	u'kappa':	  954,
	u'Lambda':	 923,
	u'lambda':	 955,
	u'lang':	   9001,
	u'laquo':	  171,
	u'larr':	   8592,
	u'lArr':	   8656,
	u'lceil':	  8968,
	u'ldquo':	  8220,
	u'le':		 8804,
	u'lfloor':	 8970,
	u'lowast':	 8727,
	u'loz':		9674,
	u'lrm':		8206,
	u'lsaquo':	 8249,
	u'lsquo':	  8216,
	u'lt':		 60,
	u'macr':	   175,
	u'mdash':	  8212,
	u'micro':	  181,
	u'middot':	 183,
	u'minus':	  8722,
	u'Mu':		 924,
	u'mu':		 956,
	u'nabla':	  8711,
	u'nbsp':	   160,
	u'ndash':	  8211,
	u'ne':		 8800,
	u'ni':		 8715,
	u'not':		172,
	u'notin':	  8713,
	u'nsub':	   8836,
	u'Ntilde':	 209,
	u'ntilde':	 241,
	u'Nu':		 925,
	u'nu':		 957,
	u'Oacute':	 211,
	u'oacute':	 243,
	u'Ocirc':	  212,
	u'ocirc':	  244,
	u'OElig':	  338,
	u'oelig':	  339,
	u'Ograve':	 210,
	u'ograve':	 242,
	u'oline':	  8254,
	u'Omega':	  937,
	u'omega':	  969,
	u'Omicron':	927,
	u'omicron':	959,
	u'oplus':	  8853,
	u'or':		 8744,
	u'ordf':	   170,
	u'ordm':	   186,
	u'Oslash':	 216,
	u'oslash':	 248,
	u'Otilde':	 213,
	u'otilde':	 245,
	u'otimes':	 8855,
	u'Ouml':	   214,
	u'ouml':	   246,
	u'para':	   182,
	u'part':	   8706,
	u'permil':	 8240,
	u'perp':	   8869,
	u'Phi':		934,
	u'phi':		966,
	u'Pi':		 928,
	u'pi':		 960,
	u'piv':		982,
	u'plusmn':	 177,
	u'pound':	  163,
	u'prime':	  8242,
	u'Prime':	  8243,
	u'prod':	   8719,
	u'prop':	   8733,
	u'Psi':		936,
	u'psi':		968,
	u'quot':	   34,
	u'radic':	  8730,
	u'rang':	   9002,
	u'raquo':	  187,
	u'rarr':	   8594,
	u'rArr':	   8658,
	u'rceil':	  8969,
	u'rdquo':	  8221,
	u'real':	   8476,
	u'reg':		174,
	u'rfloor':	 8971,
	u'Rho':		929,
	u'rho':		961,
	u'rlm':		8207,
	u'rsaquo':	 8250,
	u'rsquo':	  8217,
	u'sbquo':	  8218,
	u'Scaron':	 352,
	u'scaron':	 353,
	u'sdot':	   8901,
	u'sect':	   167,
	u'shy':		173,
	u'Sigma':	  931,
	u'sigma':	  963,
	u'sigmaf':	 962,
	u'sim':		8764,
	u'spades':	 9824,
	u'sub':		8834,
	u'sube':	   8838,
	u'sum':		8721,
	u'sup':		8835,
	u'sup1':	   185,
	u'sup2':	   178,
	u'sup3':	   179,
	u'supe':	   8839,
	u'szlig':	  223,
	u'Tau':		932,
	u'tau':		964,
	u'there4':	 8756,
	u'Theta':	  920,
	u'theta':	  952,
	u'thetasym':   977,
	u'thinsp':	 8201,
	u'THORN':	  222,
	u'thorn':	  254,
	u'tilde':	  732,
	u'times':	  215,
	u'trade':	  8482,
	u'Uacute':	 218,
	u'uacute':	 250,
	u'uarr':	   8593,
	u'uArr':	   8657,
	u'Ucirc':	  219,
	u'ucirc':	  251,
	u'Ugrave':	 217,
	u'ugrave':	 249,
	u'uml':		168,
	u'upsih':	  978,
	u'Upsilon':	933,
	u'upsilon':	965,
	u'Uuml':	   220,
	u'uuml':	   252,
	u'weierp':	 8472,
	u'Xi':		 926,
	u'xi':		 958,
	u'Yacute':	 221,
	u'yacute':	 253,
	u'yen':		165,
	u'Yuml':	   376,
	u'yuml':	   255,
	u'Zeta':	   918,
	u'zeta':	   950,
	u'zwj':		8205,
	u'zwnj':	   8204
}

_charRefsPat = re.compile(ur'''(&([A-Za-z0-9]+);|&#([0-9]+);|&#[xX]([0-9A-Za-z]+);|(&))''', re.UNICODE)
_cssCommentPat = re.compile(ur'''\*.*?\*''', re.UNICODE)
_toUTFPat = re.compile(ur'''\\([0-9A-Fa-f]{1,6})[\s]?''', re.UNICODE)
_hackPat = re.compile(ur'''(expression|tps*://|url\s*\().*''', re.UNICODE | re.IGNORECASE)
_hrPat = re.compile(u'''^-----*''', re.UNICODE | re.MULTILINE)
_h1Pat = re.compile(u'^=(.+)=\s*$', re.UNICODE | re.MULTILINE)
_h2Pat = re.compile(u'^==(.+)==\s*$', re.UNICODE | re.MULTILINE)
_h3Pat = re.compile(u'^===(.+)===\s*$', re.UNICODE | re.MULTILINE)
_h4Pat = re.compile(u'^====(.+)====\s*$', re.UNICODE | re.MULTILINE)
_h5Pat = re.compile(u'^=====(.+)=====\s*$', re.UNICODE | re.MULTILINE)
_h6Pat = re.compile(u'^======(.+)======\s*$', re.UNICODE | re.MULTILINE)
_quotePat = re.compile(u"""(''+)""", re.UNICODE)
_removePat = re.compile(ur'\b(' + ur'|'.join((u"a", u"an", u"as", u"at", u"before", u"but", u"by", u"for", u"from",
							u"is", u"in", u"into", u"like", u"of", u"off", u"on", u"onto", u"per",
							u"since", u"than", u"the", u"this", u"that", u"to", u"up", u"via",
							u"with")) + ur')\b', re.UNICODE | re.IGNORECASE)
_nonWordSpaceDashPat = re.compile(ur'[^\w\s\-\./]', re.UNICODE)
_multiSpacePat = re.compile(ur'[\s\-_\./]+', re.UNICODE)
_spacePat = re.compile(ur' ', re.UNICODE)
_linkPat = re.compile(ur'^(?:([A-Za-z0-9]+):)?([^\|]+)(?:\|([^\n]+?))?\]\](.*)$', re.UNICODE | re.DOTALL)
_bracketedLinkPat = re.compile(ur'(?:\[((?:mailto:|irc://|https?://|ftp://|/)[^<>\]\[' + u"\x00-\x20\x7f" + ur']*)\s*(.*?)\])', re.UNICODE)
_protocolPat = re.compile(ur'(\b(?:mailto:|irc://|https?://|ftp://))', re.UNICODE)
_specialUrlPat = re.compile(ur'^([^<>\]\[' + u"\x00-\x20\x7f" + ur']+)(.*)$', re.UNICODE)
_protocolsPat = re.compile(ur'^(mailto:|irc://|https?://|ftp://)$', re.UNICODE)
_controlCharsPat = re.compile(ur'[\]\[<>"' + u"\\x00-\\x20\\x7F" + ur']]', re.UNICODE)
_hostnamePat = re.compile(ur'^([^:]+:)(//[^/]+)?(.*)$', re.UNICODE)
_stripPat = re.compile(u'\\s|\u00ad|\u1806|\u200b|\u2060|\ufeff|\u03f4|\u034f|\u180b|\u180c|\u180d|\u200c|\u200d|[\ufe00-\ufe0f]', re.UNICODE)
_zomgPat = re.compile(ur'^(:*)\{\|(.*)$', re.UNICODE)
_headerPat = re.compile(ur"<[Hh]([1-6])(.*?)>(.*?)</[Hh][1-6] *>", re.UNICODE)
_templateSectionPat = re.compile(ur"<!--MWTEMPLATESECTION=([^&]+)&([^_]+)-->", re.UNICODE)
_tagPat = re.compile(ur"<.*?>", re.UNICODE)
_startRegexHash = {}
_endRegexHash = {}
_endCommentPat = re.compile(ur'(-->)', re.UNICODE)
_extractTagsAndParams_n = 1
_guillemetLeftPat = re.compile(ur'(.) (\?|:|;|!|\302\273)', re.UNICODE)
_guillemetRightPat = re.compile(ur'(\302\253) ', re.UNICODE)

def setupAttributeWhitelist():
	common = ( u'id', u'class', u'lang', u'dir', u'title', u'style' )
	block = common + (u'align',)
	tablealign = ( u'align', u'char', u'charoff', u'valign' )
	tablecell = ( u'abbr',
					u'axis',
					u'headers',
					u'scope',
					u'rowspan',
					u'colspan',
					u'nowrap', # deprecated
					u'width',  # deprecated
					u'height', # deprecated
					u'bgcolor' # deprecated
					)
	return {
		u'div':			block,
		u'center':		common, # deprecated
		u'span':		block, # ??
		u'h1':			block,
		u'h2':			block,
		u'h3':			block,
		u'h4':			block,
		u'h5':			block,
		u'h6':			block,
		u'em':			common,
		u'strong':		common,
		u'cite':		common,
		u'code':		common,
		u'var':			common,
		u'img':			common + (u'src', u'alt', u'width', u'height',),
		u'blockquote':	common + (u'cite',),
		u'sub':			common,
		u'sup':			common,
		u'p':			block,
		u'br':			(u'id', u'class', u'title', u'style', u'clear',),
		u'pre':			common + (u'width',),
		u'ins':			common + (u'cite', u'datetime'),
		u'del':			common + (u'cite', u'datetime'),
		u'ul':			common + (u'type',),
		u'ol':			common + (u'type', u'start'),
		u'li':			common + (u'type', u'value'),
		u'dl':			common,
		u'dd':			common,
		u'dt':			common,
		u'table':		common + ( u'summary', u'width', u'border', u'frame',
									u'rules', u'cellspacing', u'cellpadding',
									u'align', u'bgcolor',
							),
		u'caption':		common + (u'align',),
		u'thead':		common + tablealign,
		u'tfoot':		common + tablealign,
		u'tbody':		common + tablealign,
		u'colgroup':	common + ( u'span', u'width' ) + tablealign,
		u'col':			common + ( u'span', u'width' ) + tablealign,
		u'tr':			common + ( u'bgcolor', ) + tablealign,
		u'td':			common + tablecell + tablealign,
		u'th':			common + tablecell + tablealign,
		u'tt':			common,
		u'b':			common,
		u'i':			common,
		u'big':			common,
		u'small':		common,
		u'strike':		common,
		u's':			common,
		u'u':			common,
		u'font':		common + ( u'size', u'color', u'face' ),
		u'hr':			common + ( u'noshade', u'size', u'width' ),
		u'ruby':		common,
		u'rb':			common,
		u'rt':			common, #array_merge( $common, array( 'rbspan' ) ),
		u'rp':			common,
	}
_whitelist = setupAttributeWhitelist()
_page_cache = {}
env = {}

def registerTagHook(tag, function):
	mTagHooks[tag] = function

class BaseParser(object):
	def __init__(self):
		self.uniq_prefix = u"\x07UNIQ" + unicode(random.randint(1, 1000000000))
		self.strip_state = {}
		self.arg_stack = []
		self.env = env
		self.keep_env = (env != {})

	def __del__(self):
		if not self.keep_env:
			global env
			env = {}

	''' Used to store objects in the environment
		used to prevent recursive imports '''
	def store_object(self, namespace, key, value=True):
		# Store the item to not reprocess it
		if namespace not in self.env:
			self.env[namespace] = {}
		self.env[namespace][key] = value

	def has_object(self, namespace, key):
		if namespace not in self.env:
			self.env[namespace] = {}
		if hasattr(self, 'count'):
			data = self.env[namespace]
			test = key in data
			self.count = True
		return key in self.env[namespace]

	def retrieve_object(self, namespace, key, default=None):
		if not self.env.get(namespace):
			self.env[namespace] = {}
		return self.env[namespace].get(key, default)

	def parse(self, text):
		utf8 = isinstance(text, str)
		text = to_unicode(text)
		if text[-1:] != u'\n':
			text = text + u'\n'
			taggedNewline = True
		else:
			taggedNewline = False

		text = self.strip(text)
		text = self.removeHtmlTags(text)
		text = self.parseHorizontalRule(text)
		text = self.parseAllQuotes(text)
		text = self.replaceExternalLinks(text)
		text = self.unstrip(text)
		text = self.fixtags(text)
		text = self.doBlockLevels(text, True)
		text = self.unstripNoWiki(text)
		text = text.split(u'\n')
		text = u'\n'.join(text)
		if taggedNewline and text[-1:] == u'\n':
			text = text[:-1]
		if utf8:
			return text.encode("utf-8")
		return text

	def strip(self, text, stripcomments=False, dontstrip=[]):
		render = True

		commentState = {}

		elements = ['nowiki',]  + mTagHooks.keys()
		if True: #wgRawHtml
			elements.append('html')

		# Removing $dontstrip tags from $elements list (currently only 'gallery', fixing bug 2700)
		for k in dontstrip:
			if k in elements:
				del elements[k]

		matches = {}
		text = self.extractTagsAndParams(elements, text, matches)

		for marker in matches:
			element, content, params, tag = matches[marker]
			if render:
				tagName = element.lower()
				if tagName == u'!--':
					# comment
					output = tag
					if tag[-3:] != u'-->':
						output += "-->"
				elif tagName == u'html':
					output = content
				elif tagName == u'nowiki':
					output = content.replace(u'&', u'&amp;').replace(u'<', u'&lt;').replace(u'>', u'&gt;')
				else:
					if tagName in mTagHooks:
						output = mTagHooks[tagName](self, content, params)
					else:
						output = content.replace(u'&', u'&amp;').replace(u'<', u'&lt;').replace(u'>', u'&gt;')
			else:
				# Just stripping tags; keep the source
				output = tag

			# Unstrip the output, because unstrip() is no longer recursive so
			# it won't do it itself
			output = self.unstrip(output)

			if not stripcomments and element == u'!--':
				commentState[marker] = output
			elif element == u'html' or element == u'nowiki':
				if 'nowiki' not in self.strip_state:
					self.strip_state['nowiki'] = {}
				self.strip_state['nowiki'][marker] = output
			else:
				if 'general' not in self.strip_state:
					self.strip_state['general'] = {}
				self.strip_state['general'][marker] = output

		# Unstrip comments unless explicitly told otherwise.
		# (The comments are always stripped prior to this point, so as to
		# not invoke any extension tags / parser hooks contained within
		# a comment.)
		if not stripcomments:
			# Put them all back and forget them
			for k in commentState:
				v = commentState[k]
				text = text.replace(k, v)

		return text

	def removeHtmlTags(self, text):
		"""convert bad tags into HTML identities"""
		sb = []
		text = self.removeHtmlComments(text)
		bits = text.split(u'<')
		sb.append(bits.pop(0))
		tagstack = []
		tablestack = tagstack
		for x in bits:
			m = _tagPattern.match(x)
			if not m:
				continue
			slash, t, params, brace, rest = m.groups()
			t = t.lower()
			badtag = False
			if t in _htmlelements:
				# Check our stack
				if slash:
					# Closing a tag...
					if t in _htmlsingleonly or len(tagstack) == 0:
						badtag = True
					else:
						ot = tagstack.pop()
						if ot != t:
							if ot in _htmlsingleallowed:
								# Pop all elements with an optional close tag
								# and see if we find a match below them
								optstack = []
								optstack.append(ot)
								while True:
									if len(tagstack) == 0:
										break
									ot = tagstack.pop()
									if ot == t or ot not in _htmlsingleallowed:
										break
									optstack.append(ot)
								if t != ot:
									# No match. Push the optinal elements back again
									badtag = True
									tagstack += reversed(optstack)
							else:
								tagstack.append(ot)
								# <li> can be nested in <ul> or <ol>, skip those cases:
								if ot not in _htmllist and t in _listtags:
									badtag = True
						elif t == u'table':
							if len(tablestack) == 0:
								bagtag = True
							else:
								tagstack = tablestack.pop()
					newparams = u''
				else:
					# Keep track for later
					if t in _tabletags and u'table' not in tagstack:
						badtag = True
					elif t in tagstack and t not in _htmlnest:
						badtag = True
					# Is it a self-closed htmlpair? (bug 5487)
					elif brace == u'/>' and t in _htmlpairs:
						badTag = True
					elif t in _htmlsingleonly:
						# Hack to force empty tag for uncloseable elements
						brace = u'/>'
					elif t in _htmlsingle:
						# Hack to not close $htmlsingle tags
						brace = None
					else:
						if t == u'table':
							tablestack.append(tagstack)
							tagstack = []
						tagstack.append(t)
					newparams = self.fixTagAttributes(params, t)
				if not badtag:
					rest = rest.replace(u'>', u'&gt;')
					if brace == u'/>':
						close = u' /'
					else:
						close = u''
					sb.append(u'<')
					sb.append(slash)
					sb.append(t)
					sb.append(newparams)
					sb.append(close)
					sb.append(u'>')
					sb.append(rest)
					continue
			sb.append(u'&lt;')
			sb.append(x.replace(u'>', u'&gt;'))

		# Close off any remaining tags
		while tagstack:
			t = tagstack.pop()
			sb.append(u'</')
			sb.append(t)
			sb.append(u'>\n')
			if t == u'table':
				if not tablestack:
					break
				tagstack = tablestack.pop()

		return u''.join(sb)

	def removeHtmlComments(self, text):
		"""remove <!-- text --> comments from given text"""
		sb = []
		start = text.find(u'<!--')
		last = 0
		while start != -1:
			end = text.find(u'-->', start)
			if end == -1:
				break
			end += 3

			spaceStart = max(0, start-1)
			spaceEnd = end
			while text[spaceStart] == u' ' and spaceStart > 0:
				spaceStart -= 1
			while text[spaceEnd] == u' ':
				spaceEnd += 1

			if text[spaceStart] == u'\n' and text[spaceEnd] == u'\n':
				sb.append(text[last:spaceStart])
				sb.append(u'\n')
				last = spaceEnd+1
			else:
				sb.append(text[last:spaceStart+1])
				last = spaceEnd

			start = text.find(u'<!--', end)
		sb.append(text[last:])
		return u''.join(sb)

	def decodeTagAttributes(self, text):
		"""docstring for decodeTagAttributes"""
		attribs = {}
		if text.strip() == u'':
			return attribs
		scanner = _attributePat.scanner(text)
		match = scanner.search()
		while match:
			key, val1, val2, val3, val4 = match.groups()
			value = val1 or val2 or val3 or val4
			if value:
				value = _space.sub(u' ', value).strip()
			else:
				value = ''
			attribs[key] = self.decodeCharReferences(value)

			match = scanner.search()
		return attribs

	def validateTagAttributes(self, attribs, element):
		"""docstring for validateTagAttributes"""
		out = {}
		if element not in _whitelist:
			return out
		whitelist = _whitelist[element]
		for attribute in attribs:
			value = attribs[attribute]
			if attribute not in whitelist:
				continue
			# Strip javascript "expression" from stylesheets.
			# http://msdn.microsoft.com/workshop/author/dhtml/overview/recalc.asp
			if attribute == u'style':
				value = self.checkCss(value)
				if value == False:
					continue
			elif attribute == u'id':
				value = self.escapeId(value)
			# If this attribute was previously set, override it.
			# Output should only have one attribute of each name.
			out[attribute] = value
		return out

	def safeEncodeAttribute(self, encValue):
		"""docstring for safeEncodeAttribute"""
		encValue = encValue.replace(u'&', u'&amp;')
		encValue = encValue.replace(u'<', u'&lt;')
		encValue = encValue.replace(u'>', u'&gt;')
		encValue = encValue.replace(u'"', u'&quot;')
		encValue = encValue.replace(u'{', u'&#123;')
		encValue = encValue.replace(u'[', u'&#91;')
		encValue = encValue.replace(u"''", u'&#39;&#39;')
		encValue = encValue.replace(u'ISBN', u'&#73;SBN')
		encValue = encValue.replace(u'RFC', u'&#82;FC')
		encValue = encValue.replace(u'PMID', u'&#80;MID')
		encValue = encValue.replace(u'|', u'&#124;')
		encValue = encValue.replace(u'__', u'&#95;_')
		encValue = encValue.replace(u'\n', u'&#10;')
		encValue = encValue.replace(u'\r', u'&#13;')
		encValue = encValue.replace(u'\t', u'&#9;')
		return encValue

	def fixTagAttributes(self, text, element):
		if text.strip() == u'':
			return u''

		stripped = self.validateTagAttributes(self.decodeTagAttributes(text), element)

		sb = []

		for attribute in stripped:
			value = stripped[attribute]
			encAttribute = attribute.replace(u'&', u'&amp;').replace(u'<', u'&lt;').replace(u'>', u'&gt;')
			encValue = self.safeEncodeAttribute(value)

			sb.append(u' ')
			sb.append(encAttribute)
			sb.append(u'="')
			sb.append(encValue)
			sb.append(u'"')

		return u''.join(sb)

	def validateCodepoint(self, codepoint):
		return codepoint ==	0x09 \
			or codepoint ==	0x0a \
			or codepoint ==	0x0d \
			or (codepoint >=	0x20 and codepoint <=   0xd7ff) \
			or (codepoint >=  0xe000 and codepoint <=   0xfffd) \
			or (codepoint >= 0x10000 and codepoint <= 0x10ffff)

	def _normalizeCallback(self, match):
		text, norm, dec, hexval, _ = match.groups()
		if norm:
			sb = []
			sb.append(u'&')
			if norm not in _htmlEntities:
				sb.append(u'amp;')
			sb.append(norm)
			sb.append(u';')
			return u''.join(sb)
		elif dec:
			dec = int(dec)
			if self.validateCodepoint(dec):
				sb = []
				sb.append(u'&#')
				sb.append(dec)
				sb.append(u';')
				return u''.join(sb)
		elif hexval:
			hexval = int(hexval, 16)
			if self.validateCodepoint(hexval):
				sb = []
				sb.append(u'&#x')
				sb.append(hex(hexval))
				sb.append(u';')
				return u''.join(sb)
		return text.replace(u'&', u'&amp;').replace(u'<', u'&lt;').replace(u'>', u'&gt;')

	def normalizeCharReferences(self, text):
		"""docstring for normalizeCharReferences"""
		return _charRefsPat.sub(self._normalizeCallback, text)

	def _decodeCallback(self, match):
		text, norm, dec, hexval, _ = match.groups()
		if norm:
			if norm in _htmlEntities:
				return unichr(_htmlEntities[norm])
			else:
				sb = []
				sb.append(u'&')
				sb.append(norm)
				sb.append(u';')
				return u''.join(sb)
		elif dec:
			dec = int(dec)
			if self.validateCodepoint(dec):
				return unichr(dec)
			return u'?'
		elif hexval:
			hexval = int(hexval, 16)
			if self.validateCodepoint(dec):
				return unichr(dec)
			return u'?'
		return text

	def decodeCharReferences(self, text):
		"""docstring for decodeCharReferences"""
		if text:
			return _charRefsPat.sub(self._decodeCallback, text)
		return ''

	def _convertToUtf8(self, s):
		return unichr(int(s.group(1), 16))

	def checkCss(self, value):
		"""docstring for checkCss"""
		stripped = self.decodeCharReferences(value)

		stripped = _cssCommentPat.sub(u'', stripped)
		value = stripped

		stripped = _toUTFPat.sub(self._convertToUtf8, stripped)
		stripped.replace(u'\\', u'')
		if _hackPat.search(stripped):
			# someone is haxx0ring
			return False

		return value

	def escapeId(self, value):
		"""docstring for escapeId"""
		# TODO
		return safe_name(value)

	def parseHorizontalRule(self, text):
		return _hrPat.sub(ur'<hr />', text)

	def parseHeaders(self, text):
		text = _h6Pat.sub(ur'<h6>\1</h6>', text)
		text = _h5Pat.sub(ur'<h5>\1</h5>', text)
		text = _h4Pat.sub(ur'<h4>\1</h4>', text)
		text = _h3Pat.sub(ur'<h3>\1</h3>', text)
		text = _h2Pat.sub(ur'<h2>\1</h2>', text)
		text = _h1Pat.sub(ur'<h1>\1</h1>', text)
		return text

	def parseQuotes(self, text):
		arr = _quotePat.split(text)
		if len(arr) == 1:
			return text
		# First, do some preliminary work. This may shift some apostrophes from
		# being mark-up to being text. It also counts the number of occurrences
		# of bold and italics mark-ups.
		numBold = 0
		numItalics = 0
		for i,r in zip(range(len(arr)), arr):
			if i%2 == 1:
				l = len(r)
				if l == 4:
					arr[i-1] += u"'"
					arr[i] = u"'''"
				elif l > 5:
					arr[i-1] += u"'" * (len(arr[i]) - 5)
					arr[i] = u"'''''"
				if l == 2:
					numItalics += 1
				elif l >= 5:
					numItalics += 1
					numBold += 1
				else:
					numBold += 1

		# If there is an odd number of both bold and italics, it is likely
		# that one of the bold ones was meant to be an apostrophe followed
		# by italics. Which one we cannot know for certain, but it is more
		# likely to be one that has a single-letter word before it.
		if numBold%2 == 1 and numItalics%2 == 1:
			firstSingleLetterWord = -1
			firstMultiLetterWord = -1
			firstSpace = -1
			for i,r in zip(range(len(arr)), arr):
				if i%2 == 1 and len(r) == 3:
					x1 = arr[i-1][-1:]
					x2 = arr[i-1][-2:-1]
					if x1 == u' ':
						if firstSpace == -1:
							firstSpace = i
					elif x2 == u' ':
						if firstSingleLetterWord == -1:
							firstSingleLetterWord = i
					else:
						if firstMultiLetterWord == -1:
							firstMultiLetterWord = i

			# If there is a single-letter word, use it!
			if firstSingleLetterWord > -1:
				arr[firstSingleLetterWord] = u"''"
				arr[firstSingleLetterWord-1] += u"'"
			# If not, but there's a multi-letter word, use that one.
			elif firstMultiLetterWord > -1:
				arr[firstMultiLetterWord] = u"''"
				arr[firstMultiLetterWord-1] += u"'"
			# ... otherwise use the first one that has neither.
			# (notice that it is possible for all three to be -1 if, for example,
			# there is only one pentuple-apostrophe in the line)
			elif firstSpace > -1:
				arr[firstSpace] = u"''"
				arr[firstSpace-1] += u"'"

		# Now let's actually convert our apostrophic mush to HTML!
		output = []
		buffer = None
		state = ''
		for i,r in zip(range(len(arr)), arr):
			if i%2 == 0:
				if state == 'both':
					buffer.append(r)
				else:
					output.append(r)
			else:
				if len(r) == 2:
					if state == 'i':
						output.append(u"</i>")
						state = ''
					elif state == 'bi':
						output.append(u"</i>")
						state = 'b'
					elif state == 'ib':
						output.append(u"</b></i><b>")
						state = 'b'
					elif state == 'both':
						output.append(u"<b><i>")
						output.append(u''.join(buffer))
						buffer = None
						output.append(u"</i>")
						state = 'b'
					elif state == 'b':
						output.append(u"<i>")
						state = 'bi'
					else: # ''
						output.append(u"<i>")
						state = 'i'
				elif len(r) == 3:
					if state == 'b':
						output.append(u"</b>")
						state = ''
					elif state == 'bi':
						output.append(u"</i></b><i>")
						state = 'i'
					elif state == 'ib':
						output.append(u"</b>")
						state = 'i'
					elif state == 'both':
						output.append(u"<i><b>")
						output.append(u''.join(buffer))
						buffer = None
						output.append(u"</b>")
						state = 'i'
					elif state == 'i':
						output.append(u"<b>")
						state = 'ib'
					else: # ''
						output.append(u"<b>")
						state = 'b'
				elif len(r) == 5:
					if state == 'b':
						output.append(u"</b><i>")
						state = 'i'
					elif state == 'i':
						output.append(u"</i><b>")
						state = 'b'
					elif state == 'bi':
						output.append(u"</i></b>")
						state = ''
					elif state == 'ib':
						output.append(u"</b></i>")
						state = ''
					elif state == 'both':
						output.append(u"<i><b>")
						output.append(u''.join(buffer))
						buffer = None
						output.append(u"</b></i>")
						state = ''
					else: # ''
						buffer = []
						state = 'both'

		if state == 'both':
			output.append(u"<i><b>")
			output.append(u''.join(buffer))
			buffer = None
			output.append(u"</b></i>")
		elif state != '':
			if state == 'b' or state == 'ib':
				output.append(u"</b>")
			if state == 'i' or state == 'bi' or state == 'ib':
				output.append(u"</i>")
			if state == 'bi':
				output.append(u"</b>")
		return u''.join(output)

	def parseAllQuotes(self, text):
		sb = []
		lines = text.split(u'\n')
		first = True
		for line in lines:
			if not first:
				sb.append(u'\n')
			else:
				first = False
			sb.append(self.parseQuotes(line))
		return u''.join(sb)

	def replaceExternalLinks(self, text):
		sb = []
		bits = _bracketedLinkPat.split(text)
		l = len(bits)
		i = 0
		num_links = 0
		while i < l:
			if i%3 == 0:
				#sb.append(self.replaceFreeExternalLinks(bits[i]))
				sb.append(bits[i])
				i += 1
			else:
				sb.append(u'<a href="')
				sb.append(bits[i])
				sb.append(u'">')
				if not bits[i+1]:
					num_links += 1
					sb.append(to_unicode(truncate_url(bits[i])))
				else:
					sb.append(bits[i+1])
				sb.append(u'</a>')
				i += 2
		return ''.join(sb)

	# TODO: fix this so it actually works
	def replaceFreeExternalLinks(self, text):
		bits = _protocolPat.split(text)
		sb = [bits.pop(0)]
		i = 0
		l = len(bits)
		while i < l:
			protocol = bits[i]
			remainder = bits[i+1]
			i += 2
			match = _specialUrlPat.match(remainder)
			if match:
				# Found some characters after the protocol that look promising
				url = protocol + match.group(1)
				trail = match.group(2)

				# special case: handle urls as url args:
				# http://www.example.com/foo?=http://www.example.com/bar
				if len(trail) == 0 and len(bits) > i and _protocolsPat.match(bits[i]):
					match = _specialUrlPat.match(remainder)
					if match:
						url += bits[i] + match.group(1)
						i += 2
						trail = match.group(2)

				# The characters '<' and '>' (which were escaped by
				# removeHTMLtags()) should not be included in
				# URLs, per RFC 2396.
				pos = max(url.find('&lt;'), url.find('&gt;'))
				if pos != -1:
					trail = url[pos:] + trail
					url = url[0:pos]

				sep = ',;.:!?'
				if '(' not in url:
					sep += ')'

				i = len(url)-1
				while i >= 0:
					char = url[i]
					if char not in sep:
						break
					i -= 1
				i += 1

				if i != len(url):
					trail = url[i:] + trail
					url = url[0:i]

				url = self.cleanURL(url)

				sb.append(u'<a href="')
				sb.append(url)
				sb.append(u'">')
				sb.append(truncate_url(url))
				sb.append(u'</a>')
				#sb.append(text)
				sb.append(trail)
			else:
				sb.append(protocol)
				sb.append(remainder)
		return ''.join(sb)

	def urlencode(self, char):
		num = ord(char)
		if num == 32:
			return '+'
		return "%%%02x" % num

	def cleanURL(self, url):
		# Normalize any HTML entities in input. They will be
		# re-escaped by makeExternalLink().
		url = self.decodeCharReferences(url)

		# Escape any control characters introduced by the above step
		url = _controlCharsPat.sub(self.urlencode, url)

		# Validate hostname portion
		match = _hostnamePat.match(url)
		if match:
			protocol, host, rest = match.groups()

			# Characters that will be ignored in IDNs.
			# http://tools.ietf.org/html/3454#section-3.1
			# Strip them before further processing so blacklists and such work.

			_stripPat.sub('', host)

			# @fixme: validate hostnames here

			return protocol + host + rest
		else:
			return url

	def unstripForHTML(self, text):
		text = self.unstrip(text)
		text = self.unstripNoWiki(text)
		return text

	def unstrip(self, text):
		if 'general' not in self.strip_state:
			return text

		general = self.strip_state['general']
		for k in general:
			v = general[k]
			text = text.replace(k, v)
		return text

	def unstripNoWiki(self, text):
		if 'nowiki' not in self.strip_state:
			return text
		nowiki = self.strip_state['nowiki']
		for k in nowiki:
			v = nowiki[k]
			text = text.replace(k, v)
		return text

	def extractTagsAndParams(self, elements, text, matches):
		"""
		Replaces all occurrences of HTML-style comments and the given tags
		in the text with a random marker and returns teh next text. The output
		parameter $matches will be an associative array filled with data in
		the form:
		  'UNIQ-xxxxx' => array(
		  'element',
		  'tag content',
		  array( 'param' => 'x' ),
		  '<element param="x">tag content</element>' ) )
		"""
		stripped = u''

		taglist = u'|'.join(elements)
		if taglist not in _startRegexHash:
			_startRegexHash[taglist] = re.compile(ur"<(" + taglist + ur")(\s+[^>]*?|\s*?)(/?>)|<(!--)", re.UNICODE | re.IGNORECASE)
		start = _startRegexHash[taglist]

		while text != u'':
			p = start.split(text, 1)
			stripped += p[0]
			if len(p) == 1:
				break
			elif p[4]:
				# comment
				element = p[4]
				attributes = u''
				close = u''
			else:
				element = p[1]
				attributes = p[2]
				close = p[3]
			inside = p[5]

			global _extractTagsAndParams_n
			marker = self.uniq_prefix + u'-' + element + u'-' + (u"%08X" % _extractTagsAndParams_n) + u'-QINU'
			_extractTagsAndParams_n += 1
			stripped += marker

			if close == u'/>':
				# empty element tag, <tag />
				content = None
				text = inside
				tail = None
			else:
				if element == u'!--':
					end = _endCommentPat
				else:
					if element not in _endRegexHash:
						_endRegexHash[element] = re.compile(ur'(</' + element + ur'\s*>)', re.UNICODE | re.IGNORECASE)
					end = _endRegexHash[element]
				q = end.split(inside, 1)
				content = q[0]
				if len(q) < 3:
					# no end tag
					tail = ''
					text = ''
				else:
					tail = q[1]
					text = q[2]

			matches[marker] = (
				element,
				content,
				self.decodeTagAttributes(attributes),
				u"<" + element + attributes + close + content + tail
			)
		return stripped

	def fixtags(self, text):
		"""Clean up special characters, only run once, next-to-last before doBlockLevels"""
		# french spaces, last one Guillemet-left
		# only if there is something before the space
		text = _guillemetLeftPat.sub(ur'\1&nbsp;\2', text)
		# french spaces, Guillemet-right
		text = _guillemetRightPat.sub(ur'\1&nbsp;', text)
		return text

	def closeParagraph(self, mLastSection):
		"""Used by doBlockLevels()"""
		result = u''
		if mLastSection != u'':
			result = u'</' + mLastSection + u'>\n'

		return result

	def getCommon(self, st1, st2):
		"""
		getCommon() returns the length of the longest common substring
		of both arguments, starting at the beginning of both.
		"""
		fl = len(st1)
		shorter = len(st2)
		if fl < shorter:
			shorter = fl

		i = 0
		while i < shorter:
			if st1[i] != st2[i]:
				break
			i += 1
		return i

	def openList(self, char, mLastSection):
		"""
		These next three functions open, continue, and close the list
		element appropriate to the prefix character passed into them.
		"""
		result = self.closeParagraph(mLastSection)

		mDTopen = False
		if char == u'*':
			result += u'<ul><li>'
		elif char == u'#':
			result += u'<ol><li>'
		elif char == u':':
			result += u'<dl><dd>'
		elif char == u';':
			result += u'<dl><dt>'
			mDTopen = True
		else:
			result += u'<!-- ERR 1 -->'

		return result, mDTopen

	def nextItem(self, char, mDTopen):
		if char == u'*' or char == '#':
			return u'</li><li>', None
		elif char == u':' or char == u';':
			close = u'</dd>'
			if mDTopen:
				close = '</dt>'
			if char == u';':
				return close + u'<dt>', True
			else:
				return close + u'<dd>', False
		return u'<!-- ERR 2 -->'

	def closeList(self, char, mDTopen):
		if char == u'*':
			return u'</li></ul>\n'
		elif char == u'#':
			return u'</li></ol>\n'
		elif char == u':':
			if mDTopen:
				return u'</dt></dl>\n'
			else:
				return u'</dd></dl>\n'
		else:
			return u'<!-- ERR 3 -->'

	def findColonNoLinks(self, text, before, after):
		try:
			pos = text.search(':')
		except:
			return False

		lt = text.find('<')
		if lt == -1 or lt > pos:
			# Easy; no tag nesting to worry about
			before = text[0:pos]
			after = text[0:pos+1]
			return before, after, pos

		# Ugly state machine to walk through avoiding tags.
		state = MW_COLON_STATE_TEXT;
		stack = 0;
		i = 0
		while i < len(text):
			c = text[i];

			if state == 0: # MW_COLON_STATE_TEXT:
				if text[i] == '<':
					# Could be either a <start> tag or an </end> tag
					state = MW_COLON_STATE_TAGSTART
				elif text[i] == ':':
					if stack == 0:
						# we found it
						return text[0:i], text[i+1], i
				else:
					# Skip ahead looking for something interesting
					try:
						colon = text.search(':', i)
					except:
						return False
					lt = text.find('<', i)
					if stack == 0:
						if lt == -1 or colon < lt:
							# we found it
							return text[0:colon], text[colon+1], i
					if lt == -1:
						break
					# Skip ahead to next tag start
					i = lt
					state = MW_COLON_STATE_TAGSTART
			elif state == 1: # MW_COLON_STATE_TAG:
				# In a <tag>
				if text[i] == '>':
					stack += 1
					state = MW_COLON_STATE_TEXT
				elif text[i] == '/':
					state = MW_COLON_STATE_TAGSLASH
			elif state == 2: # MW_COLON_STATE_TAGSTART:
				if text[i] == '/':
					state = MW_COLON_STATE_CLOSETAG
				elif text[i] == '!':
					state = MW_COLON_STATE_COMMENT
				elif text[i] == '>':
					# Illegal early close? This shouldn't happen D:
					state = MW_COLON_STATE_TEXT
				else:
					state = MW_COLON_STATE_TAG
			elif state == 3: # MW_COLON_STATE_CLOSETAG:
				# In a </tag>
				if text[i] == '>':
					stack -= 1
					if stack < 0:
						return False
					state = MW_COLON_STATE_TEXT
			elif state == MW_COLON_STATE_TAGSLASH:
				if text[i] == '>':
					# Yes, a self-closed tag <blah/>
					state = MW_COLON_STATE_TEXT
				else:
					# Probably we're jumping the gun, and this is an attribute
					state = MW_COLON_STATE_TAG
			elif state == 5: # MW_COLON_STATE_COMMENT:
				if text[i] == '-':
					state = MW_COLON_STATE_COMMENTDASH
			elif state == MW_COLON_STATE_COMMENTDASH:
				if text[i] == '-':
					state = MW_COLON_STATE_COMMENTDASHDASH
				else:
					state = MW_COLON_STATE_COMMENT
			elif state == MW_COLON_STATE_COMMENTDASHDASH:
				if text[i] == '>':
					state = MW_COLON_STATE_TEXT
				else:
					state = MW_COLON_STATE_COMMENT
			else:
				raise
		if stack > 0:
			return False
		return False

	def doBlockLevels(self, text, linestart):
		# Parsing through the text line by line.  The main thing
		# happening here is handling of block-level elements p, pre,
		# and making lists from lines starting with * # : etc.
		lastPrefix = u''
		mDTopen = inBlockElem = False
		prefixLength = 0
		paragraphStack = False
		_closeMatchPat = re.compile(ur"(</table|</blockquote|</h1|</h2|</h3|</h4|</h5|</h6|<td|<th|<div|</div|<hr|</pre|</p|" +  self.uniq_prefix + ur"-pre|</li|</ul|</ol|<center)", re.UNICODE | re.IGNORECASE)
		mInPre = False
		mLastSection = u''
		mDTopen = False
		output = []
		for oLine in text.split('\n')[not linestart and 1 or 0:]:
			lastPrefixLength = len(lastPrefix)
			preCloseMatch = _closePrePat.search(oLine)
			preOpenMatch = _openPrePat.search(oLine)
			if not mInPre:
				chars = u'*#:;'
				prefixLength = 0
				for c in oLine:
					if c in chars:
						prefixLength += 1
					else:
						break
				pref = oLine[0:prefixLength]

				# eh?
				pref2 = pref.replace(u';', u':')
				t = oLine[prefixLength:]
				mInPre = bool(preOpenMatch)
			else:
				# Don't interpret any other prefixes in preformatted text
				prefixLength = 0
				pref = pref2 = u''
				t = oLine

			# List generation
			if prefixLength and lastPrefix == pref2:
				# Same as the last item, so no need to deal with nesting or opening stuff
				tmpOutput, tmpMDTopen = self.nextItem(pref[-1:], mDTopen)
				output.append(tmpOutput)
				if tmpMDTopen is not None:
					mDTopen = tmpMDTopen
				paragraphStack = False

				if pref[-1:] == u';':
					# The one nasty exception: definition lists work like this:
					# ; title : definition text
					# So we check for : in the remainder text to split up the
					# title and definition, without b0rking links.
					term = t2 = u''
					z = self.findColonNoLinks(t, term, t2)
					if z != False:
						term, t2 = z[1:2]
						t = t2
						output.append(term)
						tmpOutput, tmpMDTopen = self.nextItem(u':', mDTopen)
						output.append(tmpOutput)
						if tmpMDTopen is not None:
							mDTopen = tmpMDTopen

			elif prefixLength or lastPrefixLength:
				# Either open or close a level...
				commonPrefixLength = self.getCommon(pref, lastPrefix)
				paragraphStack = False
				while commonPrefixLength < lastPrefixLength:
					tmp = self.closeList(lastPrefix[lastPrefixLength-1], mDTopen)
					output.append(tmp)
					mDTopen = False
					lastPrefixLength -= 1
				if prefixLength <= commonPrefixLength and commonPrefixLength > 0:
					tmpOutput, tmpMDTopen = self.nextItem(pref[commonPrefixLength-1], mDTopen)
					output.append(tmpOutput)
					if tmpMDTopen is not None:
						mDTopen = tmpMDTopen

				while prefixLength > commonPrefixLength:
					char = pref[commonPrefixLength:commonPrefixLength+1]
					tmpOutput, tmpMDTOpen = self.openList(char, mLastSection)
					if tmpMDTOpen:
						mDTopen = True
					output.append(tmpOutput)
					mLastSection = u''
					mInPre = False

					if char == u';':
						# FIXME: This is dupe of code above
						term = t2 = u''
						z = self.findColonNoLinks(t, term, t2)
						if z != False:
							term, t2 = z[1:2]
							t = t2
							output.append(term)
							tmpOutput, tmpMDTopen = self.nextItem(u':', mDTopen)
							output.append(tmpOutput)
							if tmpMDTopen is not None:
								mDTopen = tmpMDTopen

					commonPrefixLength += 1

				lastPrefix = pref2

			if prefixLength == 0:
				# No prefix (not in list)--go to paragraph mode
				# XXX: use a stack for nestable elements like span, table and div
				openmatch = _openMatchPat.search(t)
				closematch = _closeMatchPat.search(t)
				if openmatch or closematch:
					paragraphStack = False
					output.append(self.closeParagraph(mLastSection))
					mLastSection = u''
					if preCloseMatch:
						mInPre = False
					if preOpenMatch:
						mInPre = True
					inBlockElem = bool(not closematch)
				elif not inBlockElem and not mInPre:
					if t[0:1] == u' ' and (mLastSection ==  u'pre' or t.strip() != u''):
						# pre
						if mLastSection != u'pre':
							paragraphStack = False
							output.append(self.closeParagraph(u'') + u'<pre>')
							mInPre = False
							mLastSection = u'pre'
						t = t[1:]
					else:
						# paragraph
						if t.strip() == u'':
							if paragraphStack:
								output.append(paragraphStack + u'<br />')
								paragraphStack = False
								mLastSection = u'p'
							else:
								if mLastSection != u'p':
									output.append(self.closeParagraph(mLastSection))
									mLastSection = u''
									mInPre = False
									paragraphStack = u'<p>'
								else:
									paragraphStack = u'</p><p>'
						else:
							if paragraphStack:
								output.append(paragraphStack)
								paragraphStack = False
								mLastSection = u'p'
							elif mLastSection != u'p':
								output.append(self.closeParagraph(mLastSection) + u'<p>')
								mLastSection = u'p'
								mInPre = False

			# somewhere above we forget to get out of pre block (bug 785)
			if preCloseMatch and mInPre:
				mInPre = False

			if paragraphStack == False:
				output.append(t + u"\n")

		while prefixLength:
			output.append(self.closeList(pref2[prefixLength-1], mDTopen))
			mDTopen = False
			prefixLength -= 1

		if mLastSection != u'':
			output.append(u'</' + mLastSection + u'>')
			mLastSection = u''

		return ''.join(output)

class Parser(BaseParser):
	def __init__(self, show_toc=True):
		super(Parser, self).__init__()
		self.show_toc = show_toc

	def parse(self, text):
		utf8 = isinstance(text, str)
		text = to_unicode(text)
		if text[-1:] != u'\n':
			text = text + u'\n'
			taggedNewline = True
		else:
			taggedNewline = False

		text = self.strip(text)
		text = self.removeHtmlTags(text)
		text = self.doTableStuff(text)
		text = self.parseHorizontalRule(text)
		text = self.checkTOC(text)
		text = self.parseHeaders(text)
		text = self.parseAllQuotes(text)
		text = self.replaceExternalLinks(text)
		if not self.show_toc and text.find(u"<!--MWTOC-->") == -1:
			self.show_toc = False
		text = self.formatHeadings(text, True)
		text = self.unstrip(text)
		text = self.fixtags(text)
		text = self.doBlockLevels(text, True)
		text = self.unstripNoWiki(text)
		text = text.split(u'\n')
		text = u'\n'.join(text)
		if taggedNewline and text[-1:] == u'\n':
			text = text[:-1]
		if utf8:
			return text.encode("utf-8")
		return text

	def checkTOC(self, text):
		if text.find(u"__NOTOC__") != -1:
			text = text.replace(u"__NOTOC__", u"")
			self.show_toc = False
		if text.find(u"__TOC__") != -1:
			text = text.replace(u"__TOC__", u"<!--MWTOC-->")
			self.show_toc = True
		return text

	def doTableStuff(self, text):
		t = text.split(u"\n")
		td = [] # Is currently a td tag open?
		ltd = [] # Was it TD or TH?
		tr = [] # Is currently a tr tag open?
		ltr = [] # tr attributes
		has_opened_tr = [] # Did this table open a <tr> element?
		indent_level = 0 # indent level of the table

		for k, x in zip(range(len(t)), t):
			x = x.strip()
			fc = x[0:1]
			matches = _zomgPat.match(x)
			if matches:
				indent_level = len(matches.group(1))

				attributes = self.unstripForHTML(matches.group(2))

				t[k] = u'<dl><dd>'*indent_level + u'<table' + self.fixTagAttributes(attributes, u'table') + u'>'
				td.append(False)
				ltd.append(u'')
				tr.append(False)
				ltr.append(u'')
				has_opened_tr.append(False)
			elif len(td) == 0:
				pass
			elif u'|}' == x[0:2]:
				z = u"</table>" + x[2:]
				l = ltd.pop()
				if not has_opened_tr.pop():
					z = u"<tr><td></td><tr>" + z
				if tr.pop():
					z = u"</tr>" + z
				if td.pop():
					z = u'</' + l + u'>' + z
				ltr.pop()
				t[k] = z + u'</dd></dl>'*indent_level
			elif u'|-' == x[0:2]: # Allows for |-------------
				x = x[1:]
				while x != u'' and x[0:1] == '-':
					x = x[1:]
				z = ''
				l = ltd.pop()
				has_opened_tr.pop()
				has_opened_tr.append(True)
				if tr.pop():
					z = u'</tr>' + z
				if td.pop():
					z = u'</' + l + u'>' + z
				ltr.pop()
				t[k] = z
				tr.append(False)
				td.append(False)
				ltd.append(u'')
				attributes = self.unstripForHTML(x)
				ltr.append(self.fixTagAttributes(attributes, u'tr'))
			elif u'|' == fc or u'!' == fc or u'|+' == x[0:2]: # Caption
				# x is a table row
				if u'|+' == x[0:2]:
					fc = u'+'
					x = x[1:]
				x = x[1:]
				if fc == u'!':
					x = x.replace(u'!!', u'||')
				# Split up multiple cells on the same line.
				# FIXME: This can result in improper nesting of tags processed
				# by earlier parser steps, but should avoid splitting up eg
				# attribute values containing literal "||".
				x = x.split(u'||')

				t[k] = u''

				# Loop through each table cell
				for theline in x:
					z = ''
					if fc != u'+':
						tra = ltr.pop()
						if not tr.pop():
							z = u'<tr' + tra + u'>\n'
						tr.append(True)
						ltr.append(u'')
						has_opened_tr.pop()
						has_opened_tr.append(True)
					l = ltd.pop()
					if td.pop():
						z = u'</' + l + u'>' + z
					if fc == u'|':
						l = u'td'
					elif fc == u'!':
						l = u'th'
					elif fc == u'+':
						l = u'caption'
					else:
						l = u''
					ltd.append(l)

					#Cell parameters
					y = theline.split(u'|', 1)
					# Note that a '|' inside an invalid link should not
					# be mistaken as delimiting cell parameters
					if y[0].find(u'[[') != -1:
						y = [theline]

					if len(y) == 1:
						y = z + u"<" + l + u">" + y[0]
					else:
						attributes = self.unstripForHTML(y[0])
						y = z + u"<" + l + self.fixTagAttributes(attributes, l) + u">" + y[1]

					t[k] += y
					td.append(True)

		while len(td) > 0:
			l = ltd.pop()
			if td.pop():
				t.append(u'</td>')
			if tr.pop():
				t.append(u'</tr>')
			if not has_opened_tr.pop():
				t.append(u'<tr><td></td></tr>')
			t.append(u'</table>')

		text = u'\n'.join(t)
		# special case: don't return empty table
		if text == u"<table>\n<tr><td></td></tr>\n</table>":
			text = u''

		return text

	def formatHeadings(self, text, isMain):
		"""
		This function accomplishes several tasks:
		1) Auto-number headings if that option is enabled
		2) Add an [edit] link to sections for logged in users who have enabled the option
		3) Add a Table of contents on the top for users who have enabled the option
		4) Auto-anchor headings

		It loops through all headlines, collects the necessary data, then splits up the
		string and re-inserts the newly formatted headlines.
		"""
		doNumberHeadings = False
		showEditLink = True # Can User Edit

		if text.find(u"__NOEDITSECTION__") != -1:
			showEditLink = False
			text = text.replace(u"__NOEDITSECTION__", u"")

		# Get all headlines for numbering them and adding funky stuff like [edit]
		# links - this is for later, but we need the number of headlines right now
		matches = _headerPat.findall(text)
		numMatches = len(matches)

		# if there are fewer than 4 headlines in the article, do not show TOC
		# unless it's been explicitly enabled.
		enoughToc = self.show_toc and (numMatches >= 4 or text.find(u"<!--MWTOC-->") != -1)

		# Allow user to stipulate that a page should have a "new section"
		# link added via __NEWSECTIONLINK__
		showNewSection = False
		if text.find(u"__NEWSECTIONLINK__") != -1:
			showNewSection = True
			text = text.replace(u"__NEWSECTIONLINK__", u"")
		# if the string __FORCETOC__ (not case-sensitive) occurs in the HTML,
		# override above conditions and always show TOC above first header
		if text.find(u"__FORCETOC__") != -1:
			self.show_toc = True
			enoughToc = True
			text = text.replace(u"__FORCETOC__", u"")
		# Never ever show TOC if no headers
		if numMatches < 1:
			enoughToc = False

		# headline counter
		headlineCount = 0
		sectionCount = 0 # headlineCount excluding template sections

		# Ugh .. the TOC should have neat indentation levels which can be
		# passed to the skin functions. These are determined here
		toc = []
		head = {}
		sublevelCount = {}
		levelCount = {}
		toclevel = 0
		level = 0
		prevlevel = 0
		toclevel = 0
		prevtoclevel = 0
		refers = {}
		refcount = {}
		wgMaxTocLevel = 5

		for match in matches:
			headline = match[2]
			istemplate = False
			templatetitle = u''
			templatesection = 0
			numbering = []

			m = _templateSectionPat.search(headline)
			if m:
				istemplate = True
				templatetitle = b64decode(m[0])
				templatesection = 1 + int(b64decode(m[1]))
				headline = _templateSectionPat.sub(u'', headline)

			if toclevel:
				prevlevel = level
				prevtoclevel = toclevel

			level = matches[headlineCount][0]

			if doNumberHeadings or enoughToc:
				if level > prevlevel:
					toclevel += 1
					sublevelCount[toclevel] = 0
					if toclevel < wgMaxTocLevel:
						toc.append(u'\n<ul>')
				elif level < prevlevel and toclevel > 1:
					# Decrease TOC level, find level to jump to

					if toclevel == 2 and level < levelCount[1]:
						toclevel = 1
					else:
						for i in range(toclevel, 0, -1):
							if levelCount[i] == level:
								# Found last matching level
								toclevel = i
								break
							elif levelCount[i] < level:
								toclevel = i + 1
								break
					if toclevel < wgMaxTocLevel:
						toc.append(u"</li>\n")
						toc.append(u"</ul>\n</li>\n" * max(prevtoclevel - toclevel, 0))
				else:
					if toclevel < wgMaxTocLevel:
						toc.append(u"</li>\n")

				levelCount[toclevel] = level

				# count number of headlines for each level
				sublevelCount[toclevel] += 1
				for i in range(1, toclevel+1):
					if sublevelCount[i]:
						numbering.append(to_unicode(sublevelCount[i]))

			# The canonized header is a version of the header text safe to use for links
			# Avoid insertion of weird stuff like <math> by expanding the relevant sections
			canonized_headline = self.unstrip(headline)
			canonized_headline = self.unstripNoWiki(canonized_headline)

			# -- don't know what to do with this yet.
			# Remove link placeholders by the link text.
			#	 <!--LINK number-->
			# turns into
			#	 link text with suffix
	#		$canonized_headline = preg_replace( '/<!--LINK ([0-9]*)-->/e',
	#							"\$this->mLinkHolders['texts'][\$1]",
	#							$canonized_headline );
	#		$canonized_headline = preg_replace( '/<!--IWLINK ([0-9]*)-->/e',
	#							"\$this->mInterwikiLinkHolders['texts'][\$1]",
	#							$canonized_headline );

			# strip out HTML
			canonized_headline = _tagPat.sub(u'', canonized_headline)
			tocline = canonized_headline.strip()
			# Save headline for section edit hint before it's escaped
			headline_hint = tocline
			canonized_headline = self.escapeId(tocline)
			refers[headlineCount] = canonized_headline

			# count how many in assoc. array so we can track dupes in anchors
			if canonized_headline not in refers:
				refers[canonized_headline] = 1
			else:
				refers[canonized_headline] += 1
			refcount[headlineCount] = refers[canonized_headline]

			numbering = '.'.join(numbering)

			# Don't number the heading if it is the only one (looks silly)
			if doNumberHeadings and numMatches > 1:
				# the two are different if the line contains a link
				headline = numbering + u' ' + headline

			# Create the anchor for linking from the TOC to the section
			anchor = canonized_headline;
			if refcount[headlineCount] > 1:
				anchor += u'_' + unicode(refcount[headlineCount])

			if enoughToc:
				toc.append(u'\n<li class="toclevel-')
				toc.append(to_unicode(toclevel))
				toc.append(u'"><a href="#w_')
				toc.append(anchor)
				toc.append(u'"><span class="tocnumber">')
				toc.append(numbering)
				toc.append(u'</span> <span class="toctext">')
				toc.append(tocline)
				toc.append(u'</span></a>')

	#		if showEditLink and (not istemplate or templatetitle != u""):
	#			if not head[headlineCount]:
	#				head[headlineCount] = u''
	#
	#			if istemplate:
	#				head[headlineCount] += sk.editSectionLinkForOther(templatetile, templatesection)
	#			else:
	#				head[headlineCount] += sk.editSectionLink(mTitle, sectionCount+1, headline_hint)

			# give headline the correct <h#> tag
			if headlineCount not in head:
				head[headlineCount] = []
			h = head[headlineCount]
			h.append(u'<h')
			h.append(to_unicode(level))
			h.append(u' id="w_')
			h.append(anchor)
			h.append('">')
			h.append(matches[headlineCount][1].strip())
			h.append(headline.strip())
			h.append(u'</h')
			h.append(to_unicode(level))
			h.append(u'>')

			headlineCount += 1

			if not istemplate:
				sectionCount += 1

		if enoughToc:
			if toclevel < wgMaxTocLevel:
				toc.append(u"</li>\n")
				toc.append(u"</ul>\n</li>\n" * max(0, toclevel - 1))
			#TODO: use gettext
			#toc.insert(0, u'<div id="toc"><h2>' + _('Table of Contents') + '</h2>')
			toc.insert(0, u'<div id="toc"><h2>Table of Contents</h2>')
			toc.append(u'</ul>\n</div>')

		# split up and insert constructed headlines

		blocks = _headerPat.split(text)

		i = 0
		len_blocks = len(blocks)
		forceTocPosition = text.find(u"<!--MWTOC-->")
		full = []
		while i < len_blocks:
			j = i/4
			full.append(blocks[i])
			if enoughToc and not i and isMain and forceTocPosition == -1:
				full += toc
				toc = None
			if j in head and head[j]:
				full += head[j]
				head[j] = None
			i += 4
		full = u''.join(full)
		if forceTocPosition != -1:
			return full.replace(u"<!--MWTOC-->", u''.join(toc), 1)
		else:
			return full

def parse(text, showToc=True):
	"""Returns HTML from MediaWiki markup"""
	p = Parser(show_toc=showToc)
	return p.parse(text)

def parselite(text):
	"""Returns HTML from MediaWiki markup ignoring
	without headings"""
	p = BaseParser()
	return p.parse(text)

def truncate_url(url, length=40):
	if len(url) <= length:
		return url
	import re
	pattern = r'(/[^/]+/?)$'
	match = re.search(pattern, url)
	if not match:
		return url
	l = len(match.group(1))
	domain = url.replace(match.group(1), '')
	firstpart = url[0:len(url)-l]
	secondpart = match.group(1)
	if firstpart == firstpart[0:length-3]:
		secondpart = secondpart[0:length-3] + '...'
	else:
		firstpart = firstpart[0:length-3]
		secondpart = '...' + secondpart
	t_url = firstpart+secondpart
	return t_url

def to_unicode(text, charset=None):
	"""Convert a `str` object to an `unicode` object.

	If `charset` is given, we simply assume that encoding for the text,
	but we'll use the "replace" mode so that the decoding will always
	succeed.
	If `charset` is ''not'' specified, we'll make some guesses, first
	trying the UTF-8 encoding, then trying the locale preferred encoding,
	in "replace" mode. This differs from the `unicode` builtin, which
	by default uses the locale preferred encoding, in 'strict' mode,
	and is therefore prompt to raise `UnicodeDecodeError`s.

	Because of the "replace" mode, the original content might be altered.
	If this is not what is wanted, one could map the original byte content
	by using an encoding which maps each byte of the input to an unicode
	character, e.g. by doing `unicode(text, 'iso-8859-1')`.
	"""
	if not isinstance(text, str):
		if isinstance(text, Exception):
			# two possibilities for storing unicode strings in exception data:
			try:
				# custom __str__ method on the exception (e.g. PermissionError)
				return unicode(text)
			except UnicodeError:
				# unicode arguments given to the exception (e.g. parse_date)
				return ' '.join([to_unicode(arg) for arg in text.args])
		return unicode(text)
	if charset:
		return unicode(text, charset, 'replace')
	else:
		try:
			return unicode(text, 'utf-8')
		except UnicodeError:
			return unicode(text, locale.getpreferredencoding(), 'replace')

# tag hooks
mTagHooks = {}

## IMPORTANT
## Make sure all hooks output CLEAN html. Escape any user input BEFORE it's returned

# Arguments passed:
# - wiki environment instance
# - tag content
# - dictionary of attributes

# quote example:
# <quote cite="person">quote</quote>
from cgi import escape

def hook_quote(env, body, attributes={}):
	text = [u'<div class="blockquote">']
	if 'cite' in attributes:
		text.append(u"<strong class=\"cite\">%s wrote:</strong>\n" % escape(attributes['cite']))
	text.append(body.strip())
	text.append(u'</div>')
	return u'\n'.join(text)
registerTagHook('quote', hook_quote)

def safe_name(name=None, remove_slashes=True):
	if name is None:
		return None
	name = str2url(name)
	if remove_slashes:
		name = re.sub(r"[^a-zA-Z0-9\-_\s\.]", "", name)
	else:
		name = re.sub(r"[^a-zA-Z0-9\-_\s\.\/]", "", name)
	name = re.sub(r"[\s\._]", "-", name)
	name = re.sub(r"[-]+", "-", name)
	return name.strip("-").lower()

def str2url(str):
	"""
	Takes a UTF-8 string and replaces all characters with the equivalent in 7-bit
	ASCII. It returns a plain ASCII string usable in URLs.
	"""
	try:
		str = str.encode('utf-8')
	except:
		pass
	mfrom	= "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝßàáâãäåæçèéêëìíîï"
	to		= "AAAAAAECEEEEIIIIDNOOOOOOUUUUYSaaaaaaaceeeeiiii"
	mfrom	+= "ñòóôõöøùúûüýÿĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģ"
	to		+= "noooooouuuuyyaaaaaaccccccccddddeeeeeeeeeegggggggg"
	mfrom	+= "ĤĥĦħĨĩĪīĬĭĮįİıĴĵĶķĸĹĺĻļĽľĿŀŁłŃńŅņŇňŉŊŋŌōŎŏŐőŒœŔŕŖŗŘř"
	to		+= "hhhhiiiiiiiiiijjkkkllllllllllnnnnnnnnnoooooooorrrrrr"
	mfrom	+= "ŚśŜŝŞşŠšŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽžſƀƂƃƄƅƇƈƉƊƐƑƒƓƔ"
	to		+= "ssssssssttttttuuuuuuuuuuuuwwyyyzzzzzzfbbbbbccddeffgv"
	mfrom	+= "ƖƗƘƙƚƝƞƟƠƤƦƫƬƭƮƯưƱƲƳƴƵƶǍǎǏǐǑǒǓǔǕǖǗǘǙǚǛǜǝǞǟǠǡǢǣǤǥǦǧǨǩ"
	to		+= "likklnnoopettttuuuuyyzzaaiioouuuuuuuuuueaaaaeeggggkk"
	mfrom	+= "ǪǫǬǭǰǴǵǷǸǹǺǻǼǽǾǿȀȁȂȃȄȅȆȇȈȉȊȋȌȍȎȏȐȑȒȓȔȕȖȗȘșȚțȞȟȤȥȦȧȨȩ"
	to		+= "oooojggpnnaaeeooaaaaeeeeiiiioooorrrruuuusstthhzzaaee"
	mfrom	+= "ȪȫȬȭȮȯȰȱȲȳḀḁḂḃḄḅḆḇḈḉḊḋḌḍḎḏḐḑḒḓḔḕḖḗḘḙḚḛḜḝḞḟḠḡḢḣḤḥḦḧḨḩḪḫ"
	to		+= "ooooooooyyaabbbbbbccddddddddddeeeeeeeeeeffgghhhhhhhhhh"
	mfrom	+= "ḬḭḮḯḰḱḲḳḴḵḶḷḸḹḺḻḼḽḾḿṀṁṂṃṄṅṆṇṈṉṊṋṌṍṎṏṐṑṒṓṔṕṖṗṘṙṚṛṜṝṞṟ"
	to		+= "iiiikkkkkkllllllllmmmmmmnnnnnnnnoooooooopppprrrrrrrr"
	mfrom	+= "ṠṡṢṣṤṥṦṧṨṩṪṫṬṭṮṯṰṱṲṳṴṵṶṷṸṹṺṻṼṽṾṿẀẁẂẃẄẅẆẇẈẉẊẋẌẍẎẏẐẑẒẓẔẕ"
	to		+= "ssssssssssttttttttuuuuuuuuuuvvvvwwwwwwwwwwxxxxxyzzzzzz"
	mfrom	+= "ẖẗẘẙẚẛẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊị"
	to		+= "htwyafaaaaaaaaaaaaaaaaaaaaaaaaeeeeeeeeeeeeeeeeiiii"
	mfrom	+= "ỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹ"
	to		+= "oooooooooooooooooooooooouuuuuuuuuuuuuuyyyyyyyy"
	for i in zip(mfrom, to):
		str = str.replace(*i)
	return str

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
