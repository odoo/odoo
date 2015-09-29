define(function(require, exports, module) {
module.exports = (function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);throw new Error("Cannot find module '"+o+"'")}var f=n[o]={exports:{}};t[o][0].call(f.exports,function(e){var n=t[o][1][e];return s(n?n:e)},f,f.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({
1:[function(_dereq_,module,exports){
function isScopeMarker(node) {
	if (node.namespaceURI === "http://www.w3.org/1999/xhtml") {
		return node.localName === "applet"
			|| node.localName === "caption"
			|| node.localName === "marquee"
			|| node.localName === "object"
			|| node.localName === "table"
			|| node.localName === "td"
			|| node.localName === "th";
	}
	if (node.namespaceURI === "http://www.w3.org/1998/Math/MathML") {
		return node.localName === "mi"
			|| node.localName === "mo"
			|| node.localName === "mn"
			|| node.localName === "ms"
			|| node.localName === "mtext"
			|| node.localName === "annotation-xml";
	}
	if (node.namespaceURI === "http://www.w3.org/2000/svg") {
		return node.localName === "foreignObject"
			|| node.localName === "desc"
			|| node.localName === "title";
	}
}

function isListItemScopeMarker(node) {
	return isScopeMarker(node)
		|| (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'ol')
		|| (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'ul');
}

function isTableScopeMarker(node) {
	return (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'table')
		|| (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'html');
}

function isTableBodyScopeMarker(node) {
	return (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'tbody')
		|| (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'tfoot')
		|| (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'thead')
		|| (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'html');
}

function isTableRowScopeMarker(node) {
	return (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'tr')
		|| (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'html');
}

function isButtonScopeMarker(node) {
	return isScopeMarker(node)
		|| (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'button');
}

function isSelectScopeMarker(node) {
	return !(node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'optgroup')
		&& !(node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.localName === 'option');
}

/**
 * Represents a stack of open elements
 * @constructor
 */
function ElementStack() {
	this.elements = [];
	this.rootNode = null;
	this.headElement = null;
	this.bodyElement = null;
}

/**
 *
 * @param {String} localName
 * @param {Function} isMarker
 * @return {Boolean}
 * @private
 */
ElementStack.prototype._inScope = function(localName, isMarker) {
	for (var i = this.elements.length - 1; i >= 0; i--) {
		var node = this.elements[i];
		if (node.localName === localName)
			return true;
		if (isMarker(node))
			return false;
	}
};

/**
 * Pushes the item on the stack top
 * @param {StackItem} item
 */
ElementStack.prototype.push = function(item) {
	this.elements.push(item);
};

/**
 * Pushes the item on the stack top
 * @param {StackItem} item HTML element stack item
 */
ElementStack.prototype.pushHtmlElement = function(item) {
	this.rootNode = item.node;
	this.push(item);
};

/**
 * Pushes the item on the stack top
 * @param {StackItem} item HEAD element stack item
 */
ElementStack.prototype.pushHeadElement = function(item) {
	this.headElement = item.node;
	this.push(item);
};

/**
 * Pushes the item on the stack top
 * @param {StackItem} item BODY element stack item
 */
ElementStack.prototype.pushBodyElement = function(item) {
	this.bodyElement = item.node;
	this.push(item);
};

/**
 * Pops the topmost item
 * @return {StackItem}
 */
ElementStack.prototype.pop = function() {
	return this.elements.pop();
};

/**
 * Removes the item from the element stack
 * @param {StackItem} item The item to remove
 */
ElementStack.prototype.remove = function(item) {
	this.elements.splice(this.elements.indexOf(item), 1);
};

/**
 * Pops until an element with a given localName is popped
 * @param {String} localName
 */
ElementStack.prototype.popUntilPopped = function(localName) {
	var element;
	do {
		element = this.pop();
	} while (element.localName != localName);
};

ElementStack.prototype.popUntilTableScopeMarker = function() {
	while (!isTableScopeMarker(this.top))
		this.pop();
};

ElementStack.prototype.popUntilTableBodyScopeMarker = function() {
	while (!isTableBodyScopeMarker(this.top))
		this.pop();
};

ElementStack.prototype.popUntilTableRowScopeMarker = function() {
	while (!isTableRowScopeMarker(this.top))
		this.pop();
};

/**
 *
 * @param {Number} index
 * @return {StackItem}
 */
ElementStack.prototype.item = function(index) {
	return this.elements[index];
};

/**
 *
 * @param {StackItem} element
 * @return {Boolean}
 */
ElementStack.prototype.contains = function(element) {
	return this.elements.indexOf(element) !== -1;
};

/**
 *
 * @param {String} localName
 * @return {Boolean}
 */
ElementStack.prototype.inScope = function(localName) {
	return this._inScope(localName, isScopeMarker);
};

/**
 *
 * @param {String} localName
 * @return {Boolean}
 */
ElementStack.prototype.inListItemScope = function(localName) {
	return this._inScope(localName, isListItemScopeMarker);
};

/**
 *
 * @param {String} localName
 * @return {Boolean}
 */
ElementStack.prototype.inTableScope = function(localName) {
	return this._inScope(localName, isTableScopeMarker);
};

/**
 *
 * @param {String} localName
 * @return {Boolean}
 */
ElementStack.prototype.inButtonScope = function(localName) {
	return this._inScope(localName, isButtonScopeMarker);
};

/**
 *
 * @param {String} localName
 * @return {Boolean}
 */
ElementStack.prototype.inSelectScope = function(localName) {
	return this._inScope(localName, isSelectScopeMarker);
};

/**
 *
 * @return {Boolean}
 */
ElementStack.prototype.hasNumberedHeaderElementInScope = function() {
	for (var i = this.elements.length - 1; i >= 0; i--) {
		var node = this.elements[i];
		if (node.isNumberedHeader())
			return true;
		if (isScopeMarker(node))
			return false;
	}
};

/**
 *
 * @param {Object} element
 * @return {StackItem}
 */
ElementStack.prototype.furthestBlockForFormattingElement = function(element) {
	var furthestBlock = null;
	for (var i = this.elements.length - 1; i >= 0; i--) {
		var node = this.elements[i];
		if (node.node === element)
			break;
		if (node.isSpecial())
			furthestBlock = node;
	}
    return furthestBlock;
};

/**
 *
 * @param {String} localName
 * @return {Number}
 */
ElementStack.prototype.findIndex = function(localName) {
	for (var i = this.elements.length - 1; i >= 0; i--) {
		if (this.elements[i].localName == localName)
			return i;
	}
    return -1;
};

ElementStack.prototype.remove_openElements_until = function(callback) {
	var finished = false;
	var element;
	while (!finished) {
		element = this.elements.pop();
		finished = callback(element);
	}
	return element;
};

Object.defineProperty(ElementStack.prototype, 'top', {
	get: function() {
		return this.elements[this.elements.length - 1];
	}
});

Object.defineProperty(ElementStack.prototype, 'length', {
	get: function() {
		return this.elements.length;
	}
});

exports.ElementStack = ElementStack;

},
{}],
2:[function(_dereq_,module,exports){
var entities  = _dereq_('html5-entities');
var InputStream = _dereq_('./InputStream').InputStream;

var namedEntityPrefixes = {};
Object.keys(entities).forEach(function (entityKey) {
	for (var i = 0; i < entityKey.length; i++) {
		namedEntityPrefixes[entityKey.substring(0, i + 1)] = true;
	}
});

function isAlphaNumeric(c) {
	return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

function isHexDigit(c) {
	return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
}

function isDecimalDigit(c) {
	return (c >= '0' && c <= '9');
}

var EntityParser = {};

EntityParser.consumeEntity = function(buffer, tokenizer, additionalAllowedCharacter) {
	var decodedCharacter = '';
	var consumedCharacters = '';
	var ch = buffer.char();
	if (ch === InputStream.EOF)
		return false;
	consumedCharacters += ch;
	if (ch == '\t' || ch == '\n' || ch == '\v' || ch == ' ' || ch == '<' || ch == '&') {
		buffer.unget(consumedCharacters);
		return false;
	}
	if (additionalAllowedCharacter === ch) {
		buffer.unget(consumedCharacters);
		return false;
	}
	if (ch == '#') {
		ch = buffer.shift(1);
		if (ch === InputStream.EOF) {
			tokenizer._parseError("expected-numeric-entity-but-got-eof");
			buffer.unget(consumedCharacters);
			return false;
		}
		consumedCharacters += ch;
		var radix = 10;
		var isDigit = isDecimalDigit;
		if (ch == 'x' || ch == 'X') {
			radix = 16;
			isDigit = isHexDigit;
			ch = buffer.shift(1);
			if (ch === InputStream.EOF) {
				tokenizer._parseError("expected-numeric-entity-but-got-eof");
				buffer.unget(consumedCharacters);
				return false;
			}
			consumedCharacters += ch;
		}
		if (isDigit(ch)) {
			var code = '';
			while (ch !== InputStream.EOF && isDigit(ch)) {
				code += ch;
				ch = buffer.char();
			}
			code = parseInt(code, radix);
			var replacement = this.replaceEntityNumbers(code);
			if (replacement) {
				tokenizer._parseError("invalid-numeric-entity-replaced");
				code = replacement;
			}
			if (code > 0xFFFF && code <= 0x10FFFF) {
		        // we substract 0x10000 from cp to get a 20-bits number
		        // in the range 0..0xFFFF
		        code -= 0x10000;
		        // we add 0xD800 to the number formed by the first 10 bits
		        // to give the first byte
		        var first = ((0xffc00 & code) >> 10) + 0xD800;
		        // we add 0xDC00 to the number formed by the low 10 bits
		        // to give the second byte
		        var second = (0x3ff & code) + 0xDC00;
				decodedCharacter = String.fromCharCode(first, second);
			} else
				decodedCharacter = String.fromCharCode(code);
			if (ch !== ';') {
				tokenizer._parseError("numeric-entity-without-semicolon");
				buffer.unget(ch);
			}
			return decodedCharacter;
		}
		buffer.unget(consumedCharacters);
		tokenizer._parseError("expected-numeric-entity");
		return false;
	}
	if ((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z')) {
		var mostRecentMatch = '';
		while (namedEntityPrefixes[consumedCharacters]) {
			if (entities[consumedCharacters]) {
				mostRecentMatch = consumedCharacters;
			}
			if (ch == ';')
				break;
			ch = buffer.char();
			if (ch === InputStream.EOF)
				break;
			consumedCharacters += ch;
		}
		if (!mostRecentMatch) {
			tokenizer._parseError("expected-named-entity");
			buffer.unget(consumedCharacters);
			return false;
		}
		decodedCharacter = entities[mostRecentMatch];
		if (ch === ';' || !additionalAllowedCharacter || !(isAlphaNumeric(ch) || ch === '=')) {
			if (consumedCharacters.length > mostRecentMatch.length) {
				buffer.unget(consumedCharacters.substring(mostRecentMatch.length));
			}
			if (ch !== ';') {
				tokenizer._parseError("named-entity-without-semicolon");
			}
			return decodedCharacter;
		}
		buffer.unget(consumedCharacters);
		return false;
	}
};

EntityParser.replaceEntityNumbers = function(c) {
	switch(c) {
		case 0x00: return 0xFFFD; // REPLACEMENT CHARACTER
		case 0x13: return 0x0010; // Carriage return
		case 0x80: return 0x20AC; // EURO SIGN
		case 0x81: return 0x0081; // <control>
		case 0x82: return 0x201A; // SINGLE LOW-9 QUOTATION MARK
		case 0x83: return 0x0192; // LATIN SMALL LETTER F WITH HOOK
		case 0x84: return 0x201E; // DOUBLE LOW-9 QUOTATION MARK
		case 0x85: return 0x2026; // HORIZONTAL ELLIPSIS
		case 0x86: return 0x2020; // DAGGER
		case 0x87: return 0x2021; // DOUBLE DAGGER
		case 0x88: return 0x02C6; // MODIFIER LETTER CIRCUMFLEX ACCENT
		case 0x89: return 0x2030; // PER MILLE SIGN
		case 0x8A: return 0x0160; // LATIN CAPITAL LETTER S WITH CARON
		case 0x8B: return 0x2039; // SINGLE LEFT-POINTING ANGLE QUOTATION MARK
		case 0x8C: return 0x0152; // LATIN CAPITAL LIGATURE OE
		case 0x8D: return 0x008D; // <control>
		case 0x8E: return 0x017D; // LATIN CAPITAL LETTER Z WITH CARON
		case 0x8F: return 0x008F; // <control>
		case 0x90: return 0x0090; // <control>
		case 0x91: return 0x2018; // LEFT SINGLE QUOTATION MARK
		case 0x92: return 0x2019; // RIGHT SINGLE QUOTATION MARK
		case 0x93: return 0x201C; // LEFT DOUBLE QUOTATION MARK
		case 0x94: return 0x201D; // RIGHT DOUBLE QUOTATION MARK
		case 0x95: return 0x2022; // BULLET
		case 0x96: return 0x2013; // EN DASH
		case 0x97: return 0x2014; // EM DASH
		case 0x98: return 0x02DC; // SMALL TILDE
		case 0x99: return 0x2122; // TRADE MARK SIGN
		case 0x9A: return 0x0161; // LATIN SMALL LETTER S WITH CARON
		case 0x9B: return 0x203A; // SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
		case 0x9C: return 0x0153; // LATIN SMALL LIGATURE OE
		case 0x9D: return 0x009D; // <control>
		case 0x9E: return 0x017E; // LATIN SMALL LETTER Z WITH CARON
		case 0x9F: return 0x0178; // LATIN CAPITAL LETTER Y WITH DIAERESIS
		default:
			if ((c >= 0xD800 && c <= 0xDFFF) || c > 0x10FFFF) {
				return 0xFFFD;
			} else if ((c >= 0x0001 && c <= 0x0008) || (c >= 0x000E && c <= 0x001F) ||
				(c >= 0x007F && c <= 0x009F) || (c >= 0xFDD0 && c <= 0xFDEF) ||
				c == 0x000B || c == 0xFFFE || c == 0x1FFFE || c == 0x2FFFFE ||
				c == 0x2FFFF || c == 0x3FFFE || c == 0x3FFFF || c == 0x4FFFE ||
				c == 0x4FFFF || c == 0x5FFFE || c == 0x5FFFF || c == 0x6FFFE ||
				c == 0x6FFFF || c == 0x7FFFE || c == 0x7FFFF || c == 0x8FFFE ||
				c == 0x8FFFF || c == 0x9FFFE || c == 0x9FFFF || c == 0xAFFFE ||
				c == 0xAFFFF || c == 0xBFFFE || c == 0xBFFFF || c == 0xCFFFE ||
				c == 0xCFFFF || c == 0xDFFFE || c == 0xDFFFF || c == 0xEFFFE ||
				c == 0xEFFFF || c == 0xFFFFE || c == 0xFFFFF || c == 0x10FFFE ||
				c == 0x10FFFF) {
				return c;
			}
	}
};

exports.EntityParser = EntityParser;

},
{"./InputStream":3,"html5-entities":12}],
3:[function(_dereq_,module,exports){
// FIXME convert CR to LF http://www.whatwg.org/specs/web-apps/current-work/multipage/parsing.html#input-stream
function InputStream() {
	this.data = '';
	this.start = 0;
	this.committed = 0;
	this.eof = false;
	this.lastLocation = {line: 0, column: 0};
}

InputStream.EOF = -1;

InputStream.DRAIN = -2;

InputStream.prototype = {
	slice: function() {
		if(this.start >= this.data.length) {
			if(!this.eof) throw InputStream.DRAIN;
			return InputStream.EOF;
		}
		return this.data.slice(this.start, this.data.length);
	},
	char: function() {
		if(!this.eof && this.start >= this.data.length - 1) throw InputStream.DRAIN;
		if(this.start >= this.data.length) {
			return InputStream.EOF;
		}
		var ch = this.data[this.start++];
		if (ch === '\r')
			ch = '\n';
		return ch;
	},
	advance: function(amount) {
		this.start += amount;
		if(this.start >= this.data.length) {
			if(!this.eof) throw InputStream.DRAIN;
			return InputStream.EOF;
		} else {
			if(this.committed > this.data.length / 2) {
				// Sliiiide
				this.lastLocation = this.location();
				this.data = this.data.slice(this.committed);
				this.start = this.start - this.committed;
				this.committed = 0;
			}
		}
	},
	matchWhile: function(re) {
		if(this.eof && this.start >= this.data.length ) return '';
		var r = new RegExp("^"+re+"+");
		var m = r.exec(this.slice());
		if(m) {
			if(!this.eof && m[0].length == this.data.length - this.start) throw InputStream.DRAIN;
			this.advance(m[0].length);
			return m[0];
		} else {
			return '';
		}
	},
	matchUntil: function(re) {
		var m, s;
		s = this.slice();
		if(s === InputStream.EOF) {
			return '';
		} else if(m = new RegExp(re + (this.eof ? "|$" : "")).exec(s)) {
			var t = this.data.slice(this.start, this.start + m.index);
			this.advance(m.index);
			return t.replace(/\r/g, '\n').replace(/\n{2,}/g, '\n');
		} else {
			throw InputStream.DRAIN;
		}
	},
	append: function(data) {
		this.data += data;
	},
	shift: function(n) {
		if(!this.eof && this.start + n >= this.data.length) throw InputStream.DRAIN;
		if(this.eof && this.start >= this.data.length) return InputStream.EOF;
		var d = this.data.slice(this.start, this.start + n).toString();
		this.advance(Math.min(n, this.data.length - this.start));
		return d;
	},
	peek: function(n) {
		if(!this.eof && this.start + n >= this.data.length) throw InputStream.DRAIN;
		if(this.eof && this.start >= this.data.length) return InputStream.EOF;
		return this.data.slice(this.start, Math.min(this.start + n, this.data.length)).toString();
	},
	length: function() {
		return this.data.length - this.start - 1;
	},
	unget: function(d) {
		if(d === InputStream.EOF) return;
		this.start -= (d.length);
	},
	undo: function() {
		this.start = this.committed;
	},
	commit: function() {
		this.committed = this.start;
	},
	location: function() {
		var lastLine = this.lastLocation.line;
		var lastColumn = this.lastLocation.column;
		var read = this.data.slice(0, this.committed);
		var newlines = read.match(/\n/g);
		var line = newlines ? lastLine + newlines.length : lastLine;
		var column = newlines ? read.length - read.lastIndexOf('\n') - 1 : lastColumn + read.length;
		return {line: line, column: column};
	}
};

exports.InputStream = InputStream;

},
{}],
4:[function(_dereq_,module,exports){
var SpecialElements = {
	"http://www.w3.org/1999/xhtml": [
		'address',
		'applet',
		'area',
		'article',
		'aside',
		'base',
		'basefont',
		'bgsound',
		'blockquote',
		'body',
		'br',
		'button',
		'caption',
		'center',
		'col',
		'colgroup',
		'dd',
		'details',
		'dir',
		'div',
		'dl',
		'dt',
		'embed',
		'fieldset',
		'figcaption',
		'figure',
		'footer',
		'form',
		'frame',
		'frameset',
		'h1',
		'h2',
		'h3',
		'h4',
		'h5',
		'h6',
		'head',
		'header',
		'hgroup',
		'hr',
		'html',
		'iframe',
		'img',
		'input',
		'isindex',
		'li',
		'link',
		'listing',
		'main',
		'marquee',
		'menu',
		'menuitem',
		'meta',
		'nav',
		'noembed',
		'noframes',
		'noscript',
		'object',
		'ol',
		'p',
		'param',
		'plaintext',
		'pre',
		'script',
		'section',
		'select',
		'source',
		'style',
		'summary',
		'table',
		'tbody',
		'td',
		'textarea',
		'tfoot',
		'th',
		'thead',
		'title',
		'tr',
		'track',
		'ul',
		'wbr',
		'xmp'
	],
	"http://www.w3.org/1998/Math/MathML": [
		'mi',
		'mo',
		'mn',
		'ms',
		'mtext',
		'annotation-xml'
	],
	"http://www.w3.org/2000/svg": [
		'foreignObject',
		'desc',
		'title'
	]
};


function StackItem(namespaceURI, localName, attributes, node) {
	this.localName = localName;
	this.namespaceURI = namespaceURI;
	this.attributes = attributes;
	this.node = node;
}

// http://www.whatwg.org/specs/web-apps/current-work/multipage/parsing.html#special
StackItem.prototype.isSpecial = function() {
	return this.namespaceURI in SpecialElements &&
		SpecialElements[this.namespaceURI].indexOf(this.localName) > -1;
};

StackItem.prototype.isFosterParenting = function() {
	if (this.namespaceURI === "http://www.w3.org/1999/xhtml") {
		return this.localName === 'table' ||
			this.localName === 'tbody' ||
			this.localName === 'tfoot' ||
			this.localName === 'thead' ||
			this.localName === 'tr';
	}
	return false;
};

StackItem.prototype.isNumberedHeader = function() {
	if (this.namespaceURI === "http://www.w3.org/1999/xhtml") {
		return this.localName === 'h1' ||
			this.localName === 'h2' ||
			this.localName === 'h3' ||
			this.localName === 'h4' ||
			this.localName === 'h5' ||
			this.localName === 'h6';
	}
	return false;
};

StackItem.prototype.isForeign = function() {
	return this.namespaceURI != "http://www.w3.org/1999/xhtml";
};

function getAttribute(item, name) {
	for (var i = 0; i < item.attributes.length; i++) {
		if (item.attributes[i].nodeName == name)
			return item.attributes[i].nodeValue;
	}
	return null;
}

StackItem.prototype.isHtmlIntegrationPoint = function() {
	if (this.namespaceURI === "http://www.w3.org/1998/Math/MathML") {
		if (this.localName !== "annotation-xml")
			return false;
		var encoding = getAttribute(this, 'encoding');
		if (!encoding)
			return false;
		encoding = encoding.toLowerCase();
		return encoding === "text/html" || encoding === "application/xhtml+xml";
	}
	if (this.namespaceURI === "http://www.w3.org/2000/svg") {
		return this.localName === "foreignObject"
			|| this.localName === "desc"
			|| this.localName === "title";
	}
	return false;
};

StackItem.prototype.isMathMLTextIntegrationPoint = function() {
	if (this.namespaceURI === "http://www.w3.org/1998/Math/MathML") {
		return this.localName === "mi"
			|| this.localName === "mo"
			|| this.localName === "mn"
			|| this.localName === "ms"
			|| this.localName === "mtext";
	}
	return false;
};

exports.StackItem = StackItem;

},
{}],
5:[function(_dereq_,module,exports){
var InputStream = _dereq_('./InputStream').InputStream;
var EntityParser = _dereq_('./EntityParser').EntityParser;

function isWhitespace(c){
	return c === " " || c === "\n" || c === "\t" || c === "\r" || c === "\f";
}

function isAlpha(c) {
	return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
}

/**
 *
 * @param {Object} tokenHandler
 * @constructor
 */
function Tokenizer(tokenHandler) {
	this._tokenHandler = tokenHandler;
	this._state = Tokenizer.DATA;
	this._inputStream = new InputStream();
	this._currentToken = null;
	this._temporaryBuffer = '';
	this._additionalAllowedCharacter = '';
}

Tokenizer.prototype._parseError = function(code, args) {
	this._tokenHandler.parseError(code, args);
};

Tokenizer.prototype._emitToken = function(token) {
	if (token.type === 'StartTag') {
		for (var i = 1; i < token.data.length; i++) {
			if (!token.data[i].nodeName)
				token.data.splice(i--, 1);
		}
	} else if (token.type === 'EndTag') {
		if (token.selfClosing) {
			this._parseError('self-closing-flag-on-end-tag');
		}
		if (token.data.length !== 0) {
			this._parseError('attributes-in-end-tag');
		}
	}
	this._tokenHandler.processToken(token);
	if (token.type === 'StartTag' && token.selfClosing && !this._tokenHandler.isSelfClosingFlagAcknowledged()) {
		this._parseError('non-void-element-with-trailing-solidus', {name: token.name});
	}
};

Tokenizer.prototype._emitCurrentToken = function() {
	this._state = Tokenizer.DATA;
	this._emitToken(this._currentToken);
};

Tokenizer.prototype._currentAttribute = function() {
	return this._currentToken.data[this._currentToken.data.length - 1];
};

Tokenizer.prototype.setState = function(state) {
	this._state = state;
};

Tokenizer.prototype.tokenize = function(source) {
	// FIXME proper tokenizer states
	Tokenizer.DATA = data_state;
	Tokenizer.RCDATA = rcdata_state;
	Tokenizer.RAWTEXT = rawtext_state;
	Tokenizer.SCRIPT_DATA = script_data_state;
	Tokenizer.PLAINTEXT = plaintext_state;


	this._state = Tokenizer.DATA;

	this._inputStream.append(source);

	this._tokenHandler.startTokenization(this);

	this._inputStream.eof = true;

	var tokenizer = this;

	while (this._state.call(this, this._inputStream));


	function data_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._emitToken({type: 'EOF', data: null});
			return false;
		} else if (data === '&') {
			tokenizer.setState(character_reference_in_data_state);
		} else if (data === '<') {
			tokenizer.setState(tag_open_state);
		} else if (data === '\u0000') {
			tokenizer._emitToken({type: 'Characters', data: data});
			buffer.commit();
		} else {
			var chars = buffer.matchUntil("&|<|\u0000");
			tokenizer._emitToken({type: 'Characters', data: data + chars});
			buffer.commit();
		}
		return true;
	}

	function character_reference_in_data_state(buffer) {
		var character = EntityParser.consumeEntity(buffer, tokenizer);
		tokenizer.setState(data_state);
		tokenizer._emitToken({type: 'Characters', data: character || '&'});
		return true;
	}

	function rcdata_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._emitToken({type: 'EOF', data: null});
			return false;
		} else if (data === '&') {
			tokenizer.setState(character_reference_in_rcdata_state);
		} else if (data === '<') {
			tokenizer.setState(rcdata_less_than_sign_state);
		} else if (data === "\u0000") {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._emitToken({type: 'Characters', data: '\uFFFD'});
			buffer.commit();
		} else {
			var chars = buffer.matchUntil("&|<|\u0000");
			tokenizer._emitToken({type: 'Characters', data: data + chars});
			buffer.commit();
		}
		return true;
	}

	function character_reference_in_rcdata_state(buffer) {
		var character = EntityParser.consumeEntity(buffer, tokenizer);
		tokenizer.setState(rcdata_state);
		tokenizer._emitToken({type: 'Characters', data: character || '&'});
		return true;
	}

	function rawtext_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._emitToken({type: 'EOF', data: null});
			return false;
		} else if (data === '<') {
			tokenizer.setState(rawtext_less_than_sign_state);
		} else if (data === "\u0000") {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._emitToken({type: 'Characters', data: '\uFFFD'});
			buffer.commit();
		} else {
			var chars = buffer.matchUntil("<|\u0000");
			tokenizer._emitToken({type: 'Characters', data: data + chars});
		}
		return true;
	}

	function plaintext_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._emitToken({type: 'EOF', data: null});
			return false;
		} else if (data === "\u0000") {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._emitToken({type: 'Characters', data: '\uFFFD'});
			buffer.commit();
		} else {
			var chars = buffer.matchUntil("\u0000");
			tokenizer._emitToken({type: 'Characters', data: data + chars});
		}
		return true;
	}


	function script_data_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._emitToken({type: 'EOF', data: null});
			return false;
		} else if (data === '<') {
			tokenizer.setState(script_data_less_than_sign_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._emitToken({type: 'Characters', data: '\uFFFD'});
			buffer.commit();
		} else {
			var chars = buffer.matchUntil("<|\u0000");
			tokenizer._emitToken({type: 'Characters', data: data + chars});
		}
		return true;
	}

	function rcdata_less_than_sign_state(buffer) {
		var data = buffer.char();
		if (data === "/") {
			this._temporaryBuffer = '';
			tokenizer.setState(rcdata_end_tag_open_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: '<'});
			buffer.unget(data);
			tokenizer.setState(rcdata_state);
		}
		return true;
	}

	function rcdata_end_tag_open_state(buffer) {
		var data = buffer.char();
		if (isAlpha(data)) {
			this._temporaryBuffer += data;
			tokenizer.setState(rcdata_end_tag_name_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: '</'});
			buffer.unget(data);
			tokenizer.setState(rcdata_state);
		}
		return true;
	}

	function rcdata_end_tag_name_state(buffer) {
		var appropriate = tokenizer._currentToken && (tokenizer._currentToken.name === this._temporaryBuffer.toLowerCase());
		var data = buffer.char();
		if (isWhitespace(data) && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: this._temporaryBuffer, data: [], selfClosing: false};
			tokenizer.setState(before_attribute_name_state);
		} else if (data === '/' && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: this._temporaryBuffer, data: [], selfClosing: false};
			tokenizer.setState(self_closing_tag_state);
		} else if (data === '>' && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: this._temporaryBuffer, data: [], selfClosing: false};
			tokenizer._emitCurrentToken();
			tokenizer.setState(data_state);
		} else if (isAlpha(data)) {
			this._temporaryBuffer += data;
			buffer.commit();
		} else {
			tokenizer._emitToken({type: 'Characters', data: '</' + this._temporaryBuffer});
			buffer.unget(data);
			tokenizer.setState(rcdata_state);
		}
		return true;
	}

	function rawtext_less_than_sign_state(buffer) {
		var data = buffer.char();
		if (data === "/") {
			this._temporaryBuffer = '';
			tokenizer.setState(rawtext_end_tag_open_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: '<'});
			buffer.unget(data);
			tokenizer.setState(rawtext_state);
		}
		return true;
	}

	function rawtext_end_tag_open_state(buffer) {
		var data = buffer.char();
		if (isAlpha(data)) {
			this._temporaryBuffer += data;
			tokenizer.setState(rawtext_end_tag_name_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: '</'});
			buffer.unget(data);
			tokenizer.setState(rawtext_state);
		}
		return true;
	}

	function rawtext_end_tag_name_state(buffer) {
		var appropriate = tokenizer._currentToken && (tokenizer._currentToken.name === this._temporaryBuffer.toLowerCase());
		var data = buffer.char();
		if (isWhitespace(data) && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: this._temporaryBuffer, data: [], selfClosing: false};
			tokenizer.setState(before_attribute_name_state);
		} else if (data === '/' && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: this._temporaryBuffer, data: [], selfClosing: false};
			tokenizer.setState(self_closing_tag_state);
		} else if (data === '>' && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: this._temporaryBuffer, data: [], selfClosing: false};
			tokenizer._emitCurrentToken();
			tokenizer.setState(data_state);
		} else if (isAlpha(data)) {
			this._temporaryBuffer += data;
			buffer.commit();
		} else {
			tokenizer._emitToken({type: 'Characters', data: '</' + this._temporaryBuffer});
			buffer.unget(data);
			tokenizer.setState(rawtext_state);
		}
		return true;
	}

	function script_data_less_than_sign_state(buffer) {
		var data = buffer.char();
		if (data === "/") {
			this._temporaryBuffer = '';
			tokenizer.setState(script_data_end_tag_open_state);
		} else if (data === '!') {
			tokenizer._emitToken({type: 'Characters', data: '<!'});
			tokenizer.setState(script_data_escape_start_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: '<'});
			buffer.unget(data);
			tokenizer.setState(script_data_state);
		}
		return true;
	}

	function script_data_end_tag_open_state(buffer) {
		var data = buffer.char();
		if (isAlpha(data)) {
			this._temporaryBuffer += data;
			tokenizer.setState(script_data_end_tag_name_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: '</'});
			buffer.unget(data);
			tokenizer.setState(script_data_state);
		}
		return true;
	}

	function script_data_end_tag_name_state(buffer) {
		var appropriate = tokenizer._currentToken && (tokenizer._currentToken.name === this._temporaryBuffer.toLowerCase());
		var data = buffer.char();
		if (isWhitespace(data) && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: 'script', data: [], selfClosing: false};
			tokenizer.setState(before_attribute_name_state);
		} else if (data === '/' && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: 'script', data: [], selfClosing: false};
			tokenizer.setState(self_closing_tag_state);
		} else if (data === '>' && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: 'script', data: [], selfClosing: false};
			tokenizer._emitCurrentToken();
		} else if (isAlpha(data)) {
			this._temporaryBuffer += data;
			buffer.commit();
		} else {
			tokenizer._emitToken({type: 'Characters', data: '</' + this._temporaryBuffer});
			buffer.unget(data);
			tokenizer.setState(script_data_state);
		}
		return true;
	}

	function script_data_escape_start_state(buffer) {
		var data = buffer.char();
		if (data === '-') {
			tokenizer._emitToken({type: 'Characters', data: '-'});
			tokenizer.setState(script_data_escape_start_dash_state);
		} else {
			buffer.unget(data);
			tokenizer.setState(script_data_state);
		}
		return true;
	}

	function script_data_escape_start_dash_state(buffer) {
		var data = buffer.char();
		if (data === '-') {
			tokenizer._emitToken({type: 'Characters', data: '-'});
			tokenizer.setState(script_data_escaped_dash_dash_state);
		} else {
			buffer.unget(data);
			tokenizer.setState(script_data_state);
		}
		return true;
	}

	function script_data_escaped_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '-') {
			tokenizer._emitToken({type: 'Characters', data: '-'});
			tokenizer.setState(script_data_escaped_dash_state);
		} else if (data === '<') {
			tokenizer.setState(script_data_escaped_less_then_sign_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._emitToken({type: 'Characters', data: '\uFFFD'});
			buffer.commit();
		} else {
			var chars = buffer.matchUntil('<|-|\u0000');
			tokenizer._emitToken({type: 'Characters', data: data + chars});
		}
		return true;
	}

	function script_data_escaped_dash_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '-') {
			tokenizer._emitToken({type: 'Characters', data: '-'});
			tokenizer.setState(script_data_escaped_dash_dash_state);
		} else if (data === '<') {
			tokenizer.setState(script_data_escaped_less_then_sign_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._emitToken({type: 'Characters', data: '\uFFFD'});
			tokenizer.setState(script_data_escaped_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: data});
			tokenizer.setState(script_data_escaped_state);
		}
		return true;
	}

	function script_data_escaped_dash_dash_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError('eof-in-script');
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '<') {
			tokenizer.setState(script_data_escaped_less_then_sign_state);
		} else if (data === '>') {
			tokenizer._emitToken({type: 'Characters', data: '>'});
			tokenizer.setState(script_data_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._emitToken({type: 'Characters', data: '\uFFFD'});
			tokenizer.setState(script_data_escaped_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: data});
			tokenizer.setState(script_data_escaped_state);
		}
		return true;
	}

	function script_data_escaped_less_then_sign_state(buffer) {
		var data = buffer.char();
		if (data === '/') {
			this._temporaryBuffer = '';
			tokenizer.setState(script_data_escaped_end_tag_open_state);
		} else if (isAlpha(data)) {
			tokenizer._emitToken({type: 'Characters', data: '<' + data});
			this._temporaryBuffer = data;
			tokenizer.setState(script_data_double_escape_start_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: '<'});
			buffer.unget(data);
			tokenizer.setState(script_data_escaped_state);
		}
		return true;
	}

	function script_data_escaped_end_tag_open_state(buffer) {
		var data = buffer.char();
		if (isAlpha(data)) {
			this._temporaryBuffer = data;
			tokenizer.setState(script_data_escaped_end_tag_name_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: '</'});
			buffer.unget(data);
			tokenizer.setState(script_data_escaped_state);
		}
		return true;
	}

	function script_data_escaped_end_tag_name_state(buffer) {
		var appropriate = tokenizer._currentToken && (tokenizer._currentToken.name === this._temporaryBuffer.toLowerCase());
		var data = buffer.char();
		if (isWhitespace(data) && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: 'script', data: [], selfClosing: false};
			tokenizer.setState(before_attribute_name_state);
		} else if (data === '/' && appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: 'script', data: [], selfClosing: false};
			tokenizer.setState(self_closing_tag_state);
		} else if (data === '>' &&  appropriate) {
			tokenizer._currentToken = {type: 'EndTag', name: 'script', data: [], selfClosing: false};
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (isAlpha(data)) {
			this._temporaryBuffer += data;
			buffer.commit();
		} else {
			tokenizer._emitToken({type: 'Characters', data: '</' + this._temporaryBuffer});
			buffer.unget(data);
			tokenizer.setState(script_data_escaped_state);
		}
		return true;
	}

	function script_data_double_escape_start_state(buffer) {
		var data = buffer.char();
		if (isWhitespace(data) || data === '/' || data === '>') {
			tokenizer._emitToken({type: 'Characters', data: data});
			if (this._temporaryBuffer.toLowerCase() === 'script')
				tokenizer.setState(script_data_double_escaped_state);
			else
				tokenizer.setState(script_data_escaped_state);
		} else if (isAlpha(data)) {
			tokenizer._emitToken({type: 'Characters', data: data});
			this._temporaryBuffer += data;
			buffer.commit();
		} else {
			buffer.unget(data);
			tokenizer.setState(script_data_escaped_state);
		}
		return true;
	}

	function script_data_double_escaped_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError('eof-in-script');
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '-') {
			tokenizer._emitToken({type: 'Characters', data: '-'});
			tokenizer.setState(script_data_double_escaped_dash_state);
		} else if (data === '<') {
			tokenizer._emitToken({type: 'Characters', data: '<'});
			tokenizer.setState(script_data_double_escaped_less_than_sign_state);
		} else if (data === '\u0000') {
			tokenizer._parseError('invalid-codepoint');
			tokenizer._emitToken({type: 'Characters', data: '\uFFFD'});
			buffer.commit();
		} else {
			tokenizer._emitToken({type: 'Characters', data: data});
			buffer.commit();
		}
		return true;
	}

	function script_data_double_escaped_dash_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError('eof-in-script');
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '-') {
			tokenizer._emitToken({type: 'Characters', data: '-'});
			tokenizer.setState(script_data_double_escaped_dash_dash_state);
		} else if (data === '<') {
			tokenizer._emitToken({type: 'Characters', data: '<'});
			tokenizer.setState(script_data_double_escaped_less_than_sign_state);
		} else if (data === '\u0000') {
			tokenizer._parseError('invalid-codepoint');
			tokenizer._emitToken({type: 'Characters', data: '\uFFFD'});
			tokenizer.setState(script_data_double_escaped_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: data});
			tokenizer.setState(script_data_double_escaped_state);
		}
		return true;
	}

	function script_data_double_escaped_dash_dash_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError('eof-in-script');
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '-') {
			tokenizer._emitToken({type: 'Characters', data: '-'});
			buffer.commit();
		} else if (data === '<') {
			tokenizer._emitToken({type: 'Characters', data: '<'});
			tokenizer.setState(script_data_double_escaped_less_than_sign_state);
		} else if (data === '>') {
			tokenizer._emitToken({type: 'Characters', data: '>'});
			tokenizer.setState(script_data_state);
		} else if (data === '\u0000') {
			tokenizer._parseError('invalid-codepoint');
			tokenizer._emitToken({type: 'Characters', data: '\uFFFD'});
			tokenizer.setState(script_data_double_escaped_state);
		} else {
			tokenizer._emitToken({type: 'Characters', data: data});
			tokenizer.setState(script_data_double_escaped_state);
		}
		return true;
	}

	function script_data_double_escaped_less_than_sign_state(buffer) {
		var data = buffer.char();
		if (data === '/') {
			tokenizer._emitToken({type: 'Characters', data: '/'});
			this._temporaryBuffer = '';
			tokenizer.setState(script_data_double_escape_end_state);
		} else {
			buffer.unget(data);
			tokenizer.setState(script_data_double_escaped_state);
		}
		return true;
	}

	function script_data_double_escape_end_state(buffer) {
		var data = buffer.char();
		if (isWhitespace(data) || data === '/' || data === '>') {
			tokenizer._emitToken({type: 'Characters', data: data});
			if (this._temporaryBuffer.toLowerCase() === 'script')
				tokenizer.setState(script_data_escaped_state);
			else
				tokenizer.setState(script_data_double_escaped_state);
		} else if (isAlpha(data)) {
			tokenizer._emitToken({type: 'Characters', data: data});
			this._temporaryBuffer += data;
			buffer.commit();
		} else {
			buffer.unget(data);
			tokenizer.setState(script_data_double_escaped_state);
		}
		return true;
	}

	function tag_open_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("bare-less-than-sign-at-eof");
			tokenizer._emitToken({type: 'Characters', data: '<'});
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isAlpha(data)) {
			tokenizer._currentToken = {type: 'StartTag', name: data.toLowerCase(), data: []};
			tokenizer.setState(tag_name_state);
		} else if (data === '!') {
			tokenizer.setState(markup_declaration_open_state);
		} else if (data === '/') {
			tokenizer.setState(close_tag_open_state);
		} else if (data === '>') {
			// XXX In theory it could be something besides a tag name. But
			// do we really care?
			tokenizer._parseError("expected-tag-name-but-got-right-bracket");
			tokenizer._emitToken({type: 'Characters', data: "<>"});
			tokenizer.setState(data_state);
		} else if (data === '?') {
			// XXX In theory it could be something besides a tag name. But
			// do we really care?
			tokenizer._parseError("expected-tag-name-but-got-question-mark");
			buffer.unget(data);
			tokenizer.setState(bogus_comment_state);
		} else {
			// XXX
			tokenizer._parseError("expected-tag-name");
			tokenizer._emitToken({type: 'Characters', data: "<"});
			buffer.unget(data);
			tokenizer.setState(data_state);
		}
		return true;
	}

	function close_tag_open_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("expected-closing-tag-but-got-eof");
			tokenizer._emitToken({type: 'Characters', data: '</'});
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isAlpha(data)) {
			tokenizer._currentToken = {type: 'EndTag', name: data.toLowerCase(), data: []};
			tokenizer.setState(tag_name_state);
		} else if (data === '>') {
			tokenizer._parseError("expected-closing-tag-but-got-right-bracket");
			tokenizer.setState(data_state);
		} else {
			tokenizer._parseError("expected-closing-tag-but-got-char", {data: data}); // param 1 is datavars:
			buffer.unget(data);
			tokenizer.setState(bogus_comment_state);
		}
		return true;
	}

	function tag_name_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError('eof-in-tag-name');
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			tokenizer.setState(before_attribute_name_state);
		} else if (isAlpha(data)) {
			tokenizer._currentToken.name += data.toLowerCase();
		} else if (data === '>') {
			tokenizer._emitCurrentToken();
		} else if (data === '/') {
			tokenizer.setState(self_closing_tag_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentToken.name += "\uFFFD";
		} else {
			tokenizer._currentToken.name += data;
		}
		buffer.commit();

		return true;
	}

	function before_attribute_name_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("expected-attribute-name-but-got-eof");
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			return true;
		} else if (isAlpha(data)) {
			tokenizer._currentToken.data.push({nodeName: data.toLowerCase(), nodeValue: ""});
			tokenizer.setState(attribute_name_state);
		} else if (data === '>') {
			tokenizer._emitCurrentToken();
		} else if (data === '/') {
			tokenizer.setState(self_closing_tag_state);
		} else if (data === "'" || data === '"' || data === '=' || data === '<') {
			tokenizer._parseError("invalid-character-in-attribute-name");
			tokenizer._currentToken.data.push({nodeName: data, nodeValue: ""});
			tokenizer.setState(attribute_name_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentToken.data.push({nodeName: "\uFFFD", nodeValue: ""});
		} else {
			tokenizer._currentToken.data.push({nodeName: data, nodeValue: ""});
			tokenizer.setState(attribute_name_state);
		}
		return true;
	}

	function attribute_name_state(buffer) {
		var data = buffer.char();
		var leavingThisState = true;
		var shouldEmit = false;
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-attribute-name");
			buffer.unget(data);
			tokenizer.setState(data_state);
			shouldEmit = true;
		} else if (data === '=') {
			tokenizer.setState(before_attribute_value_state);
		} else if (isAlpha(data)) {
			tokenizer._currentAttribute().nodeName += data.toLowerCase();
			leavingThisState = false;
		} else if (data === '>') {
			// XXX If we emit here the attributes are converted to a dict
			// without being checked and when the code below runs we error
			// because data is a dict not a list
			shouldEmit = true;
		} else if (isWhitespace(data)) {
			tokenizer.setState(after_attribute_name_state);
		} else if (data === '/') {
			tokenizer.setState(self_closing_tag_state);
		} else if (data === "'" || data === '"') {
			tokenizer._parseError("invalid-character-in-attribute-name");
			tokenizer._currentAttribute().nodeName += data;
			leavingThisState = false;
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentAttribute().nodeName += "\uFFFD";
		} else {
			tokenizer._currentAttribute().nodeName += data;
			leavingThisState = false;
		}

		if (leavingThisState) {
			// Attributes are not dropped at this stage. That happens when the
			// start tag token is emitted so values can still be safely appended
			// to attributes, but we do want to report the parse error in time.
			var attributes = tokenizer._currentToken.data;
			var currentAttribute = attributes[attributes.length - 1];
			for (var i = attributes.length - 2; i >= 0; i--) {
				if (currentAttribute.nodeName === attributes[i].nodeName) {
					tokenizer._parseError("duplicate-attribute", {name: currentAttribute.nodeName});
					currentAttribute.nodeName = null;
					break;
				}
			}
			if (shouldEmit)
				tokenizer._emitCurrentToken();
		} else {
			buffer.commit();
		}
		return true;
	}

	function after_attribute_name_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("expected-end-of-tag-but-got-eof");
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			return true;
		} else if (data === '=') {
			tokenizer.setState(before_attribute_value_state);
		} else if (data === '>') {
			tokenizer._emitCurrentToken();
		} else if (isAlpha(data)) {
			tokenizer._currentToken.data.push({nodeName: data, nodeValue: ""});
			tokenizer.setState(attribute_name_state);
		} else if (data === '/') {
			tokenizer.setState(self_closing_tag_state);
		} else if (data === "'" || data === '"' || data === '<') {
			tokenizer._parseError("invalid-character-after-attribute-name");
			tokenizer._currentToken.data.push({nodeName: data, nodeValue: ""});
			tokenizer.setState(attribute_name_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentToken.data.push({nodeName: "\uFFFD", nodeValue: ""});
		} else {
			tokenizer._currentToken.data.push({nodeName: data, nodeValue: ""});
			tokenizer.setState(attribute_name_state);
		}
		return true;
	}

	function before_attribute_value_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("expected-attribute-value-but-got-eof");
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			return true;
		} else if (data === '"') {
			tokenizer.setState(attribute_value_double_quoted_state);
		} else if (data === '&') {
			tokenizer.setState(attribute_value_unquoted_state);
			buffer.unget(data);
		} else if (data === "'") {
			tokenizer.setState(attribute_value_single_quoted_state);
		} else if (data === '>') {
			tokenizer._parseError("expected-attribute-value-but-got-right-bracket");
			tokenizer._emitCurrentToken();
		} else if (data === '=' || data === '<' || data === '`') {
			tokenizer._parseError("unexpected-character-in-unquoted-attribute-value");
			tokenizer._currentAttribute().nodeValue += data;
			tokenizer.setState(attribute_value_unquoted_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentAttribute().nodeValue += "\uFFFD";
		} else {
			tokenizer._currentAttribute().nodeValue += data;
			tokenizer.setState(attribute_value_unquoted_state);
		}

		return true;
	}

	function attribute_value_double_quoted_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-attribute-value-double-quote");
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '"') {
			tokenizer.setState(after_attribute_value_state);
		} else if (data === '&') {
			this._additionalAllowedCharacter = '"';
			tokenizer.setState(character_reference_in_attribute_value_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentAttribute().nodeValue += "\uFFFD";
		} else {
			var s = buffer.matchUntil('[\0"&]');
			data = data + s;
			tokenizer._currentAttribute().nodeValue += data;
		}
		return true;
	}

	function attribute_value_single_quoted_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-attribute-value-single-quote");
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === "'") {
			tokenizer.setState(after_attribute_value_state);
		} else if (data === '&') {
			this._additionalAllowedCharacter = "'";
			tokenizer.setState(character_reference_in_attribute_value_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentAttribute().nodeValue += "\uFFFD";
		} else {
			tokenizer._currentAttribute().nodeValue += data + buffer.matchUntil("\u0000|['&]");
		}
		return true;
	}

	function attribute_value_unquoted_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-after-attribute-value");
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			tokenizer.setState(before_attribute_name_state);
		} else if (data === '&') {
			this._additionalAllowedCharacter = ">";
			tokenizer.setState(character_reference_in_attribute_value_state);
		} else if (data === '>') {
			tokenizer._emitCurrentToken();
		} else if (data === '"' || data === "'" || data === '=' || data === '`' || data === '<') {
			tokenizer._parseError("unexpected-character-in-unquoted-attribute-value");
			tokenizer._currentAttribute().nodeValue += data;
			buffer.commit();
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentAttribute().nodeValue += "\uFFFD";
		} else {
			var o = buffer.matchUntil("\u0000|["+ "\t\n\v\f\x20\r" + "&<>\"'=`" +"]");
			if (o === InputStream.EOF) {
				tokenizer._parseError("eof-in-attribute-value-no-quotes");
				tokenizer._emitCurrentToken();
			}
			// Commit here since this state is re-enterable and its outcome won't change with more data.
			buffer.commit();
			tokenizer._currentAttribute().nodeValue += data + o;
		}
		return true;
	}

	function character_reference_in_attribute_value_state(buffer) {
		var character = EntityParser.consumeEntity(buffer, tokenizer, this._additionalAllowedCharacter);
		this._currentAttribute().nodeValue += character || '&';
		// We're supposed to switch back to the attribute value state that
		// we were in when we were switched into this state. Rather than
		// keeping track of this explictly, we observe that the previous
		// state can be determined by additionalAllowedCharacter.
		if (this._additionalAllowedCharacter === '"')
			tokenizer.setState(attribute_value_double_quoted_state);
		else if (this._additionalAllowedCharacter === '\'')
			tokenizer.setState(attribute_value_single_quoted_state);
		else if (this._additionalAllowedCharacter === '>')
			tokenizer.setState(attribute_value_unquoted_state);
		return true;
	}

	function after_attribute_value_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-after-attribute-value");
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			tokenizer.setState(before_attribute_name_state);
		} else if (data === '>') {
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (data === '/') {
			tokenizer.setState(self_closing_tag_state);
		} else {
			tokenizer._parseError("unexpected-character-after-attribute-value");
			buffer.unget(data);
			tokenizer.setState(before_attribute_name_state);
		}
		return true;
	}

	function self_closing_tag_state(buffer) {
		var c = buffer.char();
		if (c === InputStream.EOF) {
			tokenizer._parseError("unexpected-eof-after-solidus-in-tag");
			buffer.unget(c);
			tokenizer.setState(data_state);
		} else if (c === '>') {
			tokenizer._currentToken.selfClosing = true;
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else {
			tokenizer._parseError("unexpected-character-after-solidus-in-tag");
			buffer.unget(c);
			tokenizer.setState(before_attribute_name_state);
		}
		return true;
	}

	function bogus_comment_state(buffer) {
		var data = buffer.matchUntil('>');
		data = data.replace(/\u0000/g, "\uFFFD");
		buffer.char();
		tokenizer._emitToken({type: 'Comment', data: data});
		tokenizer.setState(data_state);
		return true;
	}

	function markup_declaration_open_state(buffer) {
		var chars = buffer.shift(2);
		if (chars === '--') {
			tokenizer._currentToken = {type: 'Comment', data: ''};
			tokenizer.setState(comment_start_state);
		} else {
			var newchars = buffer.shift(5);
			if (newchars === InputStream.EOF || chars === InputStream.EOF) {
				tokenizer._parseError("expected-dashes-or-doctype");
				tokenizer.setState(bogus_comment_state);
				buffer.unget(chars);
				return true;
			}

			chars += newchars;
			if (chars.toUpperCase() === 'DOCTYPE') {
				tokenizer._currentToken = {type: 'Doctype', name: '', publicId: null, systemId: null, forceQuirks: false};
				tokenizer.setState(doctype_state);
			} else if (tokenizer._tokenHandler.isCdataSectionAllowed() && chars === '[CDATA[') {
				tokenizer.setState(cdata_section_state);
			} else {
				tokenizer._parseError("expected-dashes-or-doctype");
				buffer.unget(chars);
				tokenizer.setState(bogus_comment_state);
			}
		}
		return true;
	}

	function cdata_section_state(buffer) {
		var data = buffer.matchUntil(']]>');
		// skip ]]>
		buffer.shift(3);
		if (data) {
			tokenizer._emitToken({type: 'Characters', data: data});
		}
		tokenizer.setState(data_state);
		return true;
	}

	function comment_start_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-comment");
			tokenizer._emitToken(tokenizer._currentToken);
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '-') {
			tokenizer.setState(comment_start_dash_state);
		} else if (data === '>') {
			tokenizer._parseError("incorrect-comment");
			tokenizer._emitToken(tokenizer._currentToken);
			tokenizer.setState(data_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentToken.data += "\uFFFD";
		} else {
			tokenizer._currentToken.data += data;
			tokenizer.setState(comment_state);
		}
		return true;
	}

	function comment_start_dash_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-comment");
			tokenizer._emitToken(tokenizer._currentToken);
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '-') {
			tokenizer.setState(comment_end_state);
		} else if (data === '>') {
			tokenizer._parseError("incorrect-comment");
			tokenizer._emitToken(tokenizer._currentToken);
			tokenizer.setState(data_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentToken.data += "\uFFFD";
		} else {
			tokenizer._currentToken.data += '-' + data;
			tokenizer.setState(comment_state);
		}
		return true;
	}

	function comment_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-comment");
			tokenizer._emitToken(tokenizer._currentToken);
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '-') {
			tokenizer.setState(comment_end_dash_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentToken.data += "\uFFFD";
		} else {
			tokenizer._currentToken.data += data;
			buffer.commit();
		}
		return true;
	}

	function comment_end_dash_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-comment-end-dash");
			tokenizer._emitToken(tokenizer._currentToken);
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '-') {
			tokenizer.setState(comment_end_state);
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentToken.data += "-\uFFFD";
			tokenizer.setState(comment_state);
		} else {
			tokenizer._currentToken.data += '-' + data + buffer.matchUntil('\u0000|-');
			// Consume the next character which is either a "-" or an :EOF as
			// well so if there's a "-" directly after the "-" we go nicely to
			// the "comment end state" without emitting a tokenizer._parseError there.
			buffer.char();
		}
		return true;
	}

	function comment_end_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-comment-double-dash");
			tokenizer._emitToken(tokenizer._currentToken);
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '>') {
			tokenizer._emitToken(tokenizer._currentToken);
			tokenizer.setState(data_state);
		} else if (data === '!') {
			tokenizer._parseError("unexpected-bang-after-double-dash-in-comment");
			tokenizer.setState(comment_end_bang_state);
		} else if (data === '-') {
			tokenizer._parseError("unexpected-dash-after-double-dash-in-comment");
			tokenizer._currentToken.data += data;
		} else if (data === '\u0000') {
			tokenizer._parseError("invalid-codepoint");
			tokenizer._currentToken.data += "--\uFFFD";
			tokenizer.setState(comment_state);
		} else {
			// XXX
			tokenizer._parseError("unexpected-char-in-comment");
			tokenizer._currentToken.data += '--' + data;
			tokenizer.setState(comment_state);
		}
		return true;
	}

	function comment_end_bang_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-comment-end-bang-state");
			tokenizer._emitToken(tokenizer._currentToken);
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '>') {
			tokenizer._emitToken(tokenizer._currentToken);
			tokenizer.setState(data_state);
		} else if (data === '-') {
			tokenizer._currentToken.data += '--!';
			tokenizer.setState(comment_end_dash_state);
		} else {
			tokenizer._currentToken.data += '--!' + data;
			tokenizer.setState(comment_state);
		}
		return true;
	}

	function doctype_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("expected-doctype-name-but-got-eof");
			tokenizer._currentToken.forceQuirks = true;
			buffer.unget(data);
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (isWhitespace(data)) {
			tokenizer.setState(before_doctype_name_state);
		} else {
			tokenizer._parseError("need-space-after-doctype");
			buffer.unget(data);
			tokenizer.setState(before_doctype_name_state);
		}
		return true;
	}

	function before_doctype_name_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("expected-doctype-name-but-got-eof");
			tokenizer._currentToken.forceQuirks = true;
			buffer.unget(data);
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (isWhitespace(data)) {
			// pass
		} else if (data === '>') {
			tokenizer._parseError("expected-doctype-name-but-got-right-bracket");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else {
			if (isAlpha(data))
				data = data.toLowerCase();
			tokenizer._currentToken.name = data;
			tokenizer.setState(doctype_name_state);
		}
		return true;
	}

	function doctype_name_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._currentToken.forceQuirks = true;
			buffer.unget(data);
			tokenizer._parseError("eof-in-doctype-name");
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (isWhitespace(data)) {
			tokenizer.setState(after_doctype_name_state);
		} else if (data === '>') {
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else {
			if (isAlpha(data))
				data = data.toLowerCase();
			tokenizer._currentToken.name += data;
			buffer.commit();
		}
		return true;
	}

	function after_doctype_name_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._currentToken.forceQuirks = true;
			buffer.unget(data);
			tokenizer._parseError("eof-in-doctype");
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (isWhitespace(data)) {
			// pass
		} else if (data === '>') {
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else {
			if (['p', 'P'].indexOf(data) > -1) {
				var expected = [['u', 'U'], ['b', 'B'], ['l', 'L'], ['i', 'I'], ['c', 'C']];
				var matched = expected.every(function(expected){
					data = buffer.char();
					return expected.indexOf(data) > -1;
				});
				if (matched) {
					tokenizer.setState(after_doctype_public_keyword_state);
					return true;
				}
			} else if (['s', 'S'].indexOf(data) > -1) {
				var expected = [['y', 'Y'], ['s', 'S'], ['t', 'T'], ['e', 'E'], ['m', 'M']];
				var matched = expected.every(function(expected){
					data = buffer.char();
					return expected.indexOf(data) > -1;
				});
				if (matched) {
					tokenizer.setState(after_doctype_system_keyword_state);
					return true;
				}
			}

			// All the characters read before the current 'data' will be
			// [a-zA-Z], so they're garbage in the bogus doctype and can be
			// discarded; only the latest character might be '>' or EOF
			// and needs to be ungetted
			buffer.unget(data);
			tokenizer._currentToken.forceQuirks = true;

			if (data === InputStream.EOF) {
				tokenizer._parseError("eof-in-doctype");
				buffer.unget(data);
				tokenizer.setState(data_state);
				tokenizer._emitCurrentToken();
			} else {
				tokenizer._parseError("expected-space-or-right-bracket-in-doctype", {data: data});
				tokenizer.setState(bogus_doctype_state);
			}
		}
		return true;
	}

	function after_doctype_public_keyword_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			buffer.unget(data);
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (isWhitespace(data)) {
			tokenizer.setState(before_doctype_public_identifier_state);
		} else if (data === "'" || data === '"') {
			tokenizer._parseError("unexpected-char-in-doctype");
			buffer.unget(data);
			tokenizer.setState(before_doctype_public_identifier_state);
		} else {
			buffer.unget(data);
			tokenizer.setState(before_doctype_public_identifier_state);
		}
		return true;
	}

	function before_doctype_public_identifier_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			buffer.unget(data);
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (isWhitespace(data)) {
			// pass
		} else if (data === '"') {
			tokenizer._currentToken.publicId = '';
			tokenizer.setState(doctype_public_identifier_double_quoted_state);
		} else if (data === "'") {
			tokenizer._currentToken.publicId = '';
			tokenizer.setState(doctype_public_identifier_single_quoted_state);
		} else if (data === '>') {
			tokenizer._parseError("unexpected-end-of-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else {
			tokenizer._parseError("unexpected-char-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer.setState(bogus_doctype_state);
		}
		return true;
	}

	function doctype_public_identifier_double_quoted_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			buffer.unget(data);
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (data === '"') {
			tokenizer.setState(after_doctype_public_identifier_state);
		} else if (data === '>') {
			tokenizer._parseError("unexpected-end-of-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else {
			tokenizer._currentToken.publicId += data;
		}
		return true;
	}

	function doctype_public_identifier_single_quoted_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			buffer.unget(data);
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (data === "'") {
			tokenizer.setState(after_doctype_public_identifier_state);
		} else if (data === '>') {
			tokenizer._parseError("unexpected-end-of-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else {
			tokenizer._currentToken.publicId += data;
		}
		return true;
	}

	function after_doctype_public_identifier_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer._emitCurrentToken();
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			tokenizer.setState(between_doctype_public_and_system_identifiers_state);
		} else if (data === '>') {
			tokenizer.setState(data_state);
			tokenizer._emitCurrentToken();
		} else if (data === '"') {
			tokenizer._parseError("unexpected-char-in-doctype");
			tokenizer._currentToken.systemId = '';
			tokenizer.setState(doctype_system_identifier_double_quoted_state);
		} else if (data === "'") {
			tokenizer._parseError("unexpected-char-in-doctype");
			tokenizer._currentToken.systemId = '';
			tokenizer.setState(doctype_system_identifier_single_quoted_state);
		} else {
			tokenizer._parseError("unexpected-char-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer.setState(bogus_doctype_state);
		}
		return true;
	}

	function between_doctype_public_and_system_identifiers_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer._emitCurrentToken();
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			// pass
		} else if (data === '>') {
			tokenizer._emitCurrentToken();
			tokenizer.setState(data_state);
		} else if (data === '"') {
			tokenizer._currentToken.systemId = '';
			tokenizer.setState(doctype_system_identifier_double_quoted_state);
		} else if (data === "'") {
			tokenizer._currentToken.systemId = '';
			tokenizer.setState(doctype_system_identifier_single_quoted_state);
		} else {
			tokenizer._parseError("unexpected-char-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer.setState(bogus_doctype_state);
		}
		return true;
	}

	function after_doctype_system_keyword_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer._emitCurrentToken();
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			tokenizer.setState(before_doctype_system_identifier_state);
		} else if (data === "'" || data === '"') {
			tokenizer._parseError("unexpected-char-in-doctype");
			buffer.unget(data);
			tokenizer.setState(before_doctype_system_identifier_state);
		} else {
			buffer.unget(data);
			tokenizer.setState(before_doctype_system_identifier_state);
		}
		return true;
	}

	function before_doctype_system_identifier_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer._emitCurrentToken();
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			// pass
		} else if (data === '"') {
			tokenizer._currentToken.systemId = '';
			tokenizer.setState(doctype_system_identifier_double_quoted_state);
		} else if (data === "'") {
			tokenizer._currentToken.systemId = '';
			tokenizer.setState(doctype_system_identifier_single_quoted_state);
		} else if (data === '>') {
			tokenizer._parseError("unexpected-end-of-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer._emitCurrentToken();
			tokenizer.setState(data_state);
		} else {
			tokenizer._parseError("unexpected-char-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer.setState(bogus_doctype_state);
		}
		return true;
	}

	function doctype_system_identifier_double_quoted_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer._emitCurrentToken();
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === '"') {
			tokenizer.setState(after_doctype_system_identifier_state);
		} else if (data === '>') {
			tokenizer._parseError("unexpected-end-of-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer._emitCurrentToken();
			tokenizer.setState(data_state);
		} else {
			tokenizer._currentToken.systemId += data;
		}
		return true;
	}

	function doctype_system_identifier_single_quoted_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer._emitCurrentToken();
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (data === "'") {
			tokenizer.setState(after_doctype_system_identifier_state);
		} else if (data === '>') {
			tokenizer._parseError("unexpected-end-of-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer._emitCurrentToken();
			tokenizer.setState(data_state);
		} else {
			tokenizer._currentToken.systemId += data;
		}
		return true;
	}

	function after_doctype_system_identifier_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			tokenizer._parseError("eof-in-doctype");
			tokenizer._currentToken.forceQuirks = true;
			tokenizer._emitCurrentToken();
			buffer.unget(data);
			tokenizer.setState(data_state);
		} else if (isWhitespace(data)) {
			// pass
		} else if (data === '>') {
			tokenizer._emitCurrentToken();
			tokenizer.setState(data_state);
		} else {
			tokenizer._parseError("unexpected-char-in-doctype");
			tokenizer.setState(bogus_doctype_state);
		}
		return true;
	}

	function bogus_doctype_state(buffer) {
		var data = buffer.char();
		if (data === InputStream.EOF) {
			buffer.unget(data);
			tokenizer._emitCurrentToken();
			tokenizer.setState(data_state);
		} else if (data === '>') {
			tokenizer._emitCurrentToken();
			tokenizer.setState(data_state);
		}
		return true;
	}
};

Object.defineProperty(Tokenizer.prototype, 'lineNumber', {
	get: function() {
		return this._inputStream.location().line;
	}
});

Object.defineProperty(Tokenizer.prototype, 'columnNumber', {
	get: function() {
		return this._inputStream.location().column;
	}
});

exports.Tokenizer = Tokenizer;

},
{"./EntityParser":2,"./InputStream":3}],
6:[function(_dereq_,module,exports){
var assert = _dereq_('assert');

var messages = _dereq_('./messages.json');
var constants = _dereq_('./constants');

var EventEmitter = _dereq_('events').EventEmitter;

var Tokenizer = _dereq_('./Tokenizer').Tokenizer;
var ElementStack = _dereq_('./ElementStack').ElementStack;
var StackItem = _dereq_('./StackItem').StackItem;

var Marker = {};

function isWhitespace(ch) {
	return ch === " " || ch === "\n" || ch === "\t" || ch === "\r" || ch === "\f";
}

function isWhitespaceOrReplacementCharacter(ch) {
	return isWhitespace(ch) || ch === '\uFFFD';
}

function isAllWhitespace(characters) {
	for (var i = 0; i < characters.length; i++) {
		var ch = characters[i];
		if (!isWhitespace(ch))
			return false;
	}
	return true;
}

function isAllWhitespaceOrReplacementCharacters(characters) {
	for (var i = 0; i < characters.length; i++) {
		var ch = characters[i];
		if (!isWhitespaceOrReplacementCharacter(ch))
			return false;
	}
	return true;
}

function getAttribute(node, name) {
	for (var i = 0; i < node.attributes.length; i++) {
		var attribute = node.attributes[i];
		if (attribute.nodeName === name) {
			return attribute;
		}
	}
	return null;
}

function CharacterBuffer(characters) {
	this.characters = characters;
	this.current = 0;
	this.end = this.characters.length;
}

CharacterBuffer.prototype.skipAtMostOneLeadingNewline = function() {
	if (this.characters[this.current] === '\n')
		this.current++;
};

CharacterBuffer.prototype.skipLeadingWhitespace = function() {
	while (isWhitespace(this.characters[this.current])) {
		if (++this.current == this.end)
			return;
	}
};

CharacterBuffer.prototype.skipLeadingNonWhitespace = function() {
	while (!isWhitespace(this.characters[this.current])) {
		if (++this.current == this.end)
			return;
	}
};

CharacterBuffer.prototype.takeRemaining = function() {
	return this.characters.substring(this.current);
};

CharacterBuffer.prototype.takeLeadingWhitespace = function() {
	var start = this.current;
	this.skipLeadingWhitespace();
	if (start === this.current)
		return "";
	return this.characters.substring(start, this.current - start);
};

Object.defineProperty(CharacterBuffer.prototype, 'length', {
	get: function(){
		return this.end - this.current;
	}
});

/**
 *
 * @constructor
 */
function TreeBuilder() {
	this.tokenizer = null;
	this.errorHandler = null;
	this.scriptingEnabled = false;
	this.document = null;
	this.head = null;
	this.form = null;
	this.openElements = new ElementStack();
	this.activeFormattingElements = [];
	this.insertionMode = null;
	this.insertionModeName = "";
	this.originalInsertionMode = "";
	this.inQuirksMode = false; // TODO quirks mode
	this.compatMode = "no quirks";
	this.framesetOk = true;
	this.redirectAttachToFosterParent = false;
	this.selfClosingFlagAcknowledged = false;
	this.context = "";
	this.pendingTableCharacters = [];
	this.shouldSkipLeadingNewline = false;

	var tree = this;
	var modes = this.insertionModes = {};
	modes.base = {
		end_tag_handlers: {"-default": 'endTagOther'},
		start_tag_handlers: {"-default": 'startTagOther'},
		processEOF: function() {
			tree.generateImpliedEndTags();
			if (tree.openElements.length > 2) {
				tree.parseError('expected-closing-tag-but-got-eof');
			} else if (tree.openElements.length == 2 &&
				tree.openElements.item(1).localName != 'body') {
				// This happens for framesets or something?
				tree.parseError('expected-closing-tag-but-got-eof');
			} else if (tree.context && tree.openElements.length > 1) {
				// XXX This is not what the specification says. Not sure what to do here.
				//tree.parseError('eof-in-innerhtml');
			}
		},
		processComment: function(data) {
			// For most phases the following is forceQuirks. Where it's not it will be
			// overridden.
			tree.insertComment(data, tree.currentStackItem().node);
		},
		processDoctype: function(name, publicId, systemId, forceQuirks) {
			tree.parseError('unexpected-doctype');
		},
		processStartTag: function(name, attributes, selfClosing) {
			if (this[this.start_tag_handlers[name]]) {
				this[this.start_tag_handlers[name]](name, attributes, selfClosing);
			} else if (this[this.start_tag_handlers["-default"]]) {
				this[this.start_tag_handlers["-default"]](name, attributes, selfClosing);
			} else {
				throw(new Error("No handler found for "+name));
			}
		},
		processEndTag: function(name) {
			if (this[this.end_tag_handlers[name]]) {
				this[this.end_tag_handlers[name]](name);
			} else if (this[this.end_tag_handlers["-default"]]) {
				this[this.end_tag_handlers["-default"]](name);
			} else {
				throw(new Error("No handler found for "+name));
			}
		},
		startTagHtml: function(name, attributes) {
			modes.inBody.startTagHtml(name, attributes);
		}
	};

	modes.initial = Object.create(modes.base);

	modes.initial.processEOF = function() {
		tree.parseError("expected-doctype-but-got-eof");
		this.anythingElse();
		tree.insertionMode.processEOF();
	};

	modes.initial.processComment = function(data) {
		tree.insertComment(data, tree.document);
	};

	modes.initial.processDoctype = function(name, publicId, systemId, forceQuirks) {
		tree.insertDoctype(name || '', publicId || '', systemId || '');

		if (forceQuirks || name != 'html' || (publicId != null && ([
					"+//silmaril//dtd html pro v0r11 19970101//",
					"-//advasoft ltd//dtd html 3.0 aswedit + extensions//",
					"-//as//dtd html 3.0 aswedit + extensions//",
					"-//ietf//dtd html 2.0 level 1//",
					"-//ietf//dtd html 2.0 level 2//",
					"-//ietf//dtd html 2.0 strict level 1//",
					"-//ietf//dtd html 2.0 strict level 2//",
					"-//ietf//dtd html 2.0 strict//",
					"-//ietf//dtd html 2.0//",
					"-//ietf//dtd html 2.1e//",
					"-//ietf//dtd html 3.0//",
					"-//ietf//dtd html 3.0//",
					"-//ietf//dtd html 3.2 final//",
					"-//ietf//dtd html 3.2//",
					"-//ietf//dtd html 3//",
					"-//ietf//dtd html level 0//",
					"-//ietf//dtd html level 0//",
					"-//ietf//dtd html level 1//",
					"-//ietf//dtd html level 1//",
					"-//ietf//dtd html level 2//",
					"-//ietf//dtd html level 2//",
					"-//ietf//dtd html level 3//",
					"-//ietf//dtd html level 3//",
					"-//ietf//dtd html strict level 0//",
					"-//ietf//dtd html strict level 0//",
					"-//ietf//dtd html strict level 1//",
					"-//ietf//dtd html strict level 1//",
					"-//ietf//dtd html strict level 2//",
					"-//ietf//dtd html strict level 2//",
					"-//ietf//dtd html strict level 3//",
					"-//ietf//dtd html strict level 3//",
					"-//ietf//dtd html strict//",
					"-//ietf//dtd html strict//",
					"-//ietf//dtd html strict//",
					"-//ietf//dtd html//",
					"-//ietf//dtd html//",
					"-//ietf//dtd html//",
					"-//metrius//dtd metrius presentational//",
					"-//microsoft//dtd internet explorer 2.0 html strict//",
					"-//microsoft//dtd internet explorer 2.0 html//",
					"-//microsoft//dtd internet explorer 2.0 tables//",
					"-//microsoft//dtd internet explorer 3.0 html strict//",
					"-//microsoft//dtd internet explorer 3.0 html//",
					"-//microsoft//dtd internet explorer 3.0 tables//",
					"-//netscape comm. corp.//dtd html//",
					"-//netscape comm. corp.//dtd strict html//",
					"-//o'reilly and associates//dtd html 2.0//",
					"-//o'reilly and associates//dtd html extended 1.0//",
					"-//spyglass//dtd html 2.0 extended//",
					"-//sq//dtd html 2.0 hotmetal + extensions//",
					"-//sun microsystems corp.//dtd hotjava html//",
					"-//sun microsystems corp.//dtd hotjava strict html//",
					"-//w3c//dtd html 3 1995-03-24//",
					"-//w3c//dtd html 3.2 draft//",
					"-//w3c//dtd html 3.2 final//",
					"-//w3c//dtd html 3.2//",
					"-//w3c//dtd html 3.2s draft//",
					"-//w3c//dtd html 4.0 frameset//",
					"-//w3c//dtd html 4.0 transitional//",
					"-//w3c//dtd html experimental 19960712//",
					"-//w3c//dtd html experimental 970421//",
					"-//w3c//dtd w3 html//",
					"-//w3o//dtd w3 html 3.0//",
					"-//webtechs//dtd mozilla html 2.0//",
					"-//webtechs//dtd mozilla html//",
					"html"
				].some(publicIdStartsWith)
				|| [
					"-//w3o//dtd w3 html strict 3.0//en//",
					"-/w3c/dtd html 4.0 transitional/en",
					"html"
				].indexOf(publicId.toLowerCase()) > -1
				|| (systemId == null && [
					"-//w3c//dtd html 4.01 transitional//",
					"-//w3c//dtd html 4.01 frameset//"
				].some(publicIdStartsWith)))
			)
			|| (systemId != null && (systemId.toLowerCase() == "http://www.ibm.com/data/dtd/v11/ibmxhtml1-transitional.dtd"))
		) {
			tree.compatMode = "quirks";
			tree.parseError("quirky-doctype");
		} else if (publicId != null && ([
				"-//w3c//dtd xhtml 1.0 transitional//",
				"-//w3c//dtd xhtml 1.0 frameset//"
			].some(publicIdStartsWith)
			|| (systemId != null && [
				"-//w3c//dtd html 4.01 transitional//",
				"-//w3c//dtd html 4.01 frameset//"
			].indexOf(publicId.toLowerCase()) > -1))
		) {
			tree.compatMode = "limited quirks";
			tree.parseError("almost-standards-doctype");
		} else {
			if ((publicId == "-//W3C//DTD HTML 4.0//EN" && (systemId == null || systemId == "http://www.w3.org/TR/REC-html40/strict.dtd"))
				|| (publicId == "-//W3C//DTD HTML 4.01//EN" && (systemId == null || systemId == "http://www.w3.org/TR/html4/strict.dtd"))
				|| (publicId == "-//W3C//DTD XHTML 1.0 Strict//EN" && (systemId == "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"))
				|| (publicId == "-//W3C//DTD XHTML 1.1//EN" && (systemId == "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"))
			) {
				// warning
				//tree.warn("obsolete-doctype");
			} else if (!((systemId == null || systemId == "about:legacy-compat") && publicId == null)) {
				tree.parseError("unknown-doctype");
			}
		}
		tree.setInsertionMode('beforeHTML');
		function publicIdStartsWith(string) {
			return publicId.toLowerCase().indexOf(string) === 0;
		}
	};

	modes.initial.processCharacters = function(buffer) {
		buffer.skipLeadingWhitespace();
		if (!buffer.length)
			return;
		tree.parseError('expected-doctype-but-got-chars');
		this.anythingElse();
		tree.insertionMode.processCharacters(buffer);
	};

	modes.initial.processStartTag = function(name, attributes, selfClosing) {
		tree.parseError('expected-doctype-but-got-start-tag', {name: name});
		this.anythingElse();
		tree.insertionMode.processStartTag(name, attributes, selfClosing);
	};

	modes.initial.processEndTag = function(name) {
		tree.parseError('expected-doctype-but-got-end-tag', {name: name});
		this.anythingElse();
		tree.insertionMode.processEndTag(name);
	};

	modes.initial.anythingElse = function() {
		tree.compatMode = 'quirks';
		tree.setInsertionMode('beforeHTML');
	};

	modes.beforeHTML = Object.create(modes.base);

	modes.beforeHTML.start_tag_handlers = {
		html: 'startTagHtml',
		'-default': 'startTagOther'
	};

	modes.beforeHTML.processEOF = function() {
		this.anythingElse();
		tree.insertionMode.processEOF();
	};

	modes.beforeHTML.processComment = function(data) {
		tree.insertComment(data, tree.document);
	};

	modes.beforeHTML.processCharacters = function(buffer) {
		buffer.skipLeadingWhitespace();
		if (!buffer.length)
			return;
		this.anythingElse();
		tree.insertionMode.processCharacters(buffer);
	};

	modes.beforeHTML.startTagHtml = function(name, attributes, selfClosing) {
		tree.insertHtmlElement(attributes);
		tree.setInsertionMode('beforeHead');
	};

	modes.beforeHTML.startTagOther = function(name, attributes, selfClosing) {
		this.anythingElse();
		tree.insertionMode.processStartTag(name, attributes, selfClosing);
	};

	modes.beforeHTML.processEndTag = function(name) {
		this.anythingElse();
		tree.insertionMode.processEndTag(name);
	};

	modes.beforeHTML.anythingElse = function() {
		tree.insertHtmlElement();
		tree.setInsertionMode('beforeHead');
	};

	modes.afterAfterBody = Object.create(modes.base);

	modes.afterAfterBody.start_tag_handlers = {
		html: 'startTagHtml',
		'-default': 'startTagOther'
	};

	modes.afterAfterBody.processComment = function(data) {
		tree.insertComment(data, tree.document);
	};

	modes.afterAfterBody.processDoctype = function(data) {
		modes.inBody.processDoctype(data);
	};

	modes.afterAfterBody.startTagHtml = function(data, attributes) {
		modes.inBody.startTagHtml(data, attributes);
	};

	modes.afterAfterBody.startTagOther = function(name, attributes, selfClosing) {
		tree.parseError('unexpected-start-tag', {name: name});
		tree.setInsertionMode('inBody');
		tree.insertionMode.processStartTag(name, attributes, selfClosing);
	};

	modes.afterAfterBody.endTagOther = function(name) {
		tree.parseError('unexpected-end-tag', {name: name});
		tree.setInsertionMode('inBody');
		tree.insertionMode.processEndTag(name);
	};

	modes.afterAfterBody.processCharacters = function(data) {
		if (!isAllWhitespace(data.characters)) {
			tree.parseError('unexpected-char-after-body');
			tree.setInsertionMode('inBody');
			return tree.insertionMode.processCharacters(data);
		}
		modes.inBody.processCharacters(data);
	};

	modes.afterBody = Object.create(modes.base);

	modes.afterBody.end_tag_handlers = {
		html: 'endTagHtml',
		'-default': 'endTagOther'
	};

	modes.afterBody.processComment = function(data) {
		// This is needed because data is to be appended to the html element here
		// and not to whatever is currently open.
		tree.insertComment(data, tree.openElements.rootNode);
	};

	modes.afterBody.processCharacters = function(data) {
		if (!isAllWhitespace(data.characters)) {
			tree.parseError('unexpected-char-after-body');
			tree.setInsertionMode('inBody');
			return tree.insertionMode.processCharacters(data);
		}
		modes.inBody.processCharacters(data);
	};

	modes.afterBody.processStartTag = function(name, attributes, selfClosing) {
		tree.parseError('unexpected-start-tag-after-body', {name: name});
		tree.setInsertionMode('inBody');
		tree.insertionMode.processStartTag(name, attributes, selfClosing);
	};

	modes.afterBody.endTagHtml = function(name) {
		if (tree.context) {
			tree.parseError('end-html-in-innerhtml');
		} else {
			// XXX This may need to be done, not sure
			// Don't set last_phase to the current phase but to the inBody phase
			// instead. No need for extra parseErrors if there's something after
			// </html>.
			// Try <!doctype html>X</html>X for instance
			tree.setInsertionMode('afterAfterBody');
		}
	};

	modes.afterBody.endTagOther = function(name) {
		tree.parseError('unexpected-end-tag-after-body', {name: name});
		tree.setInsertionMode('inBody');
		tree.insertionMode.processEndTag(name);
	};

	modes.afterFrameset = Object.create(modes.base);

	modes.afterFrameset.start_tag_handlers = {
		html: 'startTagHtml',
		noframes: 'startTagNoframes',
		'-default': 'startTagOther'
	};

	modes.afterFrameset.end_tag_handlers = {
		html: 'endTagHtml',
		'-default': 'endTagOther'
	};

	modes.afterFrameset.processCharacters = function(buffer) {
		var characters = buffer.takeRemaining();
		var whitespace = "";
		for (var i = 0; i < characters.length; i++) {
			var ch = characters[i];
			if (isWhitespace(ch))
				whitespace += ch;
		}
		if (whitespace) {
			tree.insertText(whitespace);
		}
		if (whitespace.length < characters.length)
			tree.parseError('expected-eof-but-got-char');
	};

	modes.afterFrameset.startTagNoframes = function(name, attributes) {
		modes.inHead.processStartTag(name, attributes);
	};

	modes.afterFrameset.startTagOther = function(name, attributes) {
		tree.parseError("unexpected-start-tag-after-frameset", {name: name});
	};

	modes.afterFrameset.endTagHtml = function(name) {
		tree.setInsertionMode('afterAfterFrameset');
	};

	modes.afterFrameset.endTagOther = function(name) {
		tree.parseError("unexpected-end-tag-after-frameset", {name: name});
	};

	modes.beforeHead = Object.create(modes.base);

	modes.beforeHead.start_tag_handlers = {
		html: 'startTagHtml',
		head: 'startTagHead',
		'-default': 'startTagOther'
	};

	modes.beforeHead.end_tag_handlers = {
		html: 'endTagImplyHead',
		head: 'endTagImplyHead',
		body: 'endTagImplyHead',
		br: 'endTagImplyHead',
		'-default': 'endTagOther'
	};

	modes.beforeHead.processEOF = function() {
		this.startTagHead('head', []);
		tree.insertionMode.processEOF();
	};

	modes.beforeHead.processCharacters = function(buffer) {
		buffer.skipLeadingWhitespace();
		if (!buffer.length)
			return;
		this.startTagHead('head', []);
		tree.insertionMode.processCharacters(buffer);
	};

	modes.beforeHead.startTagHead = function(name, attributes) {
		tree.insertHeadElement(attributes);
		tree.setInsertionMode('inHead');
	};

	modes.beforeHead.startTagOther = function(name, attributes, selfClosing) {
		this.startTagHead('head', []);
		tree.insertionMode.processStartTag(name, attributes, selfClosing);
	};

	modes.beforeHead.endTagImplyHead = function(name) {
		this.startTagHead('head', []);
		tree.insertionMode.processEndTag(name);
	};

	modes.beforeHead.endTagOther = function(name) {
		tree.parseError('end-tag-after-implied-root', {name: name});
	};

	modes.inHead = Object.create(modes.base);

	modes.inHead.start_tag_handlers = {
		html: 'startTagHtml',
		head: 'startTagHead',
		title: 'startTagTitle',
		script: 'startTagScript',
		style: 'startTagNoFramesStyle',
		noscript: 'startTagNoScript',
		noframes: 'startTagNoFramesStyle',
		base: 'startTagBaseBasefontBgsoundLink',
		basefont: 'startTagBaseBasefontBgsoundLink',
		bgsound: 'startTagBaseBasefontBgsoundLink',
		link: 'startTagBaseBasefontBgsoundLink',
		meta: 'startTagMeta',
		"-default": 'startTagOther'
	};

	modes.inHead.end_tag_handlers = {
		head: 'endTagHead',
		html: 'endTagHtmlBodyBr',
		body: 'endTagHtmlBodyBr',
		br: 'endTagHtmlBodyBr',
		"-default": 'endTagOther'
	};

	modes.inHead.processEOF = function() {
		var name = tree.currentStackItem().localName;
		if (['title', 'style', 'script'].indexOf(name) != -1) {
			tree.parseError("expected-named-closing-tag-but-got-eof", {name: name});
			tree.popElement();
		}

		this.anythingElse();

		tree.insertionMode.processEOF();
	};

	modes.inHead.processCharacters = function(buffer) {
		var leadingWhitespace = buffer.takeLeadingWhitespace();
		if (leadingWhitespace)
			tree.insertText(leadingWhitespace);
		if (!buffer.length)
			return;
		this.anythingElse();
		tree.insertionMode.processCharacters(buffer);
	};

	modes.inHead.startTagHtml = function(name, attributes) {
		modes.inBody.processStartTag(name, attributes);
	};

	modes.inHead.startTagHead = function(name, attributes) {
		tree.parseError('two-heads-are-not-better-than-one');
	};

	modes.inHead.startTagTitle = function(name, attributes) {
		tree.processGenericRCDATAStartTag(name, attributes);
	};

	modes.inHead.startTagNoScript = function(name, attributes) {
		if (tree.scriptingEnabled)
			return tree.processGenericRawTextStartTag(name, attributes);
		tree.insertElement(name, attributes);
		tree.setInsertionMode('inHeadNoscript');
	};

	modes.inHead.startTagNoFramesStyle = function(name, attributes) {
		// XXX Need to decide whether to implement the scripting disabled case
		tree.processGenericRawTextStartTag(name, attributes);
	};

	modes.inHead.startTagScript = function(name, attributes) {
		tree.insertElement(name, attributes);
		tree.tokenizer.setState(Tokenizer.SCRIPT_DATA);
		tree.originalInsertionMode = tree.insertionModeName;
		tree.setInsertionMode('text');
	};

	modes.inHead.startTagBaseBasefontBgsoundLink = function(name, attributes) {
		tree.insertSelfClosingElement(name, attributes);
	};

	modes.inHead.startTagMeta = function(name, attributes) {
		tree.insertSelfClosingElement(name, attributes);
		// @todo process charset attributes
	};

	modes.inHead.startTagOther = function(name, attributes, selfClosing) {
		this.anythingElse();
		tree.insertionMode.processStartTag(name, attributes, selfClosing);
	};

	modes.inHead.endTagHead = function(name) {
		if (tree.openElements.item(tree.openElements.length - 1).localName == 'head') {
			tree.openElements.pop();
		} else {
			tree.parseError('unexpected-end-tag', {name: 'head'});
		}
		tree.setInsertionMode('afterHead');
	};

	modes.inHead.endTagHtmlBodyBr = function(name) {
		this.anythingElse();
		tree.insertionMode.processEndTag(name);
	};

	modes.inHead.endTagOther = function(name) {
		tree.parseError('unexpected-end-tag', {name: name});
	};

	modes.inHead.anythingElse = function() {
		this.endTagHead('head');
	};

	modes.afterHead = Object.create(modes.base);

	modes.afterHead.start_tag_handlers = {
		html: 'startTagHtml',
		head: 'startTagHead',
		body: 'startTagBody',
		frameset: 'startTagFrameset',
		base: 'startTagFromHead',
		link: 'startTagFromHead',
		meta: 'startTagFromHead',
		script: 'startTagFromHead',
		// XXX noframes: 'startTagFromHead' ?
		style: 'startTagFromHead',
		title: 'startTagFromHead',
		"-default": 'startTagOther'
	};

	modes.afterHead.end_tag_handlers = {
		body: 'endTagBodyHtmlBr',
		html: 'endTagBodyHtmlBr',
		br: 'endTagBodyHtmlBr',
		"-default": 'endTagOther'
	};

	modes.afterHead.processEOF = function() {
		this.anythingElse();
		tree.insertionMode.processEOF();
	};

	modes.afterHead.processCharacters = function(buffer) {
		var leadingWhitespace = buffer.takeLeadingWhitespace();
		if (leadingWhitespace)
			tree.insertText(leadingWhitespace);
		if (!buffer.length)
			return;
		this.anythingElse();
		tree.insertionMode.processCharacters(buffer);
	};

	modes.afterHead.startTagHtml = function(name, attributes) {
		modes.inBody.processStartTag(name, attributes);
	};

	modes.afterHead.startTagBody = function(name, attributes) {
		tree.framesetOk = false;
		tree.insertBodyElement(attributes);
		tree.setInsertionMode('inBody');
	};

	modes.afterHead.startTagFrameset = function(name, attributes) {
		tree.insertElement(name, attributes);
		tree.setInsertionMode('inFrameset');
	};

	modes.afterHead.startTagFromHead = function(name, attributes, selfClosing) {
		tree.parseError("unexpected-start-tag-out-of-my-head", {name: name});
		// FIXME head pointer
		tree.openElements.push(tree.head);
		modes.inHead.processStartTag(name, attributes, selfClosing);
		tree.openElements.remove(tree.head);
	};

	modes.afterHead.startTagHead = function(name, attributes, selfClosing) {
		tree.parseError('unexpected-start-tag', {name: name});
	};

	modes.afterHead.startTagOther = function(name, attributes, selfClosing) {
		this.anythingElse();
		tree.insertionMode.processStartTag(name, attributes, selfClosing);
	};

	modes.afterHead.endTagBodyHtmlBr = function(name) {
		this.anythingElse();
		tree.insertionMode.processEndTag(name);
	};

	modes.afterHead.endTagOther = function(name) {
		tree.parseError('unexpected-end-tag', {name: name});
	};

	modes.afterHead.anythingElse = function() {
		tree.insertBodyElement([]);
		tree.setInsertionMode('inBody');
		tree.framesetOk = true;
	}

	modes.inBody = Object.create(modes.base);

	modes.inBody.start_tag_handlers = {
		html: 'startTagHtml',
		head: 'startTagMisplaced',
		base: 'startTagProcessInHead',
		basefont: 'startTagProcessInHead',
		bgsound: 'startTagProcessInHead',
		link: 'startTagProcessInHead',
		meta: 'startTagProcessInHead',
		noframes: 'startTagProcessInHead',
		script: 'startTagProcessInHead',
		style: 'startTagProcessInHead',
		title: 'startTagProcessInHead',
		body: 'startTagBody',
		form: 'startTagForm',
		plaintext: 'startTagPlaintext',
		a: 'startTagA',
		button: 'startTagButton',
		xmp: 'startTagXmp',
		table: 'startTagTable',
		hr: 'startTagHr',
		image: 'startTagImage',
		input: 'startTagInput',
		textarea: 'startTagTextarea',
		select: 'startTagSelect',
		isindex: 'startTagIsindex',
		applet:	'startTagAppletMarqueeObject',
		marquee:	'startTagAppletMarqueeObject',
		object:	'startTagAppletMarqueeObject',
		li: 'startTagListItem',
		dd: 'startTagListItem',
		dt: 'startTagListItem',
		address: 'startTagCloseP',
		article: 'startTagCloseP',
		aside: 'startTagCloseP',
		blockquote: 'startTagCloseP',
		center: 'startTagCloseP',
		details: 'startTagCloseP',
		dir: 'startTagCloseP',
		div: 'startTagCloseP',
		dl: 'startTagCloseP',
		fieldset: 'startTagCloseP',
		figcaption: 'startTagCloseP',
		figure: 'startTagCloseP',
		footer: 'startTagCloseP',
		header: 'startTagCloseP',
		hgroup: 'startTagCloseP',
		main: 'startTagCloseP',
		menu: 'startTagCloseP',
		nav: 'startTagCloseP',
		ol: 'startTagCloseP',
		p: 'startTagCloseP',
		section: 'startTagCloseP',
		summary: 'startTagCloseP',
		ul: 'startTagCloseP',
		listing: 'startTagPreListing',
		pre: 'startTagPreListing',
		b: 'startTagFormatting',
		big: 'startTagFormatting',
		code: 'startTagFormatting',
		em: 'startTagFormatting',
		font: 'startTagFormatting',
		i: 'startTagFormatting',
		s: 'startTagFormatting',
		small: 'startTagFormatting',
		strike: 'startTagFormatting',
		strong: 'startTagFormatting',
		tt: 'startTagFormatting',
		u: 'startTagFormatting',
		nobr: 'startTagNobr',
		area: 'startTagVoidFormatting',
		br: 'startTagVoidFormatting',
		embed: 'startTagVoidFormatting',
		img: 'startTagVoidFormatting',
		keygen: 'startTagVoidFormatting',
		wbr: 'startTagVoidFormatting',
		param: 'startTagParamSourceTrack',
		source: 'startTagParamSourceTrack',
		track: 'startTagParamSourceTrack',
		iframe: 'startTagIFrame',
		noembed: 'startTagRawText',
		noscript: 'startTagRawText',
		h1: 'startTagHeading',
		h2: 'startTagHeading',
		h3: 'startTagHeading',
		h4: 'startTagHeading',
		h5: 'startTagHeading',
		h6: 'startTagHeading',
		caption: 'startTagMisplaced',
		col: 'startTagMisplaced',
		colgroup: 'startTagMisplaced',
		frame: 'startTagMisplaced',
		frameset: 'startTagFrameset',
		tbody: 'startTagMisplaced',
		td: 'startTagMisplaced',
		tfoot: 'startTagMisplaced',
		th: 'startTagMisplaced',
		thead: 'startTagMisplaced',
		tr: 'startTagMisplaced',
		option: 'startTagOptionOptgroup',
		optgroup: 'startTagOptionOptgroup',
		math: 'startTagMath',
		svg: 'startTagSVG',
		rt: 'startTagRpRt',
		rp: 'startTagRpRt',
		"-default": 'startTagOther'
	};

	modes.inBody.end_tag_handlers = {
		p: 'endTagP',
		body: 'endTagBody',
		html: 'endTagHtml',
		address: 'endTagBlock',
		article: 'endTagBlock',
		aside: 'endTagBlock',
		blockquote: 'endTagBlock',
		button: 'endTagBlock',
		center: 'endTagBlock',
		details: 'endTagBlock',
		dir: 'endTagBlock',
		div: 'endTagBlock',
		dl: 'endTagBlock',
		fieldset: 'endTagBlock',
		figcaption: 'endTagBlock',
		figure: 'endTagBlock',
		footer: 'endTagBlock',
		header: 'endTagBlock',
		hgroup: 'endTagBlock',
		listing: 'endTagBlock',
		main: 'endTagBlock',
		menu: 'endTagBlock',
		nav: 'endTagBlock',
		ol: 'endTagBlock',
		pre: 'endTagBlock',
		section: 'endTagBlock',
		summary: 'endTagBlock',
		ul: 'endTagBlock',
		form: 'endTagForm',
		applet: 'endTagAppletMarqueeObject',
		marquee: 'endTagAppletMarqueeObject',
		object: 'endTagAppletMarqueeObject',
		dd: 'endTagListItem',
		dt: 'endTagListItem',
		li: 'endTagListItem',
		h1: 'endTagHeading',
		h2: 'endTagHeading',
		h3: 'endTagHeading',
		h4: 'endTagHeading',
		h5: 'endTagHeading',
		h6: 'endTagHeading',
		a: 'endTagFormatting',
		b: 'endTagFormatting',
		big: 'endTagFormatting',
		code: 'endTagFormatting',
		em: 'endTagFormatting',
		font: 'endTagFormatting',
		i: 'endTagFormatting',
		nobr: 'endTagFormatting',
		s: 'endTagFormatting',
		small: 'endTagFormatting',
		strike: 'endTagFormatting',
		strong: 'endTagFormatting',
		tt: 'endTagFormatting',
		u: 'endTagFormatting',
		br: 'endTagBr',
		"-default": 'endTagOther'
	};

	modes.inBody.processCharacters = function(buffer) {
		if (tree.shouldSkipLeadingNewline) {
			tree.shouldSkipLeadingNewline = false;
			buffer.skipAtMostOneLeadingNewline();
		}
		tree.reconstructActiveFormattingElements();
		var characters = buffer.takeRemaining();
		characters = characters.replace(/\u0000/g, function(match, index){
			// @todo position
			tree.parseError("invalid-codepoint");
			return '';
		});
		if (!characters)
			return;
		tree.insertText(characters);
		if (tree.framesetOk && !isAllWhitespaceOrReplacementCharacters(characters))
			tree.framesetOk = false;
	};

	modes.inBody.startTagHtml = function(name, attributes) {
		tree.parseError('non-html-root');
		tree.addAttributesToElement(tree.openElements.rootNode, attributes);
	};

	modes.inBody.startTagProcessInHead = function(name, attributes) {
		modes.inHead.processStartTag(name, attributes);
	};

	modes.inBody.startTagBody = function(name, attributes) {
		tree.parseError('unexpected-start-tag', {name: 'body'});
		if (tree.openElements.length == 1 ||
			tree.openElements.item(1).localName != 'body') {
			assert.ok(tree.context);
		} else {
			tree.framesetOk = false;
			tree.addAttributesToElement(tree.openElements.bodyElement, attributes);
		}
	};

	modes.inBody.startTagFrameset = function(name, attributes) {
		tree.parseError('unexpected-start-tag', {name: 'frameset'});
		if (tree.openElements.length == 1 ||
			tree.openElements.item(1).localName != 'body') {
			assert.ok(tree.context);
		} else if (tree.framesetOk) {
			tree.detachFromParent(tree.openElements.bodyElement);
			while (tree.openElements.length > 1)
				tree.openElements.pop();
			tree.insertElement(name, attributes);
			tree.setInsertionMode('inFrameset');
		}
	};

	modes.inBody.startTagCloseP = function(name, attributes) {
		if (tree.openElements.inButtonScope('p'))
			this.endTagP('p');
		tree.insertElement(name, attributes);
	};

	modes.inBody.startTagPreListing = function(name, attributes) {
		if (tree.openElements.inButtonScope('p'))
			this.endTagP('p');
		tree.insertElement(name, attributes);
		tree.framesetOk = false;
		tree.shouldSkipLeadingNewline = true;
	};

	modes.inBody.startTagForm = function(name, attributes) {
		if (tree.form) {
			tree.parseError('unexpected-start-tag', {name: name});
		} else {
			if (tree.openElements.inButtonScope('p'))
				this.endTagP('p');
			tree.insertElement(name, attributes);
			tree.form = tree.currentStackItem();
		}
	};

	modes.inBody.startTagRpRt = function(name, attributes) {
		if (tree.openElements.inScope('ruby')) {
			tree.generateImpliedEndTags();
			if (tree.currentStackItem().localName != 'ruby') {
				tree.parseError('unexpected-start-tag', {name: name});
			}
		}
		tree.insertElement(name, attributes);
	};

	modes.inBody.startTagListItem = function(name, attributes) {
		/// @todo: Fix according to current spec. http://www.w3.org/TR/html5/tree-construction.html#parsing-main-inbody
		var stopNames = {li: ['li'], dd: ['dd', 'dt'], dt: ['dd', 'dt']};
		var stopName = stopNames[name];

		var els = tree.openElements;
		for (var i = els.length - 1; i >= 0; i--) {
			var node = els.item(i);
			if (stopName.indexOf(node.localName) != -1) {
				tree.insertionMode.processEndTag(node.localName);
				break;
			}

			// todo isScoping()
			if (node.isSpecial() && node.localName !== 'p' && node.localName !== 'address' && node.localName !== 'div')
				break;
		}
		if (tree.openElements.inButtonScope('p'))
			this.endTagP('p');

		// Always insert an <li> element
		tree.insertElement(name, attributes);
		tree.framesetOk = false;
	};

	modes.inBody.startTagPlaintext = function(name, attributes) {
		if (tree.openElements.inButtonScope('p'))
			this.endTagP('p');
		tree.insertElement(name, attributes);
		tree.tokenizer.setState(Tokenizer.PLAINTEXT);
	};

	modes.inBody.startTagHeading = function(name, attributes) {
		if (tree.openElements.inButtonScope('p'))
			this.endTagP('p');
		if (tree.currentStackItem().isNumberedHeader()) {
			tree.parseError('unexpected-start-tag', {name: name});
			tree.popElement();
		}
		tree.insertElement(name, attributes);
	};

	modes.inBody.startTagA = function(name, attributes) {
		var activeA = tree.elementInActiveFormattingElements('a');
		if (activeA) {
			tree.parseError("unexpected-start-tag-implies-end-tag", {startName: "a", endName: "a"});
			tree.adoptionAgencyEndTag('a');
			if (tree.openElements.contains(activeA))
				tree.openElements.remove(activeA);
			tree.removeElementFromActiveFormattingElements(activeA);
		}
		tree.reconstructActiveFormattingElements();
		tree.insertFormattingElement(name, attributes);
	};

	modes.inBody.startTagFormatting = function(name, attributes) {
		tree.reconstructActiveFormattingElements();
		tree.insertFormattingElement(name, attributes);
	};

	modes.inBody.startTagNobr = function(name, attributes) {
		tree.reconstructActiveFormattingElements();
		if (tree.openElements.inScope('nobr')) {
			tree.parseError("unexpected-start-tag-implies-end-tag", {startName: 'nobr', endName: 'nobr'});
			this.processEndTag('nobr');
				// XXX Need tests that trigger the following
				tree.reconstructActiveFormattingElements();
		}
		tree.insertFormattingElement(name, attributes);
	};

	modes.inBody.startTagButton = function(name, attributes) {
		if (tree.openElements.inScope('button')) {
			tree.parseError('unexpected-start-tag-implies-end-tag', {startName: 'button', endName: 'button'});
			this.processEndTag('button');
			tree.insertionMode.processStartTag(name, attributes);
		} else {
			tree.framesetOk = false;
			tree.reconstructActiveFormattingElements();
			tree.insertElement(name, attributes);
		}
	};

	modes.inBody.startTagAppletMarqueeObject = function(name, attributes) {
		tree.reconstructActiveFormattingElements();
		tree.insertElement(name, attributes);
		tree.activeFormattingElements.push(Marker);
		tree.framesetOk = false;
	};

	modes.inBody.endTagAppletMarqueeObject = function(name) {
		if (!tree.openElements.inScope(name)) {
			tree.parseError("unexpected-end-tag", {name: name});
		} else {
			tree.generateImpliedEndTags();
			if (tree.currentStackItem().localName != name) {
				tree.parseError('end-tag-too-early', {name: name});
			}
			tree.openElements.popUntilPopped(name);
			tree.clearActiveFormattingElements();
		}
	};

	modes.inBody.startTagXmp = function(name, attributes) {
		if (tree.openElements.inButtonScope('p'))
			this.processEndTag('p');
		tree.reconstructActiveFormattingElements();
		tree.processGenericRawTextStartTag(name, attributes);
		tree.framesetOk = false;
	};

	modes.inBody.startTagTable = function(name, attributes) {
		if (tree.compatMode !== "quirks")
			if (tree.openElements.inButtonScope('p'))
				this.processEndTag('p');
		tree.insertElement(name, attributes);
		tree.setInsertionMode('inTable');
		tree.framesetOk = false;
	};

	modes.inBody.startTagVoidFormatting = function(name, attributes) {
		tree.reconstructActiveFormattingElements();
		tree.insertSelfClosingElement(name, attributes);
		tree.framesetOk = false;
	};

	modes.inBody.startTagParamSourceTrack = function(name, attributes) {
		tree.insertSelfClosingElement(name, attributes);
	};

	modes.inBody.startTagHr = function(name, attributes) {
		if (tree.openElements.inButtonScope('p'))
			this.endTagP('p');
		tree.insertSelfClosingElement(name, attributes);
		tree.framesetOk = false;
	};

	modes.inBody.startTagImage = function(name, attributes) {
		// No, really...
		tree.parseError('unexpected-start-tag-treated-as', {originalName: 'image', newName: 'img'});
		this.processStartTag('img', attributes);
	};

	modes.inBody.startTagInput = function(name, attributes) {
		var currentFramesetOk = tree.framesetOk;
		this.startTagVoidFormatting(name, attributes);
		for (var key in attributes) {
			// input type=hidden doesn't change framesetOk
			if (attributes[key].nodeName == 'type') {
				if (attributes[key].nodeValue.toLowerCase() == 'hidden')
					tree.framesetOk = currentFramesetOk;
				break;
			}
		}
	};

	modes.inBody.startTagIsindex = function(name, attributes) {
		tree.parseError('deprecated-tag', {name: 'isindex'});
		tree.selfClosingFlagAcknowledged = true;
		if (tree.form)
			return;
		var formAttributes = [];
		var inputAttributes = [];
		var prompt = "This is a searchable index. Enter search keywords: ";
		for (var key in attributes) {
			switch (attributes[key].nodeName) {
				case 'action':
					formAttributes.push({nodeName: 'action',
						nodeValue: attributes[key].nodeValue});
					break;
				case 'prompt':
					prompt = attributes[key].nodeValue;
					break;
				case 'name':
					break;
				default:
					inputAttributes.push({nodeName: attributes[key].nodeName,
						nodeValue: attributes[key].nodeValue});
			}
		}
		inputAttributes.push({nodeName: 'name', nodeValue: 'isindex'});
		this.processStartTag('form', formAttributes);
		this.processStartTag('hr');
		this.processStartTag('label');
		this.processCharacters(new CharacterBuffer(prompt));
		this.processStartTag('input', inputAttributes);
		this.processEndTag('label');
		this.processStartTag('hr');
		this.processEndTag('form');
	};

	modes.inBody.startTagTextarea = function(name, attributes) {
		// XXX Form element pointer checking here as well...
		tree.insertElement(name, attributes);
		tree.tokenizer.setState(Tokenizer.RCDATA);
		tree.originalInsertionMode = tree.insertionModeName;
		tree.shouldSkipLeadingNewline = true;
		tree.framesetOk = false;
		tree.setInsertionMode('text');
	};

	modes.inBody.startTagIFrame = function(name, attributes) {
		tree.framesetOk = false;
		this.startTagRawText(name, attributes);
	};

	modes.inBody.startTagRawText = function(name, attributes) {
		tree.processGenericRawTextStartTag(name, attributes);
	};

	modes.inBody.startTagSelect = function(name, attributes) {
		tree.reconstructActiveFormattingElements();
		tree.insertElement(name, attributes);
		tree.framesetOk = false;
		var insertionModeName = tree.insertionModeName;
		if (insertionModeName == 'inTable' ||
			insertionModeName == 'inCaption' ||
			insertionModeName == 'inColumnGroup' ||
			insertionModeName == 'inTableBody' ||
			insertionModeName == 'inRow' ||
			insertionModeName == 'inCell') {
			tree.setInsertionMode('inSelectInTable');
		} else {
			tree.setInsertionMode('inSelect');
		}
	};

	modes.inBody.startTagMisplaced = function(name, attributes) {
		tree.parseError('unexpected-start-tag-ignored', {name: name});
	};

	modes.inBody.endTagMisplaced = function(name) {
		// This handles elements with end tags in other insertion modes.
		tree.parseError("unexpected-end-tag", {name: name});
	};

	modes.inBody.endTagBr = function(name) {
		tree.parseError("unexpected-end-tag-treated-as", {originalName: "br", newName: "br element"});
		tree.reconstructActiveFormattingElements();
		tree.insertElement(name, []);
		tree.popElement();
	};

	modes.inBody.startTagOptionOptgroup = function(name, attributes) {
		if (tree.currentStackItem().localName == 'option')
			tree.popElement();
		tree.reconstructActiveFormattingElements();
		tree.insertElement(name, attributes);
	};

	modes.inBody.startTagOther = function(name, attributes) {
		tree.reconstructActiveFormattingElements();
		tree.insertElement(name, attributes);
	};

	modes.inBody.endTagOther = function(name) {
		var node;
		for (var i = tree.openElements.length - 1; i > 0; i--) {
			node = tree.openElements.item(i);
			if (node.localName == name) {
				tree.generateImpliedEndTags(name);
				if (tree.currentStackItem().localName != name)
					tree.parseError('unexpected-end-tag', {name: name});
				// todo optimize
				tree.openElements.remove_openElements_until(function(x) {return x === node;});
				break;
			}
			if (node.isSpecial()) {
				tree.parseError('unexpected-end-tag', {name: name});
				break;
			}
		}
	};

	modes.inBody.startTagMath = function(name, attributes, selfClosing) {
		tree.reconstructActiveFormattingElements();
		attributes = tree.adjustMathMLAttributes(attributes);
		attributes = tree.adjustForeignAttributes(attributes);
		tree.insertForeignElement(name, attributes, "http://www.w3.org/1998/Math/MathML", selfClosing);
		// Need to get the parse error right for the case where the token
		// has a namespace not equal to the xmlns attribute
	};

	modes.inBody.startTagSVG = function(name, attributes, selfClosing) {
		tree.reconstructActiveFormattingElements();
		attributes = tree.adjustSVGAttributes(attributes);
		attributes = tree.adjustForeignAttributes(attributes);
		tree.insertForeignElement(name, attributes, "http://www.w3.org/2000/svg", selfClosing);
		// Need to get the parse error right for the case where the token
		// has a namespace not equal to the xmlns attribute
	};

	modes.inBody.endTagP = function(name) {
		if (!tree.openElements.inButtonScope('p')) {
			tree.parseError('unexpected-end-tag', {name: 'p'});
			this.startTagCloseP('p', []);
			this.endTagP('p');
		} else {
			tree.generateImpliedEndTags('p');
			if (tree.currentStackItem().localName != 'p')
				tree.parseError('unexpected-implied-end-tag', {name: 'p'});
			tree.openElements.popUntilPopped(name);
		}
	};

	modes.inBody.endTagBody = function(name) {
		if (!tree.openElements.inScope('body')) {
			tree.parseError('unexpected-end-tag', {name: name});
			return;
		}

		/// @todo Emit parse error on end tags other than the ones listed in http://www.w3.org/TR/html5/tree-construction.html#parsing-main-inbody
		// ['dd', 'dt', 'li', 'optgroup', 'option', 'p', 'rp', 'rt', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'body', 'html']
		if (tree.currentStackItem().localName != 'body') {
			tree.parseError('expected-one-end-tag-but-got-another', {
				expectedName: tree.currentStackItem().localName,
				gotName: name
			});
		}
		tree.setInsertionMode('afterBody');
	};

	modes.inBody.endTagHtml = function(name) {
		if (!tree.openElements.inScope('body')) {
			tree.parseError('unexpected-end-tag', {name: name});
			return;
		}

		/// @todo Emit parse error on end tags other than the ones listed in http://www.w3.org/TR/html5/tree-construction.html#parsing-main-inbody
		// ['dd', 'dt', 'li', 'optgroup', 'option', 'p', 'rp', 'rt', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'body', 'html']
		if (tree.currentStackItem().localName != 'body') {
			tree.parseError('expected-one-end-tag-but-got-another', {
				expectedName: tree.currentStackItem().localName,
				gotName: name
			});
		}
		tree.setInsertionMode('afterBody');
		tree.insertionMode.processEndTag(name);
	};

	modes.inBody.endTagBlock = function(name) {
		if (!tree.openElements.inScope(name)) {
			tree.parseError('unexpected-end-tag', {name: name});
		} else {
			tree.generateImpliedEndTags();
			if (tree.currentStackItem().localName != name) {
				tree.parseError('end-tag-too-early', {name: name});
			}
			tree.openElements.popUntilPopped(name);
		}
	};

	modes.inBody.endTagForm = function(name)  {
		var node = tree.form;
		tree.form = null;
		if (!node || !tree.openElements.inScope(name)) {
			tree.parseError('unexpected-end-tag', {name: name});
		} else {
			tree.generateImpliedEndTags();
			if (tree.currentStackItem() != node) {
				tree.parseError('end-tag-too-early-ignored', {name: 'form'});
			}
			tree.openElements.remove(node);
		}
	};

	modes.inBody.endTagListItem = function(name) {
		if (!tree.openElements.inListItemScope(name)) {
			tree.parseError('unexpected-end-tag', {name: name});
		} else {
			tree.generateImpliedEndTags(name);
			if (tree.currentStackItem().localName != name)
				tree.parseError('end-tag-too-early', {name: name});
			tree.openElements.popUntilPopped(name);
		}
	};

	modes.inBody.endTagHeading = function(name) {
		if (!tree.openElements.hasNumberedHeaderElementInScope()) {
			tree.parseError('unexpected-end-tag', {name: name});
			return;
		}
		tree.generateImpliedEndTags();
		if (tree.currentStackItem().localName != name)
			tree.parseError('end-tag-too-early', {name: name});

		tree.openElements.remove_openElements_until(function(e) {
			return e.isNumberedHeader();
		});
	};

	modes.inBody.endTagFormatting = function(name, attributes) {
		if (!tree.adoptionAgencyEndTag(name))
			this.endTagOther(name, attributes);
	};

	modes.inCaption = Object.create(modes.base);

	modes.inCaption.start_tag_handlers = {
		html: 'startTagHtml',
		caption: 'startTagTableElement',
		col: 'startTagTableElement',
		colgroup: 'startTagTableElement',
		tbody: 'startTagTableElement',
		td: 'startTagTableElement',
		tfoot: 'startTagTableElement',
		thead: 'startTagTableElement',
		tr: 'startTagTableElement',
		'-default': 'startTagOther'
	};

	modes.inCaption.end_tag_handlers = {
		caption: 'endTagCaption',
		table: 'endTagTable',
		body: 'endTagIgnore',
		col: 'endTagIgnore',
		colgroup: 'endTagIgnore',
		html: 'endTagIgnore',
		tbody: 'endTagIgnore',
		td: 'endTagIgnore',
		tfood: 'endTagIgnore',
		thead: 'endTagIgnore',
		tr: 'endTagIgnore',
		'-default': 'endTagOther'
	};

	modes.inCaption.processCharacters = function(data) {
		modes.inBody.processCharacters(data);
	};

	modes.inCaption.startTagTableElement = function(name, attributes) {
		tree.parseError('unexpected-end-tag', {name: name});
		var ignoreEndTag = !tree.openElements.inTableScope('caption');
		tree.insertionMode.processEndTag('caption');
		if (!ignoreEndTag) tree.insertionMode.processStartTag(name, attributes);
	};

	modes.inCaption.startTagOther = function(name, attributes, selfClosing) {
		modes.inBody.processStartTag(name, attributes, selfClosing);
	};

	modes.inCaption.endTagCaption = function(name) {
		if (!tree.openElements.inTableScope('caption')) {
			// context case
			assert.ok(tree.context);
			tree.parseError('unexpected-end-tag', {name: name});
		} else {
			// AT this code is quite similar to endTagTable in inTable
			tree.generateImpliedEndTags();
			if (tree.currentStackItem().localName != 'caption') {
				// @todo this is confusing for implied end tag
				tree.parseError('expected-one-end-tag-but-got-another', {
					gotName: "caption",
					expectedName: tree.currentStackItem().localName
				});
			}
			tree.openElements.popUntilPopped('caption');
			tree.clearActiveFormattingElements();
			tree.setInsertionMode('inTable');
		}
	};

	modes.inCaption.endTagTable = function(name) {
		tree.parseError("unexpected-end-table-in-caption");
		var ignoreEndTag = !tree.openElements.inTableScope('caption');
		tree.insertionMode.processEndTag('caption');
		if (!ignoreEndTag) tree.insertionMode.processEndTag(name);
	};

	modes.inCaption.endTagIgnore = function(name) {
		tree.parseError('unexpected-end-tag', {name: name});
	};

	modes.inCaption.endTagOther = function(name) {
		modes.inBody.processEndTag(name);
	};

	modes.inCell = Object.create(modes.base);

	modes.inCell.start_tag_handlers = {
		html: 'startTagHtml',
		caption: 'startTagTableOther',
		col: 'startTagTableOther',
		colgroup: 'startTagTableOther',
		tbody: 'startTagTableOther',
		td: 'startTagTableOther',
		tfoot: 'startTagTableOther',
		th: 'startTagTableOther',
		thead: 'startTagTableOther',
		tr: 'startTagTableOther',
		'-default': 'startTagOther'
	};

	modes.inCell.end_tag_handlers = {
		td: 'endTagTableCell',
		th: 'endTagTableCell',
		body: 'endTagIgnore',
		caption: 'endTagIgnore',
		col: 'endTagIgnore',
		colgroup: 'endTagIgnore',
		html: 'endTagIgnore',
		table: 'endTagImply',
		tbody: 'endTagImply',
		tfoot: 'endTagImply',
		thead: 'endTagImply',
		tr: 'endTagImply',
		'-default': 'endTagOther'
	};

	modes.inCell.processCharacters = function(data) {
		modes.inBody.processCharacters(data);
	};

	modes.inCell.startTagTableOther = function(name, attributes, selfClosing) {
		if (tree.openElements.inTableScope('td') || tree.openElements.inTableScope('th')) {
			this.closeCell();
			tree.insertionMode.processStartTag(name, attributes, selfClosing);
		} else {
			// context case
			tree.parseError('unexpected-start-tag', {name: name});
		}
	};

	modes.inCell.startTagOther = function(name, attributes, selfClosing) {
		modes.inBody.processStartTag(name, attributes, selfClosing);
	};

	modes.inCell.endTagTableCell = function(name) {
		if (tree.openElements.inTableScope(name)) {
			tree.generateImpliedEndTags(name);
			if (tree.currentStackItem().localName != name.toLowerCase()) {
				tree.parseError('unexpected-cell-end-tag', {name: name});
				tree.openElements.popUntilPopped(name);
			} else {
				tree.popElement();
			}
			tree.clearActiveFormattingElements();
			tree.setInsertionMode('inRow');
		} else {
			tree.parseError('unexpected-end-tag', {name: name});
		}
	};

	modes.inCell.endTagIgnore = function(name) {
		tree.parseError('unexpected-end-tag', {name: name});
	};

	modes.inCell.endTagImply = function(name) {
		if (tree.openElements.inTableScope(name)) {
			this.closeCell();
			tree.insertionMode.processEndTag(name);
		} else {
			// sometimes context case
			tree.parseError('unexpected-end-tag', {name: name});
		}
	};

	modes.inCell.endTagOther = function(name) {
		modes.inBody.processEndTag(name);
	};

	modes.inCell.closeCell = function() {
		if (tree.openElements.inTableScope('td')) {
			this.endTagTableCell('td');
		} else if (tree.openElements.inTableScope('th')) {
			this.endTagTableCell('th');
		}
	};


	modes.inColumnGroup = Object.create(modes.base);

	modes.inColumnGroup.start_tag_handlers = {
		html: 'startTagHtml',
		col: 'startTagCol',
		'-default': 'startTagOther'
	};

	modes.inColumnGroup.end_tag_handlers = {
		colgroup: 'endTagColgroup',
		col: 'endTagCol',
		'-default': 'endTagOther'
	};

	modes.inColumnGroup.ignoreEndTagColgroup = function() {
		return tree.currentStackItem().localName == 'html';
	};

	modes.inColumnGroup.processCharacters = function(buffer) {
		var leadingWhitespace = buffer.takeLeadingWhitespace();
		if (leadingWhitespace)
			tree.insertText(leadingWhitespace);
		if (!buffer.length)
			return;
		var ignoreEndTag = this.ignoreEndTagColgroup();
		this.endTagColgroup('colgroup');
		if (!ignoreEndTag) tree.insertionMode.processCharacters(buffer);
	};

	modes.inColumnGroup.startTagCol = function(name, attributes) {
		tree.insertSelfClosingElement(name, attributes);
	};

	modes.inColumnGroup.startTagOther = function(name, attributes, selfClosing) {
		var ignoreEndTag = this.ignoreEndTagColgroup();
		this.endTagColgroup('colgroup');
		if (!ignoreEndTag) tree.insertionMode.processStartTag(name, attributes, selfClosing);
	};

	modes.inColumnGroup.endTagColgroup = function(name) {
		if (this.ignoreEndTagColgroup()) {
			// context case
			assert.ok(tree.context);
			tree.parseError('unexpected-end-tag', {name: name});
		} else {
			tree.popElement();
			tree.setInsertionMode('inTable');
		}
	};

	modes.inColumnGroup.endTagCol = function(name) {
		tree.parseError("no-end-tag", {name: 'col'});
	};

	modes.inColumnGroup.endTagOther = function(name) {
		var ignoreEndTag = this.ignoreEndTagColgroup();
		this.endTagColgroup('colgroup');
		if (!ignoreEndTag) tree.insertionMode.processEndTag(name) ;
	};

	modes.inForeignContent = Object.create(modes.base);

	modes.inForeignContent.processStartTag = function(name, attributes, selfClosing) {
		if (['b', 'big', 'blockquote', 'body', 'br', 'center', 'code', 'dd', 'div', 'dl', 'dt', 'em', 'embed', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'hr', 'i', 'img', 'li', 'listing', 'menu', 'meta', 'nobr', 'ol', 'p', 'pre', 'ruby', 's', 'small', 'span', 'strong', 'strike', 'sub', 'sup', 'table', 'tt', 'u', 'ul', 'var'].indexOf(name) != -1
				|| (name == 'font' && attributes.some(function(attr){ return ['color', 'face', 'size'].indexOf(attr.nodeName) >= 0 }))) {
			tree.parseError('unexpected-html-element-in-foreign-content', {name: name});
			while (tree.currentStackItem().isForeign()
				&& !tree.currentStackItem().isHtmlIntegrationPoint()
				&& !tree.currentStackItem().isMathMLTextIntegrationPoint()) {
				tree.openElements.pop();
			}
			tree.insertionMode.processStartTag(name, attributes, selfClosing);
			return;
		}
		if (tree.currentStackItem().namespaceURI == "http://www.w3.org/1998/Math/MathML") {
			attributes = tree.adjustMathMLAttributes(attributes);
		}
		if (tree.currentStackItem().namespaceURI == "http://www.w3.org/2000/svg") {
			name = tree.adjustSVGTagNameCase(name);
			attributes = tree.adjustSVGAttributes(attributes);
		}
		attributes = tree.adjustForeignAttributes(attributes);
		tree.insertForeignElement(name, attributes, tree.currentStackItem().namespaceURI, selfClosing);
	};

	modes.inForeignContent.processEndTag = function(name) {
		var node = tree.currentStackItem();
		var index = tree.openElements.length - 1;
		if (node.localName.toLowerCase() != name)
			tree.parseError("unexpected-end-tag", {name: name});

		while (true) {
			if (index === 0)
				break;
			if (node.localName.toLowerCase() == name) {
				while (tree.openElements.pop() != node);
				break;
			}
			index -= 1;
			node = tree.openElements.item(index);
			if (node.isForeign()) {
				continue;
			} else {
				tree.insertionMode.processEndTag(name);
				break;
			}
		}
	};

	modes.inForeignContent.processCharacters = function(buffer) {
		var characters = buffer.takeRemaining();
		characters = characters.replace(/\u0000/g, function(match, index){
			// @todo position
			tree.parseError('invalid-codepoint');
			return '\uFFFD';
		});
		if (tree.framesetOk && !isAllWhitespaceOrReplacementCharacters(characters))
			tree.framesetOk = false;
		tree.insertText(characters);
	};

	modes.inHeadNoscript = Object.create(modes.base);

	modes.inHeadNoscript.start_tag_handlers = {
		html: 'startTagHtml',
		basefont: 'startTagBasefontBgsoundLinkMetaNoframesStyle',
		bgsound: 'startTagBasefontBgsoundLinkMetaNoframesStyle',
		link: 'startTagBasefontBgsoundLinkMetaNoframesStyle',
		meta: 'startTagBasefontBgsoundLinkMetaNoframesStyle',
		noframes: 'startTagBasefontBgsoundLinkMetaNoframesStyle',
		style: 'startTagBasefontBgsoundLinkMetaNoframesStyle',
		head: 'startTagHeadNoscript',
		noscript: 'startTagHeadNoscript',
		"-default": 'startTagOther'
	};

	modes.inHeadNoscript.end_tag_handlers = {
		noscript: 'endTagNoscript',
		br: 'endTagBr',
		'-default': 'endTagOther'
	};

	modes.inHeadNoscript.processCharacters = function(buffer) {
		var leadingWhitespace = buffer.takeLeadingWhitespace();
		if (leadingWhitespace)
			tree.insertText(leadingWhitespace);
		if (!buffer.length)
			return;
		// FIXME error message
		tree.parseError("unexpected-char-in-frameset");
		this.anythingElse();
		tree.insertionMode.processCharacters(buffer);
	};

	modes.inHeadNoscript.processComment = function(data) {
		modes.inHead.processComment(data);
	};

	modes.inHeadNoscript.startTagBasefontBgsoundLinkMetaNoframesStyle = function(name, attributes) {
		modes.inHead.processStartTag(name, attributes);
	};

	modes.inHeadNoscript.startTagHeadNoscript = function(name, attributes) {
		// FIXME error message
		tree.parseError("unexpected-start-tag-in-frameset", {name: name});
	};

	modes.inHeadNoscript.startTagOther = function(name, attributes) {
		// FIXME error message
		tree.parseError("unexpected-start-tag-in-frameset", {name: name});
		this.anythingElse();
		tree.insertionMode.processStartTag(name, attributes);
	};

	modes.inHeadNoscript.endTagBr = function(name, attributes) {
		// FIXME error message
		tree.parseError("unexpected-end-tag-in-frameset", {name: name});
		this.anythingElse();
		tree.insertionMode.processEndTag(name, attributes);
	};

	modes.inHeadNoscript.endTagNoscript = function(name, attributes) {
		tree.popElement();
		tree.setInsertionMode('inHead');
	};

	modes.inHeadNoscript.endTagOther = function(name, attributes) {
		// FIXME error message
		tree.parseError("unexpected-end-tag-in-frameset", {name: name});
	};

	modes.inHeadNoscript.anythingElse = function() {
		tree.popElement();
		tree.setInsertionMode('inHead');
	};


	modes.inFrameset = Object.create(modes.base);

	modes.inFrameset.start_tag_handlers = {
		html: 'startTagHtml',
		frameset: 'startTagFrameset',
		frame: 'startTagFrame',
		noframes: 'startTagNoframes',
		"-default": 'startTagOther'
	};

	modes.inFrameset.end_tag_handlers = {
		frameset: 'endTagFrameset',
		noframes: 'endTagNoframes',
		'-default': 'endTagOther'
	};

	modes.inFrameset.processCharacters = function(data) {
		tree.parseError("unexpected-char-in-frameset");
	};

	modes.inFrameset.startTagFrameset = function(name, attributes) {
		tree.insertElement(name, attributes);
	};

	modes.inFrameset.startTagFrame = function(name, attributes) {
		tree.insertSelfClosingElement(name, attributes);
	};

	modes.inFrameset.startTagNoframes = function(name, attributes) {
		modes.inBody.processStartTag(name, attributes);
	};

	modes.inFrameset.startTagOther = function(name, attributes) {
		tree.parseError("unexpected-start-tag-in-frameset", {name: name});
	};

	modes.inFrameset.endTagFrameset = function(name, attributes) {
		if (tree.currentStackItem().localName == 'html') {
			// context case
			tree.parseError("unexpected-frameset-in-frameset-innerhtml");
		} else {
			tree.popElement();
		}

		if (!tree.context && tree.currentStackItem().localName != 'frameset') {
			// If we're not in context mode an the current node is not a "frameset" element (anymore) then switch
			tree.setInsertionMode('afterFrameset');
		}
	};

	modes.inFrameset.endTagNoframes = function(name) {
		modes.inBody.processEndTag(name);
	};

	modes.inFrameset.endTagOther = function(name) {
		tree.parseError("unexpected-end-tag-in-frameset", {name: name});
	};

	modes.inTable = Object.create(modes.base);

	modes.inTable.start_tag_handlers = {
		html: 'startTagHtml',
		caption: 'startTagCaption',
		colgroup: 'startTagColgroup',
		col: 'startTagCol',
		table: 'startTagTable',
		tbody: 'startTagRowGroup',
		tfoot: 'startTagRowGroup',
		thead: 'startTagRowGroup',
		td: 'startTagImplyTbody',
		th: 'startTagImplyTbody',
		tr: 'startTagImplyTbody',
		style: 'startTagStyleScript',
		script: 'startTagStyleScript',
		input: 'startTagInput',
		form: 'startTagForm',
		'-default': 'startTagOther'
	};

	modes.inTable.end_tag_handlers = {
		table: 'endTagTable',
		body: 'endTagIgnore',
		caption: 'endTagIgnore',
		col: 'endTagIgnore',
		colgroup: 'endTagIgnore',
		html: 'endTagIgnore',
		tbody: 'endTagIgnore',
		td: 'endTagIgnore',
		tfoot: 'endTagIgnore',
		th: 'endTagIgnore',
		thead: 'endTagIgnore',
		tr: 'endTagIgnore',
		'-default': 'endTagOther'
	};

	modes.inTable.processCharacters =  function(data) {
		if (tree.currentStackItem().isFosterParenting()) {
			var originalInsertionMode = tree.insertionModeName;
			tree.setInsertionMode('inTableText');
			tree.originalInsertionMode = originalInsertionMode;
			tree.insertionMode.processCharacters(data);
		} else {
			tree.redirectAttachToFosterParent = true;
			modes.inBody.processCharacters(data);
			tree.redirectAttachToFosterParent = false;
		}
	};

	modes.inTable.startTagCaption = function(name, attributes) {
		tree.openElements.popUntilTableScopeMarker();
		tree.activeFormattingElements.push(Marker);
		tree.insertElement(name, attributes);
		tree.setInsertionMode('inCaption');
	};

	modes.inTable.startTagColgroup = function(name, attributes) {
		tree.openElements.popUntilTableScopeMarker();
		tree.insertElement(name, attributes);
		tree.setInsertionMode('inColumnGroup');
	};

	modes.inTable.startTagCol = function(name, attributes) {
		this.startTagColgroup('colgroup', []);
		tree.insertionMode.processStartTag(name, attributes);
	};

	modes.inTable.startTagRowGroup = function(name, attributes) {
		tree.openElements.popUntilTableScopeMarker();
		tree.insertElement(name, attributes);
		tree.setInsertionMode('inTableBody');
	};

	modes.inTable.startTagImplyTbody = function(name, attributes) {
		this.startTagRowGroup('tbody', []);
		tree.insertionMode.processStartTag(name, attributes);
	};

	modes.inTable.startTagTable = function(name, attributes) {
		tree.parseError("unexpected-start-tag-implies-end-tag",
				{startName: "table", endName: "table"});
		tree.insertionMode.processEndTag('table');
		if (!tree.context) tree.insertionMode.processStartTag(name, attributes);
	};

	modes.inTable.startTagStyleScript = function(name, attributes) {
		modes.inHead.processStartTag(name, attributes);
	};

	modes.inTable.startTagInput = function(name, attributes) {
		for (var key in attributes) {
			if (attributes[key].nodeName.toLowerCase() == 'type') {
				if (attributes[key].nodeValue.toLowerCase() == 'hidden') {
					tree.parseError("unexpected-hidden-input-in-table");
					tree.insertElement(name, attributes);
					// XXX associate with form
					tree.openElements.pop();
					return;
				}
				break;
			}
		}
		this.startTagOther(name, attributes);
	};

	modes.inTable.startTagForm = function(name, attributes) {
		tree.parseError("unexpected-form-in-table");
		if (!tree.form) {
			tree.insertElement(name, attributes);
			tree.form = tree.currentStackItem();
			tree.openElements.pop();
		}
	};

	modes.inTable.startTagOther = function(name, attributes, selfClosing) {
		tree.parseError("unexpected-start-tag-implies-table-voodoo", {name: name});
		tree.redirectAttachToFosterParent = true;
		modes.inBody.processStartTag(name, attributes, selfClosing);
		tree.redirectAttachToFosterParent = false;
	};

	modes.inTable.endTagTable = function(name) {
		if (tree.openElements.inTableScope(name)) {
			tree.generateImpliedEndTags();
			if (tree.currentStackItem().localName != name) {
				tree.parseError("end-tag-too-early-named", {gotName: 'table', expectedName: tree.currentStackItem().localName});
			}

			tree.openElements.popUntilPopped('table');
			tree.resetInsertionMode();
		} else {
			assert.ok(tree.context);
			tree.parseError('unexpected-end-tag', {name: name});
		}
	};

	modes.inTable.endTagIgnore = function(name) {
		tree.parseError("unexpected-end-tag", {name: name});
	};

	modes.inTable.endTagOther = function(name) {
		tree.parseError("unexpected-end-tag-implies-table-voodoo", {name: name});
		// Make all the special element rearranging voodoo kick in
		tree.redirectAttachToFosterParent = true;
		// Process the end tag in the "in body" mode
		modes.inBody.processEndTag(name);
		tree.redirectAttachToFosterParent = false;
	};

	modes.inTableText = Object.create(modes.base);

	modes.inTableText.flushCharacters = function() {
		var characters = tree.pendingTableCharacters.join('');
		if (!isAllWhitespace(characters)) {
			tree.redirectAttachToFosterParent = true;
			tree.reconstructActiveFormattingElements();
			tree.insertText(characters);
			tree.framesetOk = false;
			tree.redirectAttachToFosterParent = false;
		} else {
			tree.insertText(characters);
		}
		tree.pendingTableCharacters = [];
	};

	modes.inTableText.processComment = function(data) {
		this.flushCharacters();
		tree.setInsertionMode(tree.originalInsertionMode);
		tree.insertionMode.processComment(data);
	};

	modes.inTableText.processEOF = function(data) {
		this.flushCharacters();
		tree.setInsertionMode(tree.originalInsertionMode);
		tree.insertionMode.processEOF();
	};

	modes.inTableText.processCharacters = function(buffer) {
		var characters = buffer.takeRemaining();
		characters = characters.replace(/\u0000/g, function(match, index){
			// @todo position
			tree.parseError("invalid-codepoint");
			return '';
		});
		if (!characters)
			return;
		tree.pendingTableCharacters.push(characters);
	};

	modes.inTableText.processStartTag = function(name, attributes, selfClosing) {
		this.flushCharacters();
		tree.setInsertionMode(tree.originalInsertionMode);
		tree.insertionMode.processStartTag(name, attributes, selfClosing);
	};

	modes.inTableText.processEndTag = function(name, attributes) {
		this.flushCharacters();
		tree.setInsertionMode(tree.originalInsertionMode);
		tree.insertionMode.processEndTag(name, attributes);
	};

	modes.inTableBody = Object.create(modes.base);

	modes.inTableBody.start_tag_handlers = {
		html: 'startTagHtml',
		tr: 'startTagTr',
		td: 'startTagTableCell',
		th: 'startTagTableCell',
		caption: 'startTagTableOther',
		col: 'startTagTableOther',
		colgroup: 'startTagTableOther',
		tbody: 'startTagTableOther',
		tfoot: 'startTagTableOther',
		thead: 'startTagTableOther',
		'-default': 'startTagOther'
	};

	modes.inTableBody.end_tag_handlers = {
		table: 'endTagTable',
		tbody: 'endTagTableRowGroup',
		tfoot: 'endTagTableRowGroup',
		thead: 'endTagTableRowGroup',
		body: 'endTagIgnore',
		caption: 'endTagIgnore',
		col: 'endTagIgnore',
		colgroup: 'endTagIgnore',
		html: 'endTagIgnore',
		td: 'endTagIgnore',
		th: 'endTagIgnore',
		tr: 'endTagIgnore',
		'-default': 'endTagOther'
	};

	modes.inTableBody.processCharacters = function(data) {
		modes.inTable.processCharacters(data);
	};

	modes.inTableBody.startTagTr = function(name, attributes) {
		tree.openElements.popUntilTableBodyScopeMarker();
		tree.insertElement(name, attributes);
		tree.setInsertionMode('inRow');
	};

	modes.inTableBody.startTagTableCell = function(name, attributes) {
		tree.parseError("unexpected-cell-in-table-body", {name: name});
		this.startTagTr('tr', []);
		tree.insertionMode.processStartTag(name, attributes);
	};

	modes.inTableBody.startTagTableOther = function(name, attributes) {
		// XXX any ideas on how to share this with endTagTable
		if (tree.openElements.inTableScope('tbody') ||  tree.openElements.inTableScope('thead') || tree.openElements.inTableScope('tfoot')) {
			tree.openElements.popUntilTableBodyScopeMarker();
			this.endTagTableRowGroup(tree.currentStackItem().localName);
			tree.insertionMode.processStartTag(name, attributes);
		} else {
			// context case
			tree.parseError('unexpected-start-tag', {name: name});
		}
	};

	modes.inTableBody.startTagOther = function(name, attributes) {
		modes.inTable.processStartTag(name, attributes);
	};

	modes.inTableBody.endTagTableRowGroup = function(name) {
		if (tree.openElements.inTableScope(name)) {
			tree.openElements.popUntilTableBodyScopeMarker();
			tree.popElement();
			tree.setInsertionMode('inTable');
		} else {
			tree.parseError('unexpected-end-tag-in-table-body', {name: name});
		}
	};

	modes.inTableBody.endTagTable = function(name) {
		if (tree.openElements.inTableScope('tbody') ||  tree.openElements.inTableScope('thead') || tree.openElements.inTableScope('tfoot')) {
			tree.openElements.popUntilTableBodyScopeMarker();
			this.endTagTableRowGroup(tree.currentStackItem().localName);
			tree.insertionMode.processEndTag(name);
		} else {
			// context case
			tree.parseError('unexpected-end-tag', {name: name});
		}
	};

	modes.inTableBody.endTagIgnore = function(name) {
		tree.parseError("unexpected-end-tag-in-table-body", {name: name});
	};

	modes.inTableBody.endTagOther = function(name) {
		modes.inTable.processEndTag(name);
	};

	modes.inSelect = Object.create(modes.base);

	modes.inSelect.start_tag_handlers = {
		html: 'startTagHtml',
		option: 'startTagOption',
		optgroup: 'startTagOptgroup',
		select: 'startTagSelect',
		input: 'startTagInput',
		keygen: 'startTagInput',
		textarea: 'startTagInput',
		script: 'startTagScript',
		'-default': 'startTagOther'
	};

	modes.inSelect.end_tag_handlers = {
		option: 'endTagOption',
		optgroup: 'endTagOptgroup',
		select: 'endTagSelect',
		caption: 'endTagTableElements',
		table: 'endTagTableElements',
		tbody: 'endTagTableElements',
		tfoot: 'endTagTableElements',
		thead: 'endTagTableElements',
		tr: 'endTagTableElements',
		td: 'endTagTableElements',
		th: 'endTagTableElements',
		'-default': 'endTagOther'
	};

	modes.inSelect.processCharacters = function(buffer) {
		var data = buffer.takeRemaining();
		data = data.replace(/\u0000/g, function(match, index){
			// @todo position
			tree.parseError("invalid-codepoint");
			return '';
		});
		if (!data)
			return;
		tree.insertText(data);
	};

	modes.inSelect.startTagOption = function(name, attributes) {
		// we need to imply </option> if <option> is the current node
		if (tree.currentStackItem().localName == 'option')
			tree.popElement();
		tree.insertElement(name, attributes);
	};

	modes.inSelect.startTagOptgroup = function(name, attributes) {
		if (tree.currentStackItem().localName == 'option')
			tree.popElement();
		if (tree.currentStackItem().localName == 'optgroup')
			tree.popElement();
		tree.insertElement(name, attributes);
	};

	modes.inSelect.endTagOption = function(name) {
		if (tree.currentStackItem().localName !== 'option') {
			tree.parseError('unexpected-end-tag-in-select', {name: name});
			return;
		}
		tree.popElement();
	};

	modes.inSelect.endTagOptgroup = function(name) {
		// </optgroup> implicitly closes <option>
		if (tree.currentStackItem().localName == 'option' && tree.openElements.item(tree.openElements.length - 2).localName == 'optgroup') {
			tree.popElement();
		}

		// it also closes </optgroup>
		if (tree.currentStackItem().localName == 'optgroup') {
			tree.popElement();
		} else {
			// But nothing else
			tree.parseError('unexpected-end-tag-in-select', {name: 'optgroup'});
		}
	};

	modes.inSelect.startTagSelect = function(name) {
		tree.parseError("unexpected-select-in-select");
		this.endTagSelect('select');
	};

	modes.inSelect.endTagSelect = function(name) {
		if (tree.openElements.inTableScope('select')) {
			tree.openElements.popUntilPopped('select');
			tree.resetInsertionMode();
		} else {
			// context case
			tree.parseError('unexpected-end-tag', {name: name});
		}
	};

	modes.inSelect.startTagInput = function(name, attributes) {
		tree.parseError("unexpected-input-in-select");
		if (tree.openElements.inSelectScope('select')) {
			this.endTagSelect('select');
			tree.insertionMode.processStartTag(name, attributes);
		}
	};

	modes.inSelect.startTagScript = function(name, attributes) {
		modes.inHead.processStartTag(name, attributes);
	};

	modes.inSelect.endTagTableElements = function(name) {
		tree.parseError('unexpected-end-tag-in-select', {name: name});
		if (tree.openElements.inTableScope(name)) {
			this.endTagSelect('select');
			tree.insertionMode.processEndTag(name);
		}
	};

	modes.inSelect.startTagOther = function(name, attributes) {
		tree.parseError("unexpected-start-tag-in-select", {name: name});
	};

	modes.inSelect.endTagOther = function(name) {
		tree.parseError('unexpected-end-tag-in-select', {name: name});
	};

	modes.inSelectInTable = Object.create(modes.base);

	modes.inSelectInTable.start_tag_handlers = {
		caption: 'startTagTable',
		table: 'startTagTable',
		tbody: 'startTagTable',
		tfoot: 'startTagTable',
		thead: 'startTagTable',
		tr: 'startTagTable',
		td: 'startTagTable',
		th: 'startTagTable',
		'-default': 'startTagOther'
	};

	modes.inSelectInTable.end_tag_handlers = {
		caption: 'endTagTable',
		table: 'endTagTable',
		tbody: 'endTagTable',
		tfoot: 'endTagTable',
		thead: 'endTagTable',
		tr: 'endTagTable',
		td: 'endTagTable',
		th: 'endTagTable',
		'-default': 'endTagOther'
	};

	modes.inSelectInTable.processCharacters = function(data) {
		modes.inSelect.processCharacters(data);
	};

	modes.inSelectInTable.startTagTable = function(name, attributes) {
		tree.parseError("unexpected-table-element-start-tag-in-select-in-table", {name: name});
		this.endTagOther("select");
		tree.insertionMode.processStartTag(name, attributes);
	};

	modes.inSelectInTable.startTagOther = function(name, attributes, selfClosing) {
		modes.inSelect.processStartTag(name, attributes, selfClosing);
	};

	modes.inSelectInTable.endTagTable = function(name) {
		tree.parseError("unexpected-table-element-end-tag-in-select-in-table", {name: name});
		if (tree.openElements.inTableScope(name)) {
			this.endTagOther("select");
			tree.insertionMode.processEndTag(name);
		}
	};

	modes.inSelectInTable.endTagOther = function(name) {
		modes.inSelect.processEndTag(name);
	};

	modes.inRow = Object.create(modes.base);

	modes.inRow.start_tag_handlers = {
		html: 'startTagHtml',
		td: 'startTagTableCell',
		th: 'startTagTableCell',
		caption: 'startTagTableOther',
		col: 'startTagTableOther',
		colgroup: 'startTagTableOther',
		tbody: 'startTagTableOther',
		tfoot: 'startTagTableOther',
		thead: 'startTagTableOther',
		tr: 'startTagTableOther',
		'-default': 'startTagOther'
	};

	modes.inRow.end_tag_handlers = {
		tr: 'endTagTr',
		table: 'endTagTable',
		tbody: 'endTagTableRowGroup',
		tfoot: 'endTagTableRowGroup',
		thead: 'endTagTableRowGroup',
		body: 'endTagIgnore',
		caption: 'endTagIgnore',
		col: 'endTagIgnore',
		colgroup: 'endTagIgnore',
		html: 'endTagIgnore',
		td: 'endTagIgnore',
		th: 'endTagIgnore',
		'-default': 'endTagOther'
	};

	modes.inRow.processCharacters = function(data) {
		modes.inTable.processCharacters(data);
	};

	modes.inRow.startTagTableCell = function(name, attributes) {
		tree.openElements.popUntilTableRowScopeMarker();
		tree.insertElement(name, attributes);
		tree.setInsertionMode('inCell');
		tree.activeFormattingElements.push(Marker);
	};

	modes.inRow.startTagTableOther = function(name, attributes) {
		var ignoreEndTag = this.ignoreEndTagTr();
		this.endTagTr('tr');
		// XXX how are we sure it's always ignored in the context case?
		if (!ignoreEndTag) tree.insertionMode.processStartTag(name, attributes);
	};

	modes.inRow.startTagOther = function(name, attributes, selfClosing) {
		modes.inTable.processStartTag(name, attributes, selfClosing);
	};

	modes.inRow.endTagTr = function(name) {
		if (this.ignoreEndTagTr()) {
			assert.ok(tree.context);
			tree.parseError('unexpected-end-tag', {name: name});
		} else {
			tree.openElements.popUntilTableRowScopeMarker();
			tree.popElement();
			tree.setInsertionMode('inTableBody');
		}
	};

	modes.inRow.endTagTable = function(name) {
		var ignoreEndTag = this.ignoreEndTagTr();
		this.endTagTr('tr');
		// Reprocess the current tag if the tr end tag was not ignored
		// XXX how are we sure it's always ignored in the context case?
		if (!ignoreEndTag) tree.insertionMode.processEndTag(name);
	};

	modes.inRow.endTagTableRowGroup = function(name) {
		if (tree.openElements.inTableScope(name)) {
			this.endTagTr('tr');
			tree.insertionMode.processEndTag(name);
		} else {
			// context case
			tree.parseError('unexpected-end-tag', {name: name});
		}
	};

	modes.inRow.endTagIgnore = function(name) {
		tree.parseError("unexpected-end-tag-in-table-row", {name: name});
	};

	modes.inRow.endTagOther = function(name) {
		modes.inTable.processEndTag(name);
	};

	modes.inRow.ignoreEndTagTr = function() {
		return !tree.openElements.inTableScope('tr');
	};

	modes.afterAfterFrameset = Object.create(modes.base);

	modes.afterAfterFrameset.start_tag_handlers = {
		html: 'startTagHtml',
		noframes: 'startTagNoFrames',
		'-default': 'startTagOther'
	};

	modes.afterAfterFrameset.processEOF = function() {};

	modes.afterAfterFrameset.processComment = function(data) {
		tree.insertComment(data, tree.document);
	};

	modes.afterAfterFrameset.processCharacters = function(buffer) {
		var characters = buffer.takeRemaining();
		var whitespace = "";
		for (var i = 0; i < characters.length; i++) {
			var ch = characters[i];
			if (isWhitespace(ch))
				whitespace += ch;
		}
		if (whitespace) {
			tree.reconstructActiveFormattingElements();
			tree.insertText(whitespace);
		}
		if (whitespace.length < characters.length)
			tree.parseError('expected-eof-but-got-char');
	};

	modes.afterAfterFrameset.startTagNoFrames = function(name, attributes) {
		modes.inHead.processStartTag(name, attributes);
	};

	modes.afterAfterFrameset.startTagOther = function(name, attributes, selfClosing) {
		tree.parseError('expected-eof-but-got-start-tag', {name: name});
	};

	modes.afterAfterFrameset.processEndTag = function(name, attributes) {
		tree.parseError('expected-eof-but-got-end-tag', {name: name});
	};

	modes.text = Object.create(modes.base);

	modes.text.start_tag_handlers = {
		'-default': 'startTagOther'
	};

	modes.text.end_tag_handlers = {
		script: 'endTagScript',
		'-default': 'endTagOther'
	};

	modes.text.processCharacters = function(buffer) {
		if (tree.shouldSkipLeadingNewline) {
			tree.shouldSkipLeadingNewline = false;
			buffer.skipAtMostOneLeadingNewline();
		}
		var data = buffer.takeRemaining();
		if (!data)
			return;
		tree.insertText(data);
	};

	modes.text.processEOF = function() {
		tree.parseError("expected-named-closing-tag-but-got-eof",
			{name: tree.currentStackItem().localName});
		tree.openElements.pop();
		tree.setInsertionMode(tree.originalInsertionMode);
		tree.insertionMode.processEOF();
	};

	modes.text.startTagOther = function(name) {
		throw "Tried to process start tag " + name + " in RCDATA/RAWTEXT mode";
	};

	modes.text.endTagScript = function(name) {
		var node = tree.openElements.pop();
		assert.ok(node.localName == 'script');
		tree.setInsertionMode(tree.originalInsertionMode);
	};

	modes.text.endTagOther = function(name) {
		tree.openElements.pop();
		tree.setInsertionMode(tree.originalInsertionMode);
	};
}

TreeBuilder.prototype.setInsertionMode = function(name) {
	this.insertionMode = this.insertionModes[name];
	this.insertionModeName = name;
};

/**
 * Adoption agency algorithm (http://www.whatwg.org/specs/web-apps/current-work/multipage/tree-construction.html#adoption-agency-algorithm)
 * @param {String} name A tag name subject for which the algorithm is being run
 * @return {Boolean} Returns false if the algorithm was aborted
 */
TreeBuilder.prototype.adoptionAgencyEndTag = function(name) {
	var outerIterationLimit = 8;
	var innerIterationLimit = 3;
	var formattingElement;

	function isActiveFormattingElement(el) {
		return el === formattingElement;
	}

	var outerLoopCounter = 0;

	while (outerLoopCounter++ < outerIterationLimit) {
		// 4.
		formattingElement = this.elementInActiveFormattingElements(name);

		if (!formattingElement || (this.openElements.contains(formattingElement) && !this.openElements.inScope(formattingElement.localName))) {
			this.parseError('adoption-agency-1.1', {name: name});
			return false;
		}
		if (!this.openElements.contains(formattingElement)) {
			this.parseError('adoption-agency-1.2', {name: name});
			this.removeElementFromActiveFormattingElements(formattingElement);
			return true;
		}
		if (!this.openElements.inScope(formattingElement.localName)) {
			this.parseError('adoption-agency-4.4', {name: name});
		}

		if (formattingElement != this.currentStackItem()) {
			this.parseError('adoption-agency-1.3', {name: name});
		}

		// Start of the adoption agency algorithm proper
		// todo ElementStack
		var furthestBlock = this.openElements.furthestBlockForFormattingElement(formattingElement.node);

		if (!furthestBlock) {
			this.openElements.remove_openElements_until(isActiveFormattingElement);
			this.removeElementFromActiveFormattingElements(formattingElement);
			return true;
		}

		var afeIndex = this.openElements.elements.indexOf(formattingElement);
		var commonAncestor = this.openElements.item(afeIndex - 1);

		var bookmark = this.activeFormattingElements.indexOf(formattingElement);

		var node = furthestBlock;
		var lastNode = furthestBlock;
		var index = this.openElements.elements.indexOf(node);

		var innerLoopCounter = 0;
		while (innerLoopCounter++ < innerIterationLimit) {
			index -= 1;
			node = this.openElements.item(index);
			if (this.activeFormattingElements.indexOf(node) < 0) {
				this.openElements.elements.splice(index, 1);
				continue;
			}
			if (node == formattingElement)
				break;

			if (lastNode == furthestBlock)
				bookmark = this.activeFormattingElements.indexOf(node) + 1;

			var clone = this.createElement(node.namespaceURI, node.localName, node.attributes);
			var newNode = new StackItem(node.namespaceURI, node.localName, node.attributes, clone);

			this.activeFormattingElements[this.activeFormattingElements.indexOf(node)] = newNode;
			this.openElements.elements[this.openElements.elements.indexOf(node)] = newNode;

			node = newNode;
			this.detachFromParent(lastNode.node);
			this.attachNode(lastNode.node, node.node);
			lastNode = node;
		}

		this.detachFromParent(lastNode.node);
		if (commonAncestor.isFosterParenting()) {
			this.insertIntoFosterParent(lastNode.node);
		} else {
			this.attachNode(lastNode.node, commonAncestor.node);
		}

		var clone = this.createElement("http://www.w3.org/1999/xhtml", formattingElement.localName, formattingElement.attributes);
		var formattingClone = new StackItem(formattingElement.namespaceURI, formattingElement.localName, formattingElement.attributes, clone);

		this.reparentChildren(furthestBlock.node, clone);
		this.attachNode(clone, furthestBlock.node);

		this.removeElementFromActiveFormattingElements(formattingElement);
		this.activeFormattingElements.splice(Math.min(bookmark, this.activeFormattingElements.length), 0, formattingClone);

		this.openElements.remove(formattingElement);
		this.openElements.elements.splice(this.openElements.elements.indexOf(furthestBlock) + 1, 0, formattingClone);
	}

	return true;
};

TreeBuilder.prototype.start = function() {
	throw "Not mplemented";
};

TreeBuilder.prototype.startTokenization = function(tokenizer) {
	this.tokenizer = tokenizer;
	this.compatMode = "no quirks";
	this.originalInsertionMode = "initial";
	this.framesetOk = true;
	this.openElements = new ElementStack();
	this.activeFormattingElements = [];
	this.start();
	if (this.context) {
		switch(this.context) {
		case 'title':
		case 'textarea':
			this.tokenizer.setState(Tokenizer.RCDATA);
			break;
		case 'style':
		case 'xmp':
		case 'iframe':
		case 'noembed':
		case 'noframes':
			this.tokenizer.setState(Tokenizer.RAWTEXT);
			break;
		case 'script':
			this.tokenizer.setState(Tokenizer.SCRIPT_DATA);
			break;
		case 'noscript':
			if (this.scriptingEnabled)
				this.tokenizer.setState(Tokenizer.RAWTEXT);
			break;
		case 'plaintext':
			this.tokenizer.setState(Tokenizer.PLAINTEXT);
			break;
		}
		this.insertHtmlElement();
		this.resetInsertionMode();
		// todo form pointer
	} else {
		this.setInsertionMode('initial');
	}
};

TreeBuilder.prototype.processToken = function(token) {
	this.selfClosingFlagAcknowledged = false;

	var currentNode = this.openElements.top || null;
	var insertionMode;
	if (!currentNode || !currentNode.isForeign() ||
		(currentNode.isMathMLTextIntegrationPoint() &&
			((token.type == 'StartTag' &&
					!(token.name in {mglyph:0, malignmark:0})) ||
				(token.type === 'Characters'))
		) ||
		(currentNode.namespaceURI == "http://www.w3.org/1998/Math/MathML" &&
			currentNode.localName == 'annotation-xml' &&
			token.type == 'StartTag' && token.name == 'svg'
		) ||
		(currentNode.isHtmlIntegrationPoint() &&
			token.type in {StartTag:0, Characters:0}
		) ||
		token.type == 'EOF'
	) {
		insertionMode = this.insertionMode;
	} else {
		insertionMode = this.insertionModes.inForeignContent;
	}
	switch(token.type) {
	case 'Characters':
		var buffer = new CharacterBuffer(token.data);
		insertionMode.processCharacters(buffer);
		break;
	case 'Comment':
		insertionMode.processComment(token.data);
		break;
	case 'StartTag':
		insertionMode.processStartTag(token.name, token.data, token.selfClosing);
		break;
	case 'EndTag':
		insertionMode.processEndTag(token.name);
		break;
	case 'Doctype':
		insertionMode.processDoctype(token.name, token.publicId, token.systemId, token.forceQuirks);
		break;
	case 'EOF':
		insertionMode.processEOF();
		break;
	}
};

/**
 *
 * @return {Boolean}
 */
TreeBuilder.prototype.isCdataSectionAllowed = function() {
	return this.openElements.length > 0 && this.currentStackItem().isForeign();
};

/**
 *
 * @return {Boolean}
 */
TreeBuilder.prototype.isSelfClosingFlagAcknowledged = function() {
	return this.selfClosingFlagAcknowledged;
};

TreeBuilder.prototype.createElement = function(namespaceURI, localName, attributes) {
	throw new Error("Not implemented");
};

TreeBuilder.prototype.attachNode = function(child, parent) {
	throw new Error("Not implemented");
};

TreeBuilder.prototype.attachNodeToFosterParent = function(child, table, stackParent) {
	throw new Error("Not implemented");
};

TreeBuilder.prototype.detachFromParent = function(node) {
	throw new Error("Not implemented");
};

TreeBuilder.prototype.addAttributesToElement = function(element, attributes) {
	throw new Error("Not implemented");
};

TreeBuilder.prototype.insertHtmlElement = function(attributes) {
	var root = this.createElement("http://www.w3.org/1999/xhtml", 'html', attributes);
	this.attachNode(root, this.document);
	this.openElements.pushHtmlElement(new StackItem("http://www.w3.org/1999/xhtml", 'html', attributes, root));
	return root;
};

TreeBuilder.prototype.insertHeadElement = function(attributes) {
	var element = this.createElement("http://www.w3.org/1999/xhtml", "head", attributes);
	this.head = new StackItem("http://www.w3.org/1999/xhtml", "head", attributes, element);
	this.attachNode(element, this.openElements.top.node);
	this.openElements.pushHeadElement(this.head);
	return element;
};

TreeBuilder.prototype.insertBodyElement = function(attributes) {
	var element = this.createElement("http://www.w3.org/1999/xhtml", "body", attributes);
	this.attachNode(element, this.openElements.top.node);
	this.openElements.pushBodyElement(new StackItem("http://www.w3.org/1999/xhtml", "body", attributes, element));
	return element;
};

TreeBuilder.prototype.insertIntoFosterParent = function(node) {
	var tableIndex = this.openElements.findIndex('table');
	var tableElement = this.openElements.item(tableIndex).node;
	if (tableIndex === 0)
		return this.attachNode(node, tableElement);
	this.attachNodeToFosterParent(node, tableElement, this.openElements.item(tableIndex - 1).node);
};

TreeBuilder.prototype.insertElement = function(name, attributes, namespaceURI, selfClosing) {
	if (!namespaceURI)
		namespaceURI = "http://www.w3.org/1999/xhtml";
	var element = this.createElement(namespaceURI, name, attributes);
	if (this.shouldFosterParent())
		this.insertIntoFosterParent(element);
	else
		this.attachNode(element, this.openElements.top.node);
	if (!selfClosing)
		this.openElements.push(new StackItem(namespaceURI, name, attributes, element));
};

TreeBuilder.prototype.insertFormattingElement = function(name, attributes) {
	this.insertElement(name, attributes, "http://www.w3.org/1999/xhtml");
	this.appendElementToActiveFormattingElements(this.currentStackItem());
};

TreeBuilder.prototype.insertSelfClosingElement = function(name, attributes) {
	this.selfClosingFlagAcknowledged = true;
	this.insertElement(name, attributes, "http://www.w3.org/1999/xhtml", true);
};

TreeBuilder.prototype.insertForeignElement = function(name, attributes, namespaceURI, selfClosing) {
	if (selfClosing)
		this.selfClosingFlagAcknowledged = true;
	this.insertElement(name, attributes, namespaceURI, selfClosing);
};

TreeBuilder.prototype.insertComment = function(data, parent) {
	throw new Error("Not implemented");
};

TreeBuilder.prototype.insertDoctype = function(name, publicId, systemId) {
	throw new Error("Not implemented");
};

TreeBuilder.prototype.insertText = function(data) {
	throw new Error("Not implemented");
};

/**
 * Returns topmost open element
 * @return {StackItem}
 */
TreeBuilder.prototype.currentStackItem = function() {
	return this.openElements.top;
};

/**
 * Populates current open element
 * @return {StackItem}
 */
TreeBuilder.prototype.popElement = function() {
	return this.openElements.pop();
};

/**
 * Returns true if redirect is required and current open element causes foster parenting
 * @return {Boolean}
 */
TreeBuilder.prototype.shouldFosterParent = function() {
	return this.redirectAttachToFosterParent && this.currentStackItem().isFosterParenting();
};

/**
 * Implements http://www.whatwg.org/specs/web-apps/current-work/multipage/tree-construction.html#closing-elements-that-have-implied-end-tags
 * @param {String} [exclude] Ignore specific tag name
 */
TreeBuilder.prototype.generateImpliedEndTags = function(exclude) {
	// FIXME get rid of the recursion
	var name = this.openElements.top.localName;
	if (['dd', 'dt', 'li', 'option', 'optgroup', 'p', 'rp', 'rt'].indexOf(name) != -1 && name != exclude) {
		this.popElement();
		this.generateImpliedEndTags(exclude);
	}
};

/**
 * Performs http://www.whatwg.org/specs/web-apps/current-work/multipage/parsing.html#reconstruct-the-active-formatting-elements
 */
TreeBuilder.prototype.reconstructActiveFormattingElements = function() {
	// Within this algorithm the order of steps decribed in the specification
	// is not quite the same as the order of steps in the code. It should still
	// do the same though.

	// Step 1: stop if there's nothing to do
	if (this.activeFormattingElements.length === 0)
		return;

	// Step 2 and 3: start with the last element
	var i = this.activeFormattingElements.length - 1;
	var entry = this.activeFormattingElements[i];
	if (entry == Marker || this.openElements.contains(entry))
		return;

	while (entry != Marker && !this.openElements.contains(entry)) {
		i -= 1;
		entry = this.activeFormattingElements[i];
		if (!entry)
			break;
	}

	while (true) {
		i += 1;
		entry = this.activeFormattingElements[i];
		this.insertElement(entry.localName, entry.attributes);
		var element = this.currentStackItem();
		this.activeFormattingElements[i] = element;
		if (element == this.activeFormattingElements[this.activeFormattingElements.length -1])
			break;
	}

};

/**
 *
 * @param {StackItem} item
 */
TreeBuilder.prototype.ensureNoahsArkCondition = function(item) {
	var kNoahsArkCapacity = 3;
	if (this.activeFormattingElements.length < kNoahsArkCapacity)
		return;
	var candidates = [];
	var newItemAttributeCount = item.attributes.length;
	for (var i = this.activeFormattingElements.length - 1; i >= 0; i--) {
		var candidate = this.activeFormattingElements[i];
		if (candidate === Marker)
			break;
		if (item.localName !== candidate.localName || item.namespaceURI !== candidate.namespaceURI)
			continue;
		if (candidate.attributes.length != newItemAttributeCount)
			continue;
		candidates.push(candidate);
	}
	if (candidates.length < kNoahsArkCapacity)
		return;

	var remainingCandidates = [];
	var attributes = item.attributes;
	for (var i = 0; i < attributes.length; i++) {
		var attribute = attributes[i];

		for (var j = 0; j < candidates.length; j++) {
			var candidate = candidates[j];
			var candidateAttribute = getAttribute(candidate, attribute.nodeName);
			if (candidateAttribute && candidateAttribute.nodeValue === attribute.nodeValue)
				remainingCandidates.push(candidate);
		}
		if (remainingCandidates.length < kNoahsArkCapacity)
			return;
		candidates = remainingCandidates;
		remainingCandidates = [];
	}
	// Inductively, we shouldn't spin this loop very many times. It's possible,
	// however, that we wil spin the loop more than once because of how the
	// formatting element list gets permuted.
	for (var i = kNoahsArkCapacity - 1; i < candidates.length; i++)
		this.removeElementFromActiveFormattingElements(candidates[i]);
};

/**
 *
 * @param {StackItem} item
 */
TreeBuilder.prototype.appendElementToActiveFormattingElements = function(item) {
	this.ensureNoahsArkCondition(item);
	this.activeFormattingElements.push(item);
};

/**
 *
 * @param {StackItem} item
 */
TreeBuilder.prototype.removeElementFromActiveFormattingElements = function(item) {
	var index = this.activeFormattingElements.indexOf(item);
	if (index >= 0)
		this.activeFormattingElements.splice(index, 1);
};

TreeBuilder.prototype.elementInActiveFormattingElements = function(name) {
	var els = this.activeFormattingElements;
	for (var i = els.length - 1; i >= 0; i--) {
		if (els[i] == Marker) break;
		if (els[i].localName == name) return els[i];
	}
	return false;
};

TreeBuilder.prototype.clearActiveFormattingElements = function() {
    while (!(this.activeFormattingElements.length === 0 || this.activeFormattingElements.pop() == Marker));
};

TreeBuilder.prototype.reparentChildren = function(oldParent, newParent) {
	throw new Error("Not implemented");
};

/**
 *
 * @param {String} context A context element name for fragment parsing
 */
TreeBuilder.prototype.setFragmentContext = function(context) {
	// Steps 4.2-4.6 of the HTML5 Fragment Case parsing algorithm:
	// http://www.whatwg.org/specs/web-apps/current-work/multipage/the-end.html#fragment-case
	// For efficiency, we skip step 4.2 ("Let root be a new html element with no attributes")
	// and instead use the DocumentFragment as a root node.
	//m_tree.openElements()->pushRootNode(HTMLStackItem::create(fragment, HTMLStackItem::ItemForDocumentFragmentNode));
	this.context = context;
};

/**
 *
 * @param {String} code
 * @param {Object} [args]
 */
TreeBuilder.prototype.parseError = function(code, args) {
	// FIXME: this.errors.push([this.tokenizer.position, code, data]);
	if (!this.errorHandler)
		return;
	var message = formatMessage(messages[code], args);
	this.errorHandler.error(message, this.tokenizer._inputStream.location(), code);
};

/**
 * Resets the insertion mode (http://www.whatwg.org/specs/web-apps/current-work/multipage/parsing.html#reset-the-insertion-mode-appropriately)
 */
TreeBuilder.prototype.resetInsertionMode = function() {
	var last = false;
	var node = null;
	for (var i = this.openElements.length - 1; i >= 0; i--) {
		node = this.openElements.item(i);
		if (i === 0) {
			assert.ok(this.context);
			last = true;
			node = new StackItem("http://www.w3.org/1999/xhtml", this.context, [], null);
		}

		if (node.namespaceURI === "http://www.w3.org/1999/xhtml") {
			// TODO template tag
			if (node.localName === 'select')
				// FIXME handle inSelectInTable
				return this.setInsertionMode('inSelect');
			if (node.localName === 'td' || node.localName === 'th')
				return this.setInsertionMode('inCell');
			if (node.localName === 'tr')
				return this.setInsertionMode('inRow');
			if (node.localName === 'tbody' || node.localName === 'thead' || node.localName === 'tfoot')
				return this.setInsertionMode('inTableBody');
			if (node.localName === 'caption')
				return this.setInsertionMode('inCaption');
			if (node.localName === 'colgroup')
				return this.setInsertionMode('inColumnGroup');
			if (node.localName === 'table')
				return this.setInsertionMode('inTable');
			if (node.localName === 'head' && !last)
				return this.setInsertionMode('inHead');
			if (node.localName === 'body')
				return this.setInsertionMode('inBody');
			if (node.localName === 'frameset')
				return this.setInsertionMode('inFrameset');
			if (node.localName === 'html')
				if (!this.openElements.headElement)
					return this.setInsertionMode('beforeHead');
				else
					return this.setInsertionMode('afterHead');
		}

		if (last)
			return this.setInsertionMode('inBody');
	}
};

TreeBuilder.prototype.processGenericRCDATAStartTag = function(name, attributes) {
	this.insertElement(name, attributes);
	this.tokenizer.setState(Tokenizer.RCDATA);
	this.originalInsertionMode = this.insertionModeName;
	this.setInsertionMode('text');
};

TreeBuilder.prototype.processGenericRawTextStartTag = function(name, attributes) {
	this.insertElement(name, attributes);
	this.tokenizer.setState(Tokenizer.RAWTEXT);
	this.originalInsertionMode = this.insertionModeName;
	this.setInsertionMode('text');
};

TreeBuilder.prototype.adjustMathMLAttributes = function(attributes) {
	attributes.forEach(function(a) {
		a.namespaceURI = "http://www.w3.org/1998/Math/MathML";
		if (constants.MATHMLAttributeMap[a.nodeName])
			a.nodeName = constants.MATHMLAttributeMap[a.nodeName];
	});
	return attributes;
};

TreeBuilder.prototype.adjustSVGTagNameCase = function(name) {
	return constants.SVGTagMap[name] || name;
};

TreeBuilder.prototype.adjustSVGAttributes = function(attributes) {
	attributes.forEach(function(a) {
		a.namespaceURI = "http://www.w3.org/2000/svg";
		if (constants.SVGAttributeMap[a.nodeName])
			a.nodeName = constants.SVGAttributeMap[a.nodeName];
	});
	return attributes;
};

TreeBuilder.prototype.adjustForeignAttributes = function(attributes) {
	for (var i = 0; i < attributes.length; i++) {
		var attribute = attributes[i];
		var adjusted = constants.ForeignAttributeMap[attribute.nodeName];
		if (adjusted) {
			attribute.nodeName = adjusted.localName;
			attribute.prefix = adjusted.prefix;
			attribute.namespaceURI = adjusted.namespaceURI;
		}
	}
	return attributes;
};

function formatMessage(format, args) {
	return format.replace(new RegExp('{[0-9a-z-]+}', 'gi'), function(match) {
		return args[match.slice(1, -1)] || match;
	});
}

exports.TreeBuilder = TreeBuilder;

},
{"./ElementStack":1,"./StackItem":4,"./Tokenizer":5,"./constants":7,"./messages.json":8,"assert":13,"events":16}],
7:[function(_dereq_,module,exports){
exports.SVGTagMap = {
	"altglyph": "altGlyph",
	"altglyphdef": "altGlyphDef",
	"altglyphitem": "altGlyphItem",
	"animatecolor": "animateColor",
	"animatemotion": "animateMotion",
	"animatetransform": "animateTransform",
	"clippath": "clipPath",
	"feblend": "feBlend",
	"fecolormatrix": "feColorMatrix",
	"fecomponenttransfer": "feComponentTransfer",
	"fecomposite": "feComposite",
	"feconvolvematrix": "feConvolveMatrix",
	"fediffuselighting": "feDiffuseLighting",
	"fedisplacementmap": "feDisplacementMap",
	"fedistantlight": "feDistantLight",
	"feflood": "feFlood",
	"fefunca": "feFuncA",
	"fefuncb": "feFuncB",
	"fefuncg": "feFuncG",
	"fefuncr": "feFuncR",
	"fegaussianblur": "feGaussianBlur",
	"feimage": "feImage",
	"femerge": "feMerge",
	"femergenode": "feMergeNode",
	"femorphology": "feMorphology",
	"feoffset": "feOffset",
	"fepointlight": "fePointLight",
	"fespecularlighting": "feSpecularLighting",
	"fespotlight": "feSpotLight",
	"fetile": "feTile",
	"feturbulence": "feTurbulence",
	"foreignobject": "foreignObject",
	"glyphref": "glyphRef",
	"lineargradient": "linearGradient",
	"radialgradient": "radialGradient",
	"textpath": "textPath"
};

exports.MATHMLAttributeMap = {
	definitionurl: 'definitionURL'
};

exports.SVGAttributeMap = {
	attributename:	'attributeName',
	attributetype:	'attributeType',
	basefrequency:	'baseFrequency',
	baseprofile:	'baseProfile',
	calcmode:	'calcMode',
	clippathunits:	'clipPathUnits',
	contentscripttype:	'contentScriptType',
	contentstyletype:	'contentStyleType',
	diffuseconstant:	'diffuseConstant',
	edgemode:	'edgeMode',
	externalresourcesrequired:	'externalResourcesRequired',
	filterres:	'filterRes',
	filterunits:	'filterUnits',
	glyphref:	'glyphRef',
	gradienttransform:	'gradientTransform',
	gradientunits:	'gradientUnits',
	kernelmatrix:	'kernelMatrix',
	kernelunitlength:	'kernelUnitLength',
	keypoints:	'keyPoints',
	keysplines:	'keySplines',
	keytimes:	'keyTimes',
	lengthadjust:	'lengthAdjust',
	limitingconeangle:	'limitingConeAngle',
	markerheight:	'markerHeight',
	markerunits:	'markerUnits',
	markerwidth:	'markerWidth',
	maskcontentunits:	'maskContentUnits',
	maskunits:	'maskUnits',
	numoctaves:	'numOctaves',
	pathlength:	'pathLength',
	patterncontentunits:	'patternContentUnits',
	patterntransform:	'patternTransform',
	patternunits:	'patternUnits',
	pointsatx:	'pointsAtX',
	pointsaty:	'pointsAtY',
	pointsatz:	'pointsAtZ',
	preservealpha:	'preserveAlpha',
	preserveaspectratio:	'preserveAspectRatio',
	primitiveunits:	'primitiveUnits',
	refx:	'refX',
	refy:	'refY',
	repeatcount:	'repeatCount',
	repeatdur:	'repeatDur',
	requiredextensions:	'requiredExtensions',
	requiredfeatures:	'requiredFeatures',
	specularconstant:	'specularConstant',
	specularexponent:	'specularExponent',
	spreadmethod:	'spreadMethod',
	startoffset:	'startOffset',
	stddeviation:	'stdDeviation',
	stitchtiles:	'stitchTiles',
	surfacescale:	'surfaceScale',
	systemlanguage:	'systemLanguage',
	tablevalues:	'tableValues',
	targetx:	'targetX',
	targety:	'targetY',
	textlength:	'textLength',
	viewbox:	'viewBox',
	viewtarget:	'viewTarget',
	xchannelselector:	'xChannelSelector',
	ychannelselector:	'yChannelSelector',
	zoomandpan:	'zoomAndPan'
};

exports.ForeignAttributeMap = {
	"xlink:actuate": {prefix: "xlink", localName: "actuate", namespaceURI: "http://www.w3.org/1999/xlink"},
	"xlink:arcrole": {prefix: "xlink", localName: "arcrole", namespaceURI: "http://www.w3.org/1999/xlink"},
	"xlink:href": {prefix: "xlink", localName: "href", namespaceURI: "http://www.w3.org/1999/xlink"},
	"xlink:role": {prefix: "xlink", localName: "role", namespaceURI: "http://www.w3.org/1999/xlink"},
	"xlink:show": {prefix: "xlink", localName: "show", namespaceURI: "http://www.w3.org/1999/xlink"},
	"xlink:title": {prefix: "xlink", localName: "title", namespaceURI: "http://www.w3.org/1999/xlink"},
	"xlink:type": {prefix: "xlink", localName: "title", namespaceURI: "http://www.w3.org/1999/xlink"},
	"xml:base": {prefix: "xml", localName: "base", namespaceURI: "http://www.w3.org/XML/1998/namespace"},
	"xml:lang": {prefix: "xml", localName: "lang", namespaceURI: "http://www.w3.org/XML/1998/namespace"},
	"xml:space": {prefix: "xml", localName: "space", namespaceURI: "http://www.w3.org/XML/1998/namespace"},
	"xmlns": {prefix: null, localName: "xmlns", namespaceURI: "http://www.w3.org/2000/xmlns/"},
	"xmlns:xlink": {prefix: "xmlns", localName: "xlink", namespaceURI: "http://www.w3.org/2000/xmlns/"},
};
},
{}],
8:[function(_dereq_,module,exports){
module.exports={
	"null-character":
		"Null character in input stream, replaced with U+FFFD.",
	"invalid-codepoint":
		"Invalid codepoint in stream",
	"incorrectly-placed-solidus":
		"Solidus (/) incorrectly placed in tag.",
	"incorrect-cr-newline-entity":
		"Incorrect CR newline entity, replaced with LF.",
	"illegal-windows-1252-entity":
		"Entity used with illegal number (windows-1252 reference).",
	"cant-convert-numeric-entity":
		"Numeric entity couldn't be converted to character (codepoint U+{charAsInt}).",
	"invalid-numeric-entity-replaced":
		"Numeric entity represents an illegal codepoint. Expanded to the C1 controls range.",
	"numeric-entity-without-semicolon":
		"Numeric entity didn't end with ';'.",
	"expected-numeric-entity-but-got-eof":
		"Numeric entity expected. Got end of file instead.",
	"expected-numeric-entity":
		"Numeric entity expected but none found.",
	"named-entity-without-semicolon":
		"Named entity didn't end with ';'.",
	"expected-named-entity":
		"Named entity expected. Got none.",
	"attributes-in-end-tag":
		"End tag contains unexpected attributes.",
	"self-closing-flag-on-end-tag":
		"End tag contains unexpected self-closing flag.",
	"bare-less-than-sign-at-eof":
		"End of file after <.",
	"expected-tag-name-but-got-right-bracket":
		"Expected tag name. Got '>' instead.",
	"expected-tag-name-but-got-question-mark":
		"Expected tag name. Got '?' instead. (HTML doesn't support processing instructions.)",
	"expected-tag-name":
		"Expected tag name. Got something else instead.",
	"expected-closing-tag-but-got-right-bracket":
		"Expected closing tag. Got '>' instead. Ignoring '</>'.",
	"expected-closing-tag-but-got-eof":
		"Expected closing tag. Unexpected end of file.",
	"expected-closing-tag-but-got-char":
		"Expected closing tag. Unexpected character '{data}' found.",
	"eof-in-tag-name":
		"Unexpected end of file in the tag name.",
	"expected-attribute-name-but-got-eof":
		"Unexpected end of file. Expected attribute name instead.",
	"eof-in-attribute-name":
		"Unexpected end of file in attribute name.",
	"invalid-character-in-attribute-name":
		"Invalid character in attribute name.",
	"duplicate-attribute":
		"Dropped duplicate attribute '{name}' on tag.",
	"expected-end-of-tag-but-got-eof":
		"Unexpected end of file. Expected = or end of tag.",
	"expected-attribute-value-but-got-eof":
		"Unexpected end of file. Expected attribute value.",
	"expected-attribute-value-but-got-right-bracket":
		"Expected attribute value. Got '>' instead.",
	"unexpected-character-in-unquoted-attribute-value":
		"Unexpected character in unquoted attribute",
	"invalid-character-after-attribute-name":
		"Unexpected character after attribute name.",
	"unexpected-character-after-attribute-value":
		"Unexpected character after attribute value.",
	"eof-in-attribute-value-double-quote":
		"Unexpected end of file in attribute value (\").",
	"eof-in-attribute-value-single-quote":
		"Unexpected end of file in attribute value (').",
	"eof-in-attribute-value-no-quotes":
		"Unexpected end of file in attribute value.",
	"eof-after-attribute-value":
		"Unexpected end of file after attribute value.",
	"unexpected-eof-after-solidus-in-tag":
		"Unexpected end of file in tag. Expected >.",
	"unexpected-character-after-solidus-in-tag":
		"Unexpected character after / in tag. Expected >.",
	"expected-dashes-or-doctype":
		"Expected '--' or 'DOCTYPE'. Not found.",
	"unexpected-bang-after-double-dash-in-comment":
		"Unexpected ! after -- in comment.",
	"incorrect-comment":
		"Incorrect comment.",
	"eof-in-comment":
		"Unexpected end of file in comment.",
	"eof-in-comment-end-dash":
		"Unexpected end of file in comment (-).",
	"unexpected-dash-after-double-dash-in-comment":
		"Unexpected '-' after '--' found in comment.",
	"eof-in-comment-double-dash":
		"Unexpected end of file in comment (--).",
	"eof-in-comment-end-bang-state":
		"Unexpected end of file in comment.",
	"unexpected-char-in-comment":
		"Unexpected character in comment found.",
	"need-space-after-doctype":
		"No space after literal string 'DOCTYPE'.",
	"expected-doctype-name-but-got-right-bracket":
		"Unexpected > character. Expected DOCTYPE name.",
	"expected-doctype-name-but-got-eof":
		"Unexpected end of file. Expected DOCTYPE name.",
	"eof-in-doctype-name":
		"Unexpected end of file in DOCTYPE name.",
	"eof-in-doctype":
		"Unexpected end of file in DOCTYPE.",
	"expected-space-or-right-bracket-in-doctype":
		"Expected space or '>'. Got '{data}'.",
	"unexpected-end-of-doctype":
		"Unexpected end of DOCTYPE.",
	"unexpected-char-in-doctype":
		"Unexpected character in DOCTYPE.",
	"eof-in-bogus-doctype":
		"Unexpected end of file in bogus doctype.",
	"eof-in-innerhtml":
		"Unexpected EOF in inner html mode.",
	"unexpected-doctype":
		"Unexpected DOCTYPE. Ignored.",
	"non-html-root":
		"html needs to be the first start tag.",
	"expected-doctype-but-got-eof":
		"Unexpected End of file. Expected DOCTYPE.",
	"unknown-doctype":
		"Erroneous DOCTYPE. Expected <!DOCTYPE html>.",
	"quirky-doctype":
		"Quirky doctype. Expected <!DOCTYPE html>.",
	"almost-standards-doctype":
		"Almost standards mode doctype. Expected <!DOCTYPE html>.",
	"obsolete-doctype":
		"Obsolete doctype. Expected <!DOCTYPE html>.",
	"expected-doctype-but-got-chars":
		"Non-space characters found without seeing a doctype first. Expected e.g. <!DOCTYPE html>.",
	"expected-doctype-but-got-start-tag":
		"Start tag seen without seeing a doctype first. Expected e.g. <!DOCTYPE html>.",
	"expected-doctype-but-got-end-tag":
		"End tag seen without seeing a doctype first. Expected e.g. <!DOCTYPE html>.",
	"end-tag-after-implied-root":
		"Unexpected end tag ({name}) after the (implied) root element.",
	"expected-named-closing-tag-but-got-eof":
		"Unexpected end of file. Expected end tag ({name}).",
	"two-heads-are-not-better-than-one":
		"Unexpected start tag head in existing head. Ignored.",
	"unexpected-end-tag":
		"Unexpected end tag ({name}). Ignored.",
	"unexpected-implied-end-tag":
		"End tag {name} implied, but there were open elements.",
	"unexpected-start-tag-out-of-my-head":
		"Unexpected start tag ({name}) that can be in head. Moved.",
	"unexpected-start-tag":
		"Unexpected start tag ({name}).",
	"missing-end-tag":
		"Missing end tag ({name}).",
	"missing-end-tags":
		"Missing end tags ({name}).",
	"unexpected-start-tag-implies-end-tag":
		"Unexpected start tag ({startName}) implies end tag ({endName}).",
	"unexpected-start-tag-treated-as":
		"Unexpected start tag ({originalName}). Treated as {newName}.",
	"deprecated-tag":
		"Unexpected start tag {name}. Don't use it!",
	"unexpected-start-tag-ignored":
		"Unexpected start tag {name}. Ignored.",
	"expected-one-end-tag-but-got-another":
		"Unexpected end tag ({gotName}). Missing end tag ({expectedName}).",
	"end-tag-too-early":
		"End tag ({name}) seen too early. Expected other end tag.",
	"end-tag-too-early-named":
		"Unexpected end tag ({gotName}). Expected end tag ({expectedName}.",
	"end-tag-too-early-ignored":
		"End tag ({name}) seen too early. Ignored.",
	"adoption-agency-1.1":
		"End tag ({name}) violates step 1, paragraph 1 of the adoption agency algorithm.",
	"adoption-agency-1.2":
		"End tag ({name}) violates step 1, paragraph 2 of the adoption agency algorithm.",
	"adoption-agency-1.3":
		"End tag ({name}) violates step 1, paragraph 3 of the adoption agency algorithm.",
	"adoption-agency-4.4":
		"End tag ({name}) violates step 4, paragraph 4 of the adoption agency algorithm.",
	"unexpected-end-tag-treated-as":
		"Unexpected end tag ({originalName}). Treated as {newName}.",
	"no-end-tag":
		"This element ({name}) has no end tag.",
	"unexpected-implied-end-tag-in-table":
		"Unexpected implied end tag ({name}) in the table phase.",
	"unexpected-implied-end-tag-in-table-body":
		"Unexpected implied end tag ({name}) in the table body phase.",
	"unexpected-char-implies-table-voodoo":
		"Unexpected non-space characters in table context caused voodoo mode.",
	"unexpected-hidden-input-in-table":
		"Unexpected input with type hidden in table context.",
	"unexpected-form-in-table":
		"Unexpected form in table context.",
	"unexpected-start-tag-implies-table-voodoo":
		"Unexpected start tag ({name}) in table context caused voodoo mode.",
	"unexpected-end-tag-implies-table-voodoo":
		"Unexpected end tag ({name}) in table context caused voodoo mode.",
	"unexpected-cell-in-table-body":
		"Unexpected table cell start tag ({name}) in the table body phase.",
	"unexpected-cell-end-tag":
		"Got table cell end tag ({name}) while required end tags are missing.",
	"unexpected-end-tag-in-table-body":
		"Unexpected end tag ({name}) in the table body phase. Ignored.",
	"unexpected-implied-end-tag-in-table-row":
		"Unexpected implied end tag ({name}) in the table row phase.",
	"unexpected-end-tag-in-table-row":
		"Unexpected end tag ({name}) in the table row phase. Ignored.",
	"unexpected-select-in-select":
		"Unexpected select start tag in the select phase treated as select end tag.",
	"unexpected-input-in-select":
		"Unexpected input start tag in the select phase.",
	"unexpected-start-tag-in-select":
		"Unexpected start tag token ({name}) in the select phase. Ignored.",
	"unexpected-end-tag-in-select":
		"Unexpected end tag ({name}) in the select phase. Ignored.",
	"unexpected-table-element-start-tag-in-select-in-table":
		"Unexpected table element start tag ({name}) in the select in table phase.",
	"unexpected-table-element-end-tag-in-select-in-table":
		"Unexpected table element end tag ({name}) in the select in table phase.",
	"unexpected-char-after-body":
		"Unexpected non-space characters in the after body phase.",
	"unexpected-start-tag-after-body":
		"Unexpected start tag token ({name}) in the after body phase.",
	"unexpected-end-tag-after-body":
		"Unexpected end tag token ({name}) in the after body phase.",
	"unexpected-char-in-frameset":
		"Unepxected characters in the frameset phase. Characters ignored.",
	"unexpected-start-tag-in-frameset":
		"Unexpected start tag token ({name}) in the frameset phase. Ignored.",
	"unexpected-frameset-in-frameset-innerhtml":
		"Unexpected end tag token (frameset in the frameset phase (innerHTML).",
	"unexpected-end-tag-in-frameset":
		"Unexpected end tag token ({name}) in the frameset phase. Ignored.",
	"unexpected-char-after-frameset":
		"Unexpected non-space characters in the after frameset phase. Ignored.",
	"unexpected-start-tag-after-frameset":
		"Unexpected start tag ({name}) in the after frameset phase. Ignored.",
	"unexpected-end-tag-after-frameset":
		"Unexpected end tag ({name}) in the after frameset phase. Ignored.",
	"expected-eof-but-got-char":
		"Unexpected non-space characters. Expected end of file.",
	"expected-eof-but-got-start-tag":
		"Unexpected start tag ({name}). Expected end of file.",
	"expected-eof-but-got-end-tag":
		"Unexpected end tag ({name}). Expected end of file.",
	"unexpected-end-table-in-caption":
		"Unexpected end table tag in caption. Generates implied end caption.",
	"end-html-in-innerhtml": 
		"Unexpected html end tag in inner html mode.",
	"eof-in-table":
		"Unexpected end of file. Expected table content.",
	"eof-in-script":
		"Unexpected end of file. Expected script content.",
	"non-void-element-with-trailing-solidus":
		"Trailing solidus not allowed on element {name}.",
	"unexpected-html-element-in-foreign-content":
		"HTML start tag \"{name}\" in a foreign namespace context.",
	"unexpected-start-tag-in-table":
		"Unexpected {name}. Expected table content."
}
},
{}],
9:[function(_dereq_,module,exports){
var SAXTreeBuilder = _dereq_('./SAXTreeBuilder').SAXTreeBuilder;
var Tokenizer = _dereq_('../Tokenizer').Tokenizer;
var TreeParser = _dereq_('./TreeParser').TreeParser;

function SAXParser() {
	this.contentHandler = null;
	this._errorHandler = null;
	this._treeBuilder = new SAXTreeBuilder();
	this._tokenizer = new Tokenizer(this._treeBuilder);
	this._scriptingEnabled = false;
}

SAXParser.prototype.parse = function(source) {
	this._tokenizer.tokenize(source);
	var document = this._treeBuilder.document;
	if (document) {
		new TreeParser(this.contentHandler).parse(document);
	}
};

SAXParser.prototype.parseFragment = function(source, context) {
	this._treeBuilder.setFragmentContext(context);
	this._tokenizer.tokenize(source);
	var fragment = this._treeBuilder.getFragment();
	if (fragment) {
		new TreeParser(this.contentHandler).parse(fragment);
	}
};

Object.defineProperty(SAXParser.prototype, 'scriptingEnabled', {
	get: function() {
		return this._scriptingEnabled;
	},
	set: function(value) {
		this._scriptingEnabled = value;
		this._treeBuilder.scriptingEnabled = value;
	}
});

Object.defineProperty(SAXParser.prototype, 'errorHandler', {
	get: function() {
		return this._errorHandler;
	},
	set: function(value) {
		this._errorHandler = value;
		this._treeBuilder.errorHandler = value;
	}
});

exports.SAXParser = SAXParser;

},
{"../Tokenizer":5,"./SAXTreeBuilder":10,"./TreeParser":11}],
10:[function(_dereq_,module,exports){
var util = _dereq_('util');
var TreeBuilder = _dereq_('../TreeBuilder').TreeBuilder;

function SAXTreeBuilder() {
	TreeBuilder.call(this);
}

util.inherits(SAXTreeBuilder, TreeBuilder);

SAXTreeBuilder.prototype.start = function(tokenizer) {
	this.document = new Document(this.tokenizer);
};

SAXTreeBuilder.prototype.end = function() {
	this.document.endLocator = this.tokenizer;
};

SAXTreeBuilder.prototype.insertDoctype = function(name, publicId, systemId) {
	var doctype = new DTD(this.tokenizer, name, publicId, systemId);
	doctype.endLocator = this.tokenizer;
	this.document.appendChild(doctype);
};

SAXTreeBuilder.prototype.createElement = function(namespaceURI, localName, attributes) {
	var element = new Element(this.tokenizer, namespaceURI, localName, localName, attributes || []);
	return element;
};

SAXTreeBuilder.prototype.insertComment = function(data, parent) {
	if (!parent)
		parent = this.currentStackItem();
	var comment = new Comment(this.tokenizer, data);
	parent.appendChild(comment);
};

SAXTreeBuilder.prototype.appendCharacters = function(parent, data) {
	var text = new Characters(this.tokenizer, data);
	parent.appendChild(text);
};

SAXTreeBuilder.prototype.insertText = function(data) {
	if (this.redirectAttachToFosterParent && this.openElements.top.isFosterParenting()) {
		var tableIndex = this.openElements.findIndex('table');
		var tableItem = this.openElements.item(tableIndex);
		var table = tableItem.node;
		if (tableIndex === 0) {
			return this.appendCharacters(table, data);
		}
		var text = new Characters(this.tokenizer, data);
		var parent = table.parentNode;
		if (parent) {
			parent.insertBetween(text, table.previousSibling, table);
			return;
		}
		var stackParent = this.openElements.item(tableIndex - 1).node;
		stackParent.appendChild(text);
		return;
	}
	this.appendCharacters(this.currentStackItem().node, data);
};

SAXTreeBuilder.prototype.attachNode = function(node, parent) {
	parent.appendChild(node);
};

SAXTreeBuilder.prototype.attachNodeToFosterParent = function(child, table, stackParent) {
	var parent = table.parentNode;
	if (parent)
		parent.insertBetween(child, table.previousSibling, table);
	else
		stackParent.appendChild(child);
};

SAXTreeBuilder.prototype.detachFromParent = function(element) {
	element.detach();
};

SAXTreeBuilder.prototype.reparentChildren = function(oldParent, newParent) {
	newParent.appendChildren(oldParent.firstChild);
};

SAXTreeBuilder.prototype.getFragment = function() {
	var fragment = new DocumentFragment();
	this.reparentChildren(this.openElements.rootNode, fragment);
	return fragment;
};

function getAttribute(node, name) {
	for (var i = 0; i < node.attributes.length; i++) {
		var attribute = node.attributes[i];
		if (attribute.nodeName === name)
			return attribute.nodeValue;
	}
}

SAXTreeBuilder.prototype.addAttributesToElement = function(element, attributes) {
	for (var i = 0; i < attributes.length; i++) {
		var attribute = attributes[i];
		if (!getAttribute(element, attribute.nodeName))
			element.attributes.push(attribute);
	}
};

var NodeType = {
	/**
	 * A CDATA section.
	 */
	CDATA: 1,
	/**
	 * A run of characters.
	 */
	CHARACTERS: 2,
	/**
	 * A comment.
	 */
	COMMENT: 3,
	/**
	 * A document.
	 */
	DOCUMENT: 4,
	/**
	 * A document fragment.
	 */
	DOCUMENT_FRAGMENT: 5,
	/**
	 * A DTD.
	 */
	DTD: 6,
	/**
	 * An element.
	 */
	ELEMENT: 7,
	/**
	 * An entity.
	 */
	ENTITY: 8,
	/**
	 * A run of ignorable whitespace.
	 */
	IGNORABLE_WHITESPACE: 9,
	/**
	 * A processing instruction.
	 */
	PROCESSING_INSTRUCTION: 10,
	/**
	 * A skipped entity.
	 */
	SKIPPED_ENTITY: 11
};
/**
 * The common node superclass.
 * @version $Id$
 * @author hsivonen
 */
function Node(locator) {
	if (!locator) {
		this.columnNumber = -1;
		this.lineNumber = -1;
	} else {
		this.columnNumber = locator.columnNumber;
		this.lineNumber = locator.lineNumber;
	}
	this.parentNode = null;
	this.nextSibling = null;
	this.firstChild = null;
}

/**
 * Visit the node.
 * 
 * @param treeParser the visitor
 * @throws SAXException if stuff goes wrong
 */
Node.prototype.visit = function(treeParser) {
	throw new Error("Not Implemented");
};

/**
 * Revisit the node.
 * 
 * @param treeParser the visitor
 * @throws SAXException if stuff goes wrong
 */
Node.prototype.revisit = function(treeParser) {
	return;
};


// Subclass-specific accessors that are hoisted here to 
// avoid casting.

/**
 * Detach this node from its parent.
 */
Node.prototype.detach = function() {
	if (this.parentNode !== null) {
		this.parentNode.removeChild(this);
		this.parentNode = null;
	}
};

Object.defineProperty(Node.prototype, 'previousSibling', {
	get: function() {
		var prev = null;
		var next = this.parentNode.firstChild;
		for(;;) {
			if (this == next) {
				return prev;
			}
			prev = next;
			next = next.nextSibling;
		}
	}
});


function ParentNode(locator) {
	Node.call(this, locator);
	this.lastChild = null;
	this._endLocator = null;
}

ParentNode.prototype = Object.create(Node.prototype);

/**
 * Insert a new child before a pre-existing child and return the newly inserted child.
 * @param child the new child
 * @param sibling the existing child before which to insert (must be a child of this node) or <code>null</code> to append
 * @return <code>child</code>
 */
ParentNode.prototype.insertBefore = function(child, sibling) {
	//assert sibling == null || this == sibling.getParentNode();
	if (!sibling) {
		return this.appendChild(child);
	}
	child.detach();
	child.parentNode = this;
	if (this.firstChild == sibling) {
		child.nextSibling = sibling;
		this.firstChild = child;
	} else {
		var prev = this.firstChild;
		var next = this.firstChild.nextSibling;
		while (next != sibling) {
			prev = next;
			next = next.nextSibling;
		}
		prev.nextSibling = child;
		child.nextSibling = next;
	}
	return child;
};

ParentNode.prototype.insertBetween = function(child, prev, next) {
	// assert prev == null || this == prev.getParentNode();
	// assert next == null || this == next.getParentNode();
	// assert prev != null || next == firstChild;
	// assert next != null || prev == lastChild;
	// assert prev == null || next == null || prev.getNextSibling() == next;
	if (!next) {
		return this.appendChild(child);
	}
	child.detach();
	child.parentNode = this;
	child.nextSibling = next;
	if (!prev) {
		firstChild = child;
	} else {
		prev.nextSibling = child;
	}
	return child;
};

/**
 * Append a child to this node and return the child.
 * 
 * @param child the child to append.
 * @return <code>child</code>
 */
ParentNode.prototype.appendChild = function(child) {
	child.detach();
	child.parentNode = this;
	if (!this.firstChild) {
		this.firstChild = child;
	} else {
		this.lastChild.nextSibling = child;
	}
	this.lastChild = child;
	return child;
};

/**
 * Append the children of another node to this node removing them from the other node .
 * @param parent the other node whose children to append to this one
 */
ParentNode.prototype.appendChildren = function(parent) {
	var child = parent.firstChild;
	if (!child) {
		return;
	}
	var another = parent;
	if (!this.firstChild) {
		this.firstChild = child;
	} else {
		this.lastChild.nextSibling = child;
	}
	this.lastChild = another.lastChild;
	do {
		child.parentNode = this;
	} while ((child = child.nextSibling));
	another.firstChild = null;
	another.lastChild = null;
};

/**
 * Remove a child from this node.
 * @param node the child to remove
 */
ParentNode.prototype.removeChild = function(node) {
	//assert this == node.getParentNode();
	if (this.firstChild == node) {
		this.firstChild = node.nextSibling;
		if (this.lastChild == node) {
			this.lastChild = null;
		}
	} else {
		var prev = this.firstChild;
		var next = this.firstChild.nextSibling;
		while (next != node) {
			prev = next;
			next = next.nextSibling;
		}
		prev.nextSibling = node.nextSibling;
		if (this.lastChild == node) {
			this.lastChild = prev;
		}
	}
	node.parentNode = null;
	return node;
};

Object.defineProperty(ParentNode.prototype, 'endLocator', {
	get: function() {
		return this._endLocator;
	},
	set: function(endLocator) {
		this._endLocator = {
			lineNumber: endLocator.lineNumber,
			columnNumber: endLocator.columnNumber
		};
	}
});

/**
 * A document.
 * @version $Id$
 * @author hsivonen
 */
function Document (locator) {
	ParentNode.call(this, locator);
	this.nodeType = NodeType.DOCUMENT;
}

Document.prototype = Object.create(ParentNode.prototype);

/**
 * 
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
Document.prototype.visit = function(treeParser) {
	treeParser.startDocument(this);
};

/**
 * @see nu.validator.saxtree.Node#revisit(nu.validator.saxtree.TreeParser)
 */
Document.prototype.revisit = function(treeParser) {
	treeParser.endDocument(this.endLocator);
};

/**
 * A document fragment.
 * 
 * @version $Id$
 * @author hsivonen
 */

/**
 * The constructor.
 */
function DocumentFragment() {
	ParentNode.call(this, new Locator());
	this.nodeType = NodeType.DOCUMENT_FRAGMENT;
}

DocumentFragment.prototype = Object.create(ParentNode.prototype);
/**
 * 
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
DocumentFragment.prototype.visit = function(treeParser) {
	// nothing
};

/**
 * An element.
 * @version $Id$
 * @author hsivonen
 */
function Element(locator, uri, localName, qName, atts, prefixMappings) {
	ParentNode.call(this, locator);
	this.uri = uri;
	this.localName = localName;
	this.qName = qName;
	this.attributes = atts;
	this.prefixMappings = prefixMappings;
	this.nodeType = NodeType.ELEMENT;
}

Element.prototype = Object.create(ParentNode.prototype);

/**
 * 
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
Element.prototype.visit = function(treeParser) {
	if (this.prefixMappings) {
		for (var key in prefixMappings) {
			var mapping = prefixMappings[key];
			treeParser.startPrefixMapping(mapping.getPrefix(),
					mapping.getUri(), this);
		}
	}
	treeParser.startElement(this.uri, this.localName, this.qName, this.attributes, this);
};

/**
 * @see nu.validator.saxtree.Node#revisit(nu.validator.saxtree.TreeParser)
 */
Element.prototype.revisit = function(treeParser) {
	treeParser.endElement(this.uri, this.localName, this.qName, this.endLocator);
	if (this.prefixMappings) {
		for (var key in prefixMappings) {
			var mapping = prefixMappings[key];
			treeParser.endPrefixMapping(mapping.getPrefix(), this.endLocator);
		}
	}
};

/**
 * The constructor.
 * @param locator the locator
 * @param {String} data the buffer
 */
function Characters(locator, data){
	Node.call(this, locator);
	this.data = data;
	this.nodeType = NodeType.CHARACTERS;
}

Characters.prototype = Object.create(Node.prototype);

/**
 * 
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
Characters.prototype.visit = function (treeParser) {
	treeParser.characters(this.data, 0, this.data.length, this);
};

/**
 * The constructor.
 * @param buf the buffer
 * @param start the offset
 * @param length the length
 */
function IgnorableWhitespace(locator, data) {
	Node.call(this, locator);
	this.data = data;
	this.nodeType = NodeType.IGNORABLE_WHITESPACE;
}

IgnorableWhitespace.prototype = Object.create(Node.prototype);

/**
 * 
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
IgnorableWhitespace.prototype.visit = function(treeParser) {
	treeParser.ignorableWhitespace(this.data, 0, this.data.length, this);
};

/**
 * A comment.
 * 
 * @version $Id$
 * @author hsivonen
 */

/**
 * The constructor.
 * @param locator the locator
 * @param buf the buffer
 * @param start the offset
 * @param length the length
 */
function Comment(locator, data) {
	Node.call(this, locator);
	this.data = data;
	this.nodeType = NodeType.COMMENT;
}

Comment.prototype = Object.create(Node.prototype);

/**
 * 
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
Comment.prototype.visit = function(treeParser) {
	treeParser.comment(this.data, 0, this.data.length, this);
};

/**
 * A CDATA section.
 * @version $Id$
 * @author hsivonen
 */
/**
 * The constructor.
 * @param locator the locator
 */
function CDATA(locator) {
	ParentNode.call(this, locator);
	this.nodeType = NodeType.CDATA;
}

CDATA.prototype = Object.create(ParentNode.prototype);

/**
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
CDATA.prototype.visit = function(treeParser) {
	treeParser.startCDATA(this);
};

/**
 * 
 * @throws SAXException if things go wrong
 * @see nu.validator.saxtree.Node#revisit(nu.validator.saxtree.TreeParser)
 */
CDATA.prototype.revisit = function(treeParser) {
	treeParser.endCDATA(this.endLocator);
};

/**
 * An entity.
 * @version $Id$
 * @author hsivonen
 */

/**
 * The constructor.
 * @param locator the locator
 * @param name the name
 */
function Entity(name) {
	ParentNode.call(this);
	this.name = name;
	this.nodeType = NodeType.ENTITY;
}

Entity.prototype = Object.create(ParentNode.prototype);

/**
 * 
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
Entity.prototype.visit = function(treeParser) {
	treeParser.startEntity(this.name, this);
};

/**
 * @see nu.validator.saxtree.Node#revisit(nu.validator.saxtree.TreeParser)
 */
Entity.prototype.revisit = function(treeParser) {
	treeParser.endEntity(this.name);
};

/**
 * A skipped entity.
 * @version $Id$
 * @author hsivonen
 */

/**
 * Constructor.
 * @param locator the locator
 * @param name the name
 */

function SkippedEntity(name) {
	Node.call(this);
	this.name = name;
	this.nodeType = NodeType.SKIPPED_ENTITY;
}

SkippedEntity.prototype = Object.create(Node.prototype);

/**
 * 
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
SkippedEntity.prototype.visit = function(treeParser) {
	treeParser.skippedEntity(this.name, this);
};

/**
 * A processing instruction.
 * @version $Id$
 * @author hsivonen
 */

/**
 * PI target.
 */
//private final String target;

/**
 * PI data.
 */
//private final String data;

/**
 * Constructor.
 * @param locator the locator
 * @param target PI target
 * @param data PI data
 */
function ProcessingInstruction(target, data) {
	Node.call(this);
	this.target = target;
	this.data = data;
}

ProcessingInstruction.prototype = Object.create(Node.prototype);

/**
 * 
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
ProcessingInstruction.prototype.visit = function(treeParser) {
	treeParser.processingInstruction(this.target, this.data, this);
};

/**
 * 
 * @see nu.validator.saxtree.Node#getNodeType()
 */
ProcessingInstruction.prototype.getNodeType = function() {
	return NodeType.PROCESSING_INSTRUCTION;
};

/**
 * The constructor.
 * @param locator the locator
 * @param name the name
 * @param publicIdentifier the public id
 * @param systemIdentifier the system id
 */
function DTD(name, publicIdentifier, systemIdentifier) {
	ParentNode.call(this);
	this.name = name;
	this.publicIdentifier = publicIdentifier;
	this.systemIdentifier = systemIdentifier;
	this.nodeType = NodeType.DTD;
}

DTD.prototype = Object.create(ParentNode.prototype);

/**
 * 
 * @see nu.validator.saxtree.Node#visit(nu.validator.saxtree.TreeParser)
 */
DTD.prototype.visit = function(treeParser) {
	treeParser.startDTD(this.name, this.publicIdentifier, this.systemIdentifier, this);
};

/**
 * @see nu.validator.saxtree.Node#revisit(nu.validator.saxtree.TreeParser)
 */
DTD.prototype.revisit = function(treeParser) {
	treeParser.endDTD();
};

exports.SAXTreeBuilder = SAXTreeBuilder;

},
{"../TreeBuilder":6,"util":20}],
11:[function(_dereq_,module,exports){
/**
 * A tree visitor that replays a tree as SAX events.
 * @version $Id$
 * @author hsivonen
 */

/**
 * The constructor.
 * 
 * @param contentHandler
 *            must not be <code>null</code>
 * @param lexicalHandler
 *            may be <code>null</code>
 */
function TreeParser(contentHandler, lexicalHandler){

	/**
	 * The content handler.
	 */
	this.contentHandler;

	/**
	 * The lexical handler.
	 */
	this.lexicalHandler;

	/**
	 * The current locator.
	 */
	this.locatorDelegate;

	if (!contentHandler) {
		throw new IllegalArgumentException("contentHandler was null.");
	}
	this.contentHandler = contentHandler;
	if (!lexicalHandler) {
		this.lexicalHandler = new NullLexicalHandler();
	} else {
		this.lexicalHandler = lexicalHandler;
	}
}

/**
 * Causes SAX events for the tree rooted at the argument to be emitted.
 * <code>startDocument()</code> and <code>endDocument()</code> are only
 * emitted for a <code>Document</code> node.
 * 
 * @param node
 *            the root
 * @throws SAXException
 */
TreeParser.prototype.parse = function(node) {
	this.contentHandler.documentLocator = this;
	var current = node;
	var next;
	for (;;) {
		current.visit(this);
		if (next = current.firstChild) {
			current = next;
			continue;
		}
		for (;;) {
			current.revisit(this);
			if (current == node) {
				return;
			}
			if (next = current.nextSibling) {
				current = next;
				break;
			}
			current = current.parentNode;
		}
	}
};

/**
 * @see org.xml.sax.ContentHandler#characters(char[], int, int)
 */
TreeParser.prototype.characters = function(ch, start, length, locator) {
	this.locatorDelegate = locator;
	this.contentHandler.characters(ch, start, length);
};

/**
 * @see org.xml.sax.ContentHandler#endDocument()
 */
TreeParser.prototype.endDocument = function(locator) {
	this.locatorDelegate = locator;
	this.contentHandler.endDocument();
};

/**
 * @see org.xml.sax.ContentHandler#endElement(java.lang.String,
 *      java.lang.String, java.lang.String)
 */
TreeParser.prototype.endElement = function(uri, localName, qName, locator) {
	this.locatorDelegate = locator;
	this.contentHandler.endElement(uri, localName, qName);
};

/**
 * @see org.xml.sax.ContentHandler#endPrefixMapping(java.lang.String)
 */
TreeParser.prototype.endPrefixMapping = function(prefix, locator) {
	this.locatorDelegate = locator;
	this.contentHandler.endPrefixMapping(prefix);
};

/**
 * @see org.xml.sax.ContentHandler#ignorableWhitespace(char[], int, int)
 */
TreeParser.prototype.ignorableWhitespace = function(ch, start, length, locator) {
	this.locatorDelegate = locator;
	this.contentHandler.ignorableWhitespace(ch, start, length);
};

/**
 * @see org.xml.sax.ContentHandler#processingInstruction(java.lang.String,
 *      java.lang.String)
 */
TreeParser.prototype.processingInstruction = function(target, data, locator) {
	this.locatorDelegate = locator;
	this.contentHandler.processingInstruction(target, data);
};

/**
 * @see org.xml.sax.ContentHandler#skippedEntity(java.lang.String)
 */
TreeParser.prototype.skippedEntity = function(name, locator) {
	this.locatorDelegate = locator;
	this.contentHandler.skippedEntity(name);
};

/**
 * @see org.xml.sax.ContentHandler#startDocument()
 */
TreeParser.prototype.startDocument = function(locator) {
	this.locatorDelegate = locator;
	this.contentHandler.startDocument();
};

/**
 * @see org.xml.sax.ContentHandler#startElement(java.lang.String,
 *      java.lang.String, java.lang.String, org.xml.sax.Attributes)
 */
TreeParser.prototype.startElement = function(uri, localName, qName, atts, locator) {
	this.locatorDelegate = locator;
	this.contentHandler.startElement(uri, localName, qName, atts);
};

/**
 * @see org.xml.sax.ContentHandler#startPrefixMapping(java.lang.String,
 *      java.lang.String)
 */
TreeParser.prototype.startPrefixMapping = function(prefix, uri, locator) {
	this.locatorDelegate = locator;
	this.contentHandler.startPrefixMapping(prefix, uri);
};

/**
 * @see org.xml.sax.ext.LexicalHandler#comment(char[], int, int)
 */
TreeParser.prototype.comment = function(ch, start, length, locator) {
	this.locatorDelegate = locator;
	this.lexicalHandler.comment(ch, start, length);
};

/**
 * @see org.xml.sax.ext.LexicalHandler#endCDATA()
 */
TreeParser.prototype.endCDATA = function(locator) {
	this.locatorDelegate = locator;
	this.lexicalHandler.endCDATA();
};

/**
 * @see org.xml.sax.ext.LexicalHandler#endDTD()
 */
TreeParser.prototype.endDTD = function(locator) {
	this.locatorDelegate = locator;
	this.lexicalHandler.endDTD();
};

/**
 * @see org.xml.sax.ext.LexicalHandler#endEntity(java.lang.String)
 */
TreeParser.prototype.endEntity = function(name, locator) {
	this.locatorDelegate = locator;
	this.lexicalHandler.endEntity(name);
};

/**
 * @see org.xml.sax.ext.LexicalHandler#startCDATA()
 */
TreeParser.prototype.startCDATA = function(locator) {
	this.locatorDelegate = locator;
	this.lexicalHandler.startCDATA();
};

/**
 * @see org.xml.sax.ext.LexicalHandler#startDTD(java.lang.String,
 *      java.lang.String, java.lang.String)
 */
TreeParser.prototype.startDTD = function(name, publicId, systemId, locator) {
	this.locatorDelegate = locator;
	this.lexicalHandler.startDTD(name, publicId, systemId);
};

/**
 * @see org.xml.sax.ext.LexicalHandler#startEntity(java.lang.String)
 */
TreeParser.prototype.startEntity = function(name, locator) {
	this.locatorDelegate = locator;
	this.lexicalHandler.startEntity(name);
};

Object.defineProperty(TreeParser.prototype, 'columnNumber', {
	get: function() {
		if (!this.locatorDelegate)
			return -1;
		else
			return this.locatorDelegate.columnNumber;
	}
});

Object.defineProperty(TreeParser.prototype, 'lineNumber', {
	get: function() {
		if (!this.locatorDelegate)
			return -1;
		else
			return this.locatorDelegate.lineNumber;
	}
});

/**
 * A lexical handler that does nothing.
 * @version $Id$
 * @author hsivonen
 */
// implements LexicalHandler
function NullLexicalHandler() {

}

NullLexicalHandler.prototype.comment = function() {};
NullLexicalHandler.prototype.endCDATA = function() {};
NullLexicalHandler.prototype.endDTD = function() {};
NullLexicalHandler.prototype.endEntity = function() {};
NullLexicalHandler.prototype.startCDATA = function() {};
NullLexicalHandler.prototype.startDTD = function() {};
NullLexicalHandler.prototype.startEntity = function() {};

exports.TreeParser = TreeParser;

},
{}],
12:[function(_dereq_,module,exports){
module.exports = {
	"Aacute;": "\u00C1",
	"Aacute": "\u00C1",
	"aacute;": "\u00E1",
	"aacute": "\u00E1",
	"Abreve;": "\u0102",
	"abreve;": "\u0103",
	"ac;": "\u223E",
	"acd;": "\u223F",
	"acE;": "\u223E\u0333",
	"Acirc;": "\u00C2",
	"Acirc": "\u00C2",
	"acirc;": "\u00E2",
	"acirc": "\u00E2",
	"acute;": "\u00B4",
	"acute": "\u00B4",
	"Acy;": "\u0410",
	"acy;": "\u0430",
	"AElig;": "\u00C6",
	"AElig": "\u00C6",
	"aelig;": "\u00E6",
	"aelig": "\u00E6",
	"af;": "\u2061",
	"Afr;": "\uD835\uDD04",
	"afr;": "\uD835\uDD1E",
	"Agrave;": "\u00C0",
	"Agrave": "\u00C0",
	"agrave;": "\u00E0",
	"agrave": "\u00E0",
	"alefsym;": "\u2135",
	"aleph;": "\u2135",
	"Alpha;": "\u0391",
	"alpha;": "\u03B1",
	"Amacr;": "\u0100",
	"amacr;": "\u0101",
	"amalg;": "\u2A3F",
	"amp;": "\u0026",
	"amp": "\u0026",
	"AMP;": "\u0026",
	"AMP": "\u0026",
	"andand;": "\u2A55",
	"And;": "\u2A53",
	"and;": "\u2227",
	"andd;": "\u2A5C",
	"andslope;": "\u2A58",
	"andv;": "\u2A5A",
	"ang;": "\u2220",
	"ange;": "\u29A4",
	"angle;": "\u2220",
	"angmsdaa;": "\u29A8",
	"angmsdab;": "\u29A9",
	"angmsdac;": "\u29AA",
	"angmsdad;": "\u29AB",
	"angmsdae;": "\u29AC",
	"angmsdaf;": "\u29AD",
	"angmsdag;": "\u29AE",
	"angmsdah;": "\u29AF",
	"angmsd;": "\u2221",
	"angrt;": "\u221F",
	"angrtvb;": "\u22BE",
	"angrtvbd;": "\u299D",
	"angsph;": "\u2222",
	"angst;": "\u00C5",
	"angzarr;": "\u237C",
	"Aogon;": "\u0104",
	"aogon;": "\u0105",
	"Aopf;": "\uD835\uDD38",
	"aopf;": "\uD835\uDD52",
	"apacir;": "\u2A6F",
	"ap;": "\u2248",
	"apE;": "\u2A70",
	"ape;": "\u224A",
	"apid;": "\u224B",
	"apos;": "\u0027",
	"ApplyFunction;": "\u2061",
	"approx;": "\u2248",
	"approxeq;": "\u224A",
	"Aring;": "\u00C5",
	"Aring": "\u00C5",
	"aring;": "\u00E5",
	"aring": "\u00E5",
	"Ascr;": "\uD835\uDC9C",
	"ascr;": "\uD835\uDCB6",
	"Assign;": "\u2254",
	"ast;": "\u002A",
	"asymp;": "\u2248",
	"asympeq;": "\u224D",
	"Atilde;": "\u00C3",
	"Atilde": "\u00C3",
	"atilde;": "\u00E3",
	"atilde": "\u00E3",
	"Auml;": "\u00C4",
	"Auml": "\u00C4",
	"auml;": "\u00E4",
	"auml": "\u00E4",
	"awconint;": "\u2233",
	"awint;": "\u2A11",
	"backcong;": "\u224C",
	"backepsilon;": "\u03F6",
	"backprime;": "\u2035",
	"backsim;": "\u223D",
	"backsimeq;": "\u22CD",
	"Backslash;": "\u2216",
	"Barv;": "\u2AE7",
	"barvee;": "\u22BD",
	"barwed;": "\u2305",
	"Barwed;": "\u2306",
	"barwedge;": "\u2305",
	"bbrk;": "\u23B5",
	"bbrktbrk;": "\u23B6",
	"bcong;": "\u224C",
	"Bcy;": "\u0411",
	"bcy;": "\u0431",
	"bdquo;": "\u201E",
	"becaus;": "\u2235",
	"because;": "\u2235",
	"Because;": "\u2235",
	"bemptyv;": "\u29B0",
	"bepsi;": "\u03F6",
	"bernou;": "\u212C",
	"Bernoullis;": "\u212C",
	"Beta;": "\u0392",
	"beta;": "\u03B2",
	"beth;": "\u2136",
	"between;": "\u226C",
	"Bfr;": "\uD835\uDD05",
	"bfr;": "\uD835\uDD1F",
	"bigcap;": "\u22C2",
	"bigcirc;": "\u25EF",
	"bigcup;": "\u22C3",
	"bigodot;": "\u2A00",
	"bigoplus;": "\u2A01",
	"bigotimes;": "\u2A02",
	"bigsqcup;": "\u2A06",
	"bigstar;": "\u2605",
	"bigtriangledown;": "\u25BD",
	"bigtriangleup;": "\u25B3",
	"biguplus;": "\u2A04",
	"bigvee;": "\u22C1",
	"bigwedge;": "\u22C0",
	"bkarow;": "\u290D",
	"blacklozenge;": "\u29EB",
	"blacksquare;": "\u25AA",
	"blacktriangle;": "\u25B4",
	"blacktriangledown;": "\u25BE",
	"blacktriangleleft;": "\u25C2",
	"blacktriangleright;": "\u25B8",
	"blank;": "\u2423",
	"blk12;": "\u2592",
	"blk14;": "\u2591",
	"blk34;": "\u2593",
	"block;": "\u2588",
	"bne;": "\u003D\u20E5",
	"bnequiv;": "\u2261\u20E5",
	"bNot;": "\u2AED",
	"bnot;": "\u2310",
	"Bopf;": "\uD835\uDD39",
	"bopf;": "\uD835\uDD53",
	"bot;": "\u22A5",
	"bottom;": "\u22A5",
	"bowtie;": "\u22C8",
	"boxbox;": "\u29C9",
	"boxdl;": "\u2510",
	"boxdL;": "\u2555",
	"boxDl;": "\u2556",
	"boxDL;": "\u2557",
	"boxdr;": "\u250C",
	"boxdR;": "\u2552",
	"boxDr;": "\u2553",
	"boxDR;": "\u2554",
	"boxh;": "\u2500",
	"boxH;": "\u2550",
	"boxhd;": "\u252C",
	"boxHd;": "\u2564",
	"boxhD;": "\u2565",
	"boxHD;": "\u2566",
	"boxhu;": "\u2534",
	"boxHu;": "\u2567",
	"boxhU;": "\u2568",
	"boxHU;": "\u2569",
	"boxminus;": "\u229F",
	"boxplus;": "\u229E",
	"boxtimes;": "\u22A0",
	"boxul;": "\u2518",
	"boxuL;": "\u255B",
	"boxUl;": "\u255C",
	"boxUL;": "\u255D",
	"boxur;": "\u2514",
	"boxuR;": "\u2558",
	"boxUr;": "\u2559",
	"boxUR;": "\u255A",
	"boxv;": "\u2502",
	"boxV;": "\u2551",
	"boxvh;": "\u253C",
	"boxvH;": "\u256A",
	"boxVh;": "\u256B",
	"boxVH;": "\u256C",
	"boxvl;": "\u2524",
	"boxvL;": "\u2561",
	"boxVl;": "\u2562",
	"boxVL;": "\u2563",
	"boxvr;": "\u251C",
	"boxvR;": "\u255E",
	"boxVr;": "\u255F",
	"boxVR;": "\u2560",
	"bprime;": "\u2035",
	"breve;": "\u02D8",
	"Breve;": "\u02D8",
	"brvbar;": "\u00A6",
	"brvbar": "\u00A6",
	"bscr;": "\uD835\uDCB7",
	"Bscr;": "\u212C",
	"bsemi;": "\u204F",
	"bsim;": "\u223D",
	"bsime;": "\u22CD",
	"bsolb;": "\u29C5",
	"bsol;": "\u005C",
	"bsolhsub;": "\u27C8",
	"bull;": "\u2022",
	"bullet;": "\u2022",
	"bump;": "\u224E",
	"bumpE;": "\u2AAE",
	"bumpe;": "\u224F",
	"Bumpeq;": "\u224E",
	"bumpeq;": "\u224F",
	"Cacute;": "\u0106",
	"cacute;": "\u0107",
	"capand;": "\u2A44",
	"capbrcup;": "\u2A49",
	"capcap;": "\u2A4B",
	"cap;": "\u2229",
	"Cap;": "\u22D2",
	"capcup;": "\u2A47",
	"capdot;": "\u2A40",
	"CapitalDifferentialD;": "\u2145",
	"caps;": "\u2229\uFE00",
	"caret;": "\u2041",
	"caron;": "\u02C7",
	"Cayleys;": "\u212D",
	"ccaps;": "\u2A4D",
	"Ccaron;": "\u010C",
	"ccaron;": "\u010D",
	"Ccedil;": "\u00C7",
	"Ccedil": "\u00C7",
	"ccedil;": "\u00E7",
	"ccedil": "\u00E7",
	"Ccirc;": "\u0108",
	"ccirc;": "\u0109",
	"Cconint;": "\u2230",
	"ccups;": "\u2A4C",
	"ccupssm;": "\u2A50",
	"Cdot;": "\u010A",
	"cdot;": "\u010B",
	"cedil;": "\u00B8",
	"cedil": "\u00B8",
	"Cedilla;": "\u00B8",
	"cemptyv;": "\u29B2",
	"cent;": "\u00A2",
	"cent": "\u00A2",
	"centerdot;": "\u00B7",
	"CenterDot;": "\u00B7",
	"cfr;": "\uD835\uDD20",
	"Cfr;": "\u212D",
	"CHcy;": "\u0427",
	"chcy;": "\u0447",
	"check;": "\u2713",
	"checkmark;": "\u2713",
	"Chi;": "\u03A7",
	"chi;": "\u03C7",
	"circ;": "\u02C6",
	"circeq;": "\u2257",
	"circlearrowleft;": "\u21BA",
	"circlearrowright;": "\u21BB",
	"circledast;": "\u229B",
	"circledcirc;": "\u229A",
	"circleddash;": "\u229D",
	"CircleDot;": "\u2299",
	"circledR;": "\u00AE",
	"circledS;": "\u24C8",
	"CircleMinus;": "\u2296",
	"CirclePlus;": "\u2295",
	"CircleTimes;": "\u2297",
	"cir;": "\u25CB",
	"cirE;": "\u29C3",
	"cire;": "\u2257",
	"cirfnint;": "\u2A10",
	"cirmid;": "\u2AEF",
	"cirscir;": "\u29C2",
	"ClockwiseContourIntegral;": "\u2232",
	"CloseCurlyDoubleQuote;": "\u201D",
	"CloseCurlyQuote;": "\u2019",
	"clubs;": "\u2663",
	"clubsuit;": "\u2663",
	"colon;": "\u003A",
	"Colon;": "\u2237",
	"Colone;": "\u2A74",
	"colone;": "\u2254",
	"coloneq;": "\u2254",
	"comma;": "\u002C",
	"commat;": "\u0040",
	"comp;": "\u2201",
	"compfn;": "\u2218",
	"complement;": "\u2201",
	"complexes;": "\u2102",
	"cong;": "\u2245",
	"congdot;": "\u2A6D",
	"Congruent;": "\u2261",
	"conint;": "\u222E",
	"Conint;": "\u222F",
	"ContourIntegral;": "\u222E",
	"copf;": "\uD835\uDD54",
	"Copf;": "\u2102",
	"coprod;": "\u2210",
	"Coproduct;": "\u2210",
	"copy;": "\u00A9",
	"copy": "\u00A9",
	"COPY;": "\u00A9",
	"COPY": "\u00A9",
	"copysr;": "\u2117",
	"CounterClockwiseContourIntegral;": "\u2233",
	"crarr;": "\u21B5",
	"cross;": "\u2717",
	"Cross;": "\u2A2F",
	"Cscr;": "\uD835\uDC9E",
	"cscr;": "\uD835\uDCB8",
	"csub;": "\u2ACF",
	"csube;": "\u2AD1",
	"csup;": "\u2AD0",
	"csupe;": "\u2AD2",
	"ctdot;": "\u22EF",
	"cudarrl;": "\u2938",
	"cudarrr;": "\u2935",
	"cuepr;": "\u22DE",
	"cuesc;": "\u22DF",
	"cularr;": "\u21B6",
	"cularrp;": "\u293D",
	"cupbrcap;": "\u2A48",
	"cupcap;": "\u2A46",
	"CupCap;": "\u224D",
	"cup;": "\u222A",
	"Cup;": "\u22D3",
	"cupcup;": "\u2A4A",
	"cupdot;": "\u228D",
	"cupor;": "\u2A45",
	"cups;": "\u222A\uFE00",
	"curarr;": "\u21B7",
	"curarrm;": "\u293C",
	"curlyeqprec;": "\u22DE",
	"curlyeqsucc;": "\u22DF",
	"curlyvee;": "\u22CE",
	"curlywedge;": "\u22CF",
	"curren;": "\u00A4",
	"curren": "\u00A4",
	"curvearrowleft;": "\u21B6",
	"curvearrowright;": "\u21B7",
	"cuvee;": "\u22CE",
	"cuwed;": "\u22CF",
	"cwconint;": "\u2232",
	"cwint;": "\u2231",
	"cylcty;": "\u232D",
	"dagger;": "\u2020",
	"Dagger;": "\u2021",
	"daleth;": "\u2138",
	"darr;": "\u2193",
	"Darr;": "\u21A1",
	"dArr;": "\u21D3",
	"dash;": "\u2010",
	"Dashv;": "\u2AE4",
	"dashv;": "\u22A3",
	"dbkarow;": "\u290F",
	"dblac;": "\u02DD",
	"Dcaron;": "\u010E",
	"dcaron;": "\u010F",
	"Dcy;": "\u0414",
	"dcy;": "\u0434",
	"ddagger;": "\u2021",
	"ddarr;": "\u21CA",
	"DD;": "\u2145",
	"dd;": "\u2146",
	"DDotrahd;": "\u2911",
	"ddotseq;": "\u2A77",
	"deg;": "\u00B0",
	"deg": "\u00B0",
	"Del;": "\u2207",
	"Delta;": "\u0394",
	"delta;": "\u03B4",
	"demptyv;": "\u29B1",
	"dfisht;": "\u297F",
	"Dfr;": "\uD835\uDD07",
	"dfr;": "\uD835\uDD21",
	"dHar;": "\u2965",
	"dharl;": "\u21C3",
	"dharr;": "\u21C2",
	"DiacriticalAcute;": "\u00B4",
	"DiacriticalDot;": "\u02D9",
	"DiacriticalDoubleAcute;": "\u02DD",
	"DiacriticalGrave;": "\u0060",
	"DiacriticalTilde;": "\u02DC",
	"diam;": "\u22C4",
	"diamond;": "\u22C4",
	"Diamond;": "\u22C4",
	"diamondsuit;": "\u2666",
	"diams;": "\u2666",
	"die;": "\u00A8",
	"DifferentialD;": "\u2146",
	"digamma;": "\u03DD",
	"disin;": "\u22F2",
	"div;": "\u00F7",
	"divide;": "\u00F7",
	"divide": "\u00F7",
	"divideontimes;": "\u22C7",
	"divonx;": "\u22C7",
	"DJcy;": "\u0402",
	"djcy;": "\u0452",
	"dlcorn;": "\u231E",
	"dlcrop;": "\u230D",
	"dollar;": "\u0024",
	"Dopf;": "\uD835\uDD3B",
	"dopf;": "\uD835\uDD55",
	"Dot;": "\u00A8",
	"dot;": "\u02D9",
	"DotDot;": "\u20DC",
	"doteq;": "\u2250",
	"doteqdot;": "\u2251",
	"DotEqual;": "\u2250",
	"dotminus;": "\u2238",
	"dotplus;": "\u2214",
	"dotsquare;": "\u22A1",
	"doublebarwedge;": "\u2306",
	"DoubleContourIntegral;": "\u222F",
	"DoubleDot;": "\u00A8",
	"DoubleDownArrow;": "\u21D3",
	"DoubleLeftArrow;": "\u21D0",
	"DoubleLeftRightArrow;": "\u21D4",
	"DoubleLeftTee;": "\u2AE4",
	"DoubleLongLeftArrow;": "\u27F8",
	"DoubleLongLeftRightArrow;": "\u27FA",
	"DoubleLongRightArrow;": "\u27F9",
	"DoubleRightArrow;": "\u21D2",
	"DoubleRightTee;": "\u22A8",
	"DoubleUpArrow;": "\u21D1",
	"DoubleUpDownArrow;": "\u21D5",
	"DoubleVerticalBar;": "\u2225",
	"DownArrowBar;": "\u2913",
	"downarrow;": "\u2193",
	"DownArrow;": "\u2193",
	"Downarrow;": "\u21D3",
	"DownArrowUpArrow;": "\u21F5",
	"DownBreve;": "\u0311",
	"downdownarrows;": "\u21CA",
	"downharpoonleft;": "\u21C3",
	"downharpoonright;": "\u21C2",
	"DownLeftRightVector;": "\u2950",
	"DownLeftTeeVector;": "\u295E",
	"DownLeftVectorBar;": "\u2956",
	"DownLeftVector;": "\u21BD",
	"DownRightTeeVector;": "\u295F",
	"DownRightVectorBar;": "\u2957",
	"DownRightVector;": "\u21C1",
	"DownTeeArrow;": "\u21A7",
	"DownTee;": "\u22A4",
	"drbkarow;": "\u2910",
	"drcorn;": "\u231F",
	"drcrop;": "\u230C",
	"Dscr;": "\uD835\uDC9F",
	"dscr;": "\uD835\uDCB9",
	"DScy;": "\u0405",
	"dscy;": "\u0455",
	"dsol;": "\u29F6",
	"Dstrok;": "\u0110",
	"dstrok;": "\u0111",
	"dtdot;": "\u22F1",
	"dtri;": "\u25BF",
	"dtrif;": "\u25BE",
	"duarr;": "\u21F5",
	"duhar;": "\u296F",
	"dwangle;": "\u29A6",
	"DZcy;": "\u040F",
	"dzcy;": "\u045F",
	"dzigrarr;": "\u27FF",
	"Eacute;": "\u00C9",
	"Eacute": "\u00C9",
	"eacute;": "\u00E9",
	"eacute": "\u00E9",
	"easter;": "\u2A6E",
	"Ecaron;": "\u011A",
	"ecaron;": "\u011B",
	"Ecirc;": "\u00CA",
	"Ecirc": "\u00CA",
	"ecirc;": "\u00EA",
	"ecirc": "\u00EA",
	"ecir;": "\u2256",
	"ecolon;": "\u2255",
	"Ecy;": "\u042D",
	"ecy;": "\u044D",
	"eDDot;": "\u2A77",
	"Edot;": "\u0116",
	"edot;": "\u0117",
	"eDot;": "\u2251",
	"ee;": "\u2147",
	"efDot;": "\u2252",
	"Efr;": "\uD835\uDD08",
	"efr;": "\uD835\uDD22",
	"eg;": "\u2A9A",
	"Egrave;": "\u00C8",
	"Egrave": "\u00C8",
	"egrave;": "\u00E8",
	"egrave": "\u00E8",
	"egs;": "\u2A96",
	"egsdot;": "\u2A98",
	"el;": "\u2A99",
	"Element;": "\u2208",
	"elinters;": "\u23E7",
	"ell;": "\u2113",
	"els;": "\u2A95",
	"elsdot;": "\u2A97",
	"Emacr;": "\u0112",
	"emacr;": "\u0113",
	"empty;": "\u2205",
	"emptyset;": "\u2205",
	"EmptySmallSquare;": "\u25FB",
	"emptyv;": "\u2205",
	"EmptyVerySmallSquare;": "\u25AB",
	"emsp13;": "\u2004",
	"emsp14;": "\u2005",
	"emsp;": "\u2003",
	"ENG;": "\u014A",
	"eng;": "\u014B",
	"ensp;": "\u2002",
	"Eogon;": "\u0118",
	"eogon;": "\u0119",
	"Eopf;": "\uD835\uDD3C",
	"eopf;": "\uD835\uDD56",
	"epar;": "\u22D5",
	"eparsl;": "\u29E3",
	"eplus;": "\u2A71",
	"epsi;": "\u03B5",
	"Epsilon;": "\u0395",
	"epsilon;": "\u03B5",
	"epsiv;": "\u03F5",
	"eqcirc;": "\u2256",
	"eqcolon;": "\u2255",
	"eqsim;": "\u2242",
	"eqslantgtr;": "\u2A96",
	"eqslantless;": "\u2A95",
	"Equal;": "\u2A75",
	"equals;": "\u003D",
	"EqualTilde;": "\u2242",
	"equest;": "\u225F",
	"Equilibrium;": "\u21CC",
	"equiv;": "\u2261",
	"equivDD;": "\u2A78",
	"eqvparsl;": "\u29E5",
	"erarr;": "\u2971",
	"erDot;": "\u2253",
	"escr;": "\u212F",
	"Escr;": "\u2130",
	"esdot;": "\u2250",
	"Esim;": "\u2A73",
	"esim;": "\u2242",
	"Eta;": "\u0397",
	"eta;": "\u03B7",
	"ETH;": "\u00D0",
	"ETH": "\u00D0",
	"eth;": "\u00F0",
	"eth": "\u00F0",
	"Euml;": "\u00CB",
	"Euml": "\u00CB",
	"euml;": "\u00EB",
	"euml": "\u00EB",
	"euro;": "\u20AC",
	"excl;": "\u0021",
	"exist;": "\u2203",
	"Exists;": "\u2203",
	"expectation;": "\u2130",
	"exponentiale;": "\u2147",
	"ExponentialE;": "\u2147",
	"fallingdotseq;": "\u2252",
	"Fcy;": "\u0424",
	"fcy;": "\u0444",
	"female;": "\u2640",
	"ffilig;": "\uFB03",
	"fflig;": "\uFB00",
	"ffllig;": "\uFB04",
	"Ffr;": "\uD835\uDD09",
	"ffr;": "\uD835\uDD23",
	"filig;": "\uFB01",
	"FilledSmallSquare;": "\u25FC",
	"FilledVerySmallSquare;": "\u25AA",
	"fjlig;": "\u0066\u006A",
	"flat;": "\u266D",
	"fllig;": "\uFB02",
	"fltns;": "\u25B1",
	"fnof;": "\u0192",
	"Fopf;": "\uD835\uDD3D",
	"fopf;": "\uD835\uDD57",
	"forall;": "\u2200",
	"ForAll;": "\u2200",
	"fork;": "\u22D4",
	"forkv;": "\u2AD9",
	"Fouriertrf;": "\u2131",
	"fpartint;": "\u2A0D",
	"frac12;": "\u00BD",
	"frac12": "\u00BD",
	"frac13;": "\u2153",
	"frac14;": "\u00BC",
	"frac14": "\u00BC",
	"frac15;": "\u2155",
	"frac16;": "\u2159",
	"frac18;": "\u215B",
	"frac23;": "\u2154",
	"frac25;": "\u2156",
	"frac34;": "\u00BE",
	"frac34": "\u00BE",
	"frac35;": "\u2157",
	"frac38;": "\u215C",
	"frac45;": "\u2158",
	"frac56;": "\u215A",
	"frac58;": "\u215D",
	"frac78;": "\u215E",
	"frasl;": "\u2044",
	"frown;": "\u2322",
	"fscr;": "\uD835\uDCBB",
	"Fscr;": "\u2131",
	"gacute;": "\u01F5",
	"Gamma;": "\u0393",
	"gamma;": "\u03B3",
	"Gammad;": "\u03DC",
	"gammad;": "\u03DD",
	"gap;": "\u2A86",
	"Gbreve;": "\u011E",
	"gbreve;": "\u011F",
	"Gcedil;": "\u0122",
	"Gcirc;": "\u011C",
	"gcirc;": "\u011D",
	"Gcy;": "\u0413",
	"gcy;": "\u0433",
	"Gdot;": "\u0120",
	"gdot;": "\u0121",
	"ge;": "\u2265",
	"gE;": "\u2267",
	"gEl;": "\u2A8C",
	"gel;": "\u22DB",
	"geq;": "\u2265",
	"geqq;": "\u2267",
	"geqslant;": "\u2A7E",
	"gescc;": "\u2AA9",
	"ges;": "\u2A7E",
	"gesdot;": "\u2A80",
	"gesdoto;": "\u2A82",
	"gesdotol;": "\u2A84",
	"gesl;": "\u22DB\uFE00",
	"gesles;": "\u2A94",
	"Gfr;": "\uD835\uDD0A",
	"gfr;": "\uD835\uDD24",
	"gg;": "\u226B",
	"Gg;": "\u22D9",
	"ggg;": "\u22D9",
	"gimel;": "\u2137",
	"GJcy;": "\u0403",
	"gjcy;": "\u0453",
	"gla;": "\u2AA5",
	"gl;": "\u2277",
	"glE;": "\u2A92",
	"glj;": "\u2AA4",
	"gnap;": "\u2A8A",
	"gnapprox;": "\u2A8A",
	"gne;": "\u2A88",
	"gnE;": "\u2269",
	"gneq;": "\u2A88",
	"gneqq;": "\u2269",
	"gnsim;": "\u22E7",
	"Gopf;": "\uD835\uDD3E",
	"gopf;": "\uD835\uDD58",
	"grave;": "\u0060",
	"GreaterEqual;": "\u2265",
	"GreaterEqualLess;": "\u22DB",
	"GreaterFullEqual;": "\u2267",
	"GreaterGreater;": "\u2AA2",
	"GreaterLess;": "\u2277",
	"GreaterSlantEqual;": "\u2A7E",
	"GreaterTilde;": "\u2273",
	"Gscr;": "\uD835\uDCA2",
	"gscr;": "\u210A",
	"gsim;": "\u2273",
	"gsime;": "\u2A8E",
	"gsiml;": "\u2A90",
	"gtcc;": "\u2AA7",
	"gtcir;": "\u2A7A",
	"gt;": "\u003E",
	"gt": "\u003E",
	"GT;": "\u003E",
	"GT": "\u003E",
	"Gt;": "\u226B",
	"gtdot;": "\u22D7",
	"gtlPar;": "\u2995",
	"gtquest;": "\u2A7C",
	"gtrapprox;": "\u2A86",
	"gtrarr;": "\u2978",
	"gtrdot;": "\u22D7",
	"gtreqless;": "\u22DB",
	"gtreqqless;": "\u2A8C",
	"gtrless;": "\u2277",
	"gtrsim;": "\u2273",
	"gvertneqq;": "\u2269\uFE00",
	"gvnE;": "\u2269\uFE00",
	"Hacek;": "\u02C7",
	"hairsp;": "\u200A",
	"half;": "\u00BD",
	"hamilt;": "\u210B",
	"HARDcy;": "\u042A",
	"hardcy;": "\u044A",
	"harrcir;": "\u2948",
	"harr;": "\u2194",
	"hArr;": "\u21D4",
	"harrw;": "\u21AD",
	"Hat;": "\u005E",
	"hbar;": "\u210F",
	"Hcirc;": "\u0124",
	"hcirc;": "\u0125",
	"hearts;": "\u2665",
	"heartsuit;": "\u2665",
	"hellip;": "\u2026",
	"hercon;": "\u22B9",
	"hfr;": "\uD835\uDD25",
	"Hfr;": "\u210C",
	"HilbertSpace;": "\u210B",
	"hksearow;": "\u2925",
	"hkswarow;": "\u2926",
	"hoarr;": "\u21FF",
	"homtht;": "\u223B",
	"hookleftarrow;": "\u21A9",
	"hookrightarrow;": "\u21AA",
	"hopf;": "\uD835\uDD59",
	"Hopf;": "\u210D",
	"horbar;": "\u2015",
	"HorizontalLine;": "\u2500",
	"hscr;": "\uD835\uDCBD",
	"Hscr;": "\u210B",
	"hslash;": "\u210F",
	"Hstrok;": "\u0126",
	"hstrok;": "\u0127",
	"HumpDownHump;": "\u224E",
	"HumpEqual;": "\u224F",
	"hybull;": "\u2043",
	"hyphen;": "\u2010",
	"Iacute;": "\u00CD",
	"Iacute": "\u00CD",
	"iacute;": "\u00ED",
	"iacute": "\u00ED",
	"ic;": "\u2063",
	"Icirc;": "\u00CE",
	"Icirc": "\u00CE",
	"icirc;": "\u00EE",
	"icirc": "\u00EE",
	"Icy;": "\u0418",
	"icy;": "\u0438",
	"Idot;": "\u0130",
	"IEcy;": "\u0415",
	"iecy;": "\u0435",
	"iexcl;": "\u00A1",
	"iexcl": "\u00A1",
	"iff;": "\u21D4",
	"ifr;": "\uD835\uDD26",
	"Ifr;": "\u2111",
	"Igrave;": "\u00CC",
	"Igrave": "\u00CC",
	"igrave;": "\u00EC",
	"igrave": "\u00EC",
	"ii;": "\u2148",
	"iiiint;": "\u2A0C",
	"iiint;": "\u222D",
	"iinfin;": "\u29DC",
	"iiota;": "\u2129",
	"IJlig;": "\u0132",
	"ijlig;": "\u0133",
	"Imacr;": "\u012A",
	"imacr;": "\u012B",
	"image;": "\u2111",
	"ImaginaryI;": "\u2148",
	"imagline;": "\u2110",
	"imagpart;": "\u2111",
	"imath;": "\u0131",
	"Im;": "\u2111",
	"imof;": "\u22B7",
	"imped;": "\u01B5",
	"Implies;": "\u21D2",
	"incare;": "\u2105",
	"in;": "\u2208",
	"infin;": "\u221E",
	"infintie;": "\u29DD",
	"inodot;": "\u0131",
	"intcal;": "\u22BA",
	"int;": "\u222B",
	"Int;": "\u222C",
	"integers;": "\u2124",
	"Integral;": "\u222B",
	"intercal;": "\u22BA",
	"Intersection;": "\u22C2",
	"intlarhk;": "\u2A17",
	"intprod;": "\u2A3C",
	"InvisibleComma;": "\u2063",
	"InvisibleTimes;": "\u2062",
	"IOcy;": "\u0401",
	"iocy;": "\u0451",
	"Iogon;": "\u012E",
	"iogon;": "\u012F",
	"Iopf;": "\uD835\uDD40",
	"iopf;": "\uD835\uDD5A",
	"Iota;": "\u0399",
	"iota;": "\u03B9",
	"iprod;": "\u2A3C",
	"iquest;": "\u00BF",
	"iquest": "\u00BF",
	"iscr;": "\uD835\uDCBE",
	"Iscr;": "\u2110",
	"isin;": "\u2208",
	"isindot;": "\u22F5",
	"isinE;": "\u22F9",
	"isins;": "\u22F4",
	"isinsv;": "\u22F3",
	"isinv;": "\u2208",
	"it;": "\u2062",
	"Itilde;": "\u0128",
	"itilde;": "\u0129",
	"Iukcy;": "\u0406",
	"iukcy;": "\u0456",
	"Iuml;": "\u00CF",
	"Iuml": "\u00CF",
	"iuml;": "\u00EF",
	"iuml": "\u00EF",
	"Jcirc;": "\u0134",
	"jcirc;": "\u0135",
	"Jcy;": "\u0419",
	"jcy;": "\u0439",
	"Jfr;": "\uD835\uDD0D",
	"jfr;": "\uD835\uDD27",
	"jmath;": "\u0237",
	"Jopf;": "\uD835\uDD41",
	"jopf;": "\uD835\uDD5B",
	"Jscr;": "\uD835\uDCA5",
	"jscr;": "\uD835\uDCBF",
	"Jsercy;": "\u0408",
	"jsercy;": "\u0458",
	"Jukcy;": "\u0404",
	"jukcy;": "\u0454",
	"Kappa;": "\u039A",
	"kappa;": "\u03BA",
	"kappav;": "\u03F0",
	"Kcedil;": "\u0136",
	"kcedil;": "\u0137",
	"Kcy;": "\u041A",
	"kcy;": "\u043A",
	"Kfr;": "\uD835\uDD0E",
	"kfr;": "\uD835\uDD28",
	"kgreen;": "\u0138",
	"KHcy;": "\u0425",
	"khcy;": "\u0445",
	"KJcy;": "\u040C",
	"kjcy;": "\u045C",
	"Kopf;": "\uD835\uDD42",
	"kopf;": "\uD835\uDD5C",
	"Kscr;": "\uD835\uDCA6",
	"kscr;": "\uD835\uDCC0",
	"lAarr;": "\u21DA",
	"Lacute;": "\u0139",
	"lacute;": "\u013A",
	"laemptyv;": "\u29B4",
	"lagran;": "\u2112",
	"Lambda;": "\u039B",
	"lambda;": "\u03BB",
	"lang;": "\u27E8",
	"Lang;": "\u27EA",
	"langd;": "\u2991",
	"langle;": "\u27E8",
	"lap;": "\u2A85",
	"Laplacetrf;": "\u2112",
	"laquo;": "\u00AB",
	"laquo": "\u00AB",
	"larrb;": "\u21E4",
	"larrbfs;": "\u291F",
	"larr;": "\u2190",
	"Larr;": "\u219E",
	"lArr;": "\u21D0",
	"larrfs;": "\u291D",
	"larrhk;": "\u21A9",
	"larrlp;": "\u21AB",
	"larrpl;": "\u2939",
	"larrsim;": "\u2973",
	"larrtl;": "\u21A2",
	"latail;": "\u2919",
	"lAtail;": "\u291B",
	"lat;": "\u2AAB",
	"late;": "\u2AAD",
	"lates;": "\u2AAD\uFE00",
	"lbarr;": "\u290C",
	"lBarr;": "\u290E",
	"lbbrk;": "\u2772",
	"lbrace;": "\u007B",
	"lbrack;": "\u005B",
	"lbrke;": "\u298B",
	"lbrksld;": "\u298F",
	"lbrkslu;": "\u298D",
	"Lcaron;": "\u013D",
	"lcaron;": "\u013E",
	"Lcedil;": "\u013B",
	"lcedil;": "\u013C",
	"lceil;": "\u2308",
	"lcub;": "\u007B",
	"Lcy;": "\u041B",
	"lcy;": "\u043B",
	"ldca;": "\u2936",
	"ldquo;": "\u201C",
	"ldquor;": "\u201E",
	"ldrdhar;": "\u2967",
	"ldrushar;": "\u294B",
	"ldsh;": "\u21B2",
	"le;": "\u2264",
	"lE;": "\u2266",
	"LeftAngleBracket;": "\u27E8",
	"LeftArrowBar;": "\u21E4",
	"leftarrow;": "\u2190",
	"LeftArrow;": "\u2190",
	"Leftarrow;": "\u21D0",
	"LeftArrowRightArrow;": "\u21C6",
	"leftarrowtail;": "\u21A2",
	"LeftCeiling;": "\u2308",
	"LeftDoubleBracket;": "\u27E6",
	"LeftDownTeeVector;": "\u2961",
	"LeftDownVectorBar;": "\u2959",
	"LeftDownVector;": "\u21C3",
	"LeftFloor;": "\u230A",
	"leftharpoondown;": "\u21BD",
	"leftharpoonup;": "\u21BC",
	"leftleftarrows;": "\u21C7",
	"leftrightarrow;": "\u2194",
	"LeftRightArrow;": "\u2194",
	"Leftrightarrow;": "\u21D4",
	"leftrightarrows;": "\u21C6",
	"leftrightharpoons;": "\u21CB",
	"leftrightsquigarrow;": "\u21AD",
	"LeftRightVector;": "\u294E",
	"LeftTeeArrow;": "\u21A4",
	"LeftTee;": "\u22A3",
	"LeftTeeVector;": "\u295A",
	"leftthreetimes;": "\u22CB",
	"LeftTriangleBar;": "\u29CF",
	"LeftTriangle;": "\u22B2",
	"LeftTriangleEqual;": "\u22B4",
	"LeftUpDownVector;": "\u2951",
	"LeftUpTeeVector;": "\u2960",
	"LeftUpVectorBar;": "\u2958",
	"LeftUpVector;": "\u21BF",
	"LeftVectorBar;": "\u2952",
	"LeftVector;": "\u21BC",
	"lEg;": "\u2A8B",
	"leg;": "\u22DA",
	"leq;": "\u2264",
	"leqq;": "\u2266",
	"leqslant;": "\u2A7D",
	"lescc;": "\u2AA8",
	"les;": "\u2A7D",
	"lesdot;": "\u2A7F",
	"lesdoto;": "\u2A81",
	"lesdotor;": "\u2A83",
	"lesg;": "\u22DA\uFE00",
	"lesges;": "\u2A93",
	"lessapprox;": "\u2A85",
	"lessdot;": "\u22D6",
	"lesseqgtr;": "\u22DA",
	"lesseqqgtr;": "\u2A8B",
	"LessEqualGreater;": "\u22DA",
	"LessFullEqual;": "\u2266",
	"LessGreater;": "\u2276",
	"lessgtr;": "\u2276",
	"LessLess;": "\u2AA1",
	"lesssim;": "\u2272",
	"LessSlantEqual;": "\u2A7D",
	"LessTilde;": "\u2272",
	"lfisht;": "\u297C",
	"lfloor;": "\u230A",
	"Lfr;": "\uD835\uDD0F",
	"lfr;": "\uD835\uDD29",
	"lg;": "\u2276",
	"lgE;": "\u2A91",
	"lHar;": "\u2962",
	"lhard;": "\u21BD",
	"lharu;": "\u21BC",
	"lharul;": "\u296A",
	"lhblk;": "\u2584",
	"LJcy;": "\u0409",
	"ljcy;": "\u0459",
	"llarr;": "\u21C7",
	"ll;": "\u226A",
	"Ll;": "\u22D8",
	"llcorner;": "\u231E",
	"Lleftarrow;": "\u21DA",
	"llhard;": "\u296B",
	"lltri;": "\u25FA",
	"Lmidot;": "\u013F",
	"lmidot;": "\u0140",
	"lmoustache;": "\u23B0",
	"lmoust;": "\u23B0",
	"lnap;": "\u2A89",
	"lnapprox;": "\u2A89",
	"lne;": "\u2A87",
	"lnE;": "\u2268",
	"lneq;": "\u2A87",
	"lneqq;": "\u2268",
	"lnsim;": "\u22E6",
	"loang;": "\u27EC",
	"loarr;": "\u21FD",
	"lobrk;": "\u27E6",
	"longleftarrow;": "\u27F5",
	"LongLeftArrow;": "\u27F5",
	"Longleftarrow;": "\u27F8",
	"longleftrightarrow;": "\u27F7",
	"LongLeftRightArrow;": "\u27F7",
	"Longleftrightarrow;": "\u27FA",
	"longmapsto;": "\u27FC",
	"longrightarrow;": "\u27F6",
	"LongRightArrow;": "\u27F6",
	"Longrightarrow;": "\u27F9",
	"looparrowleft;": "\u21AB",
	"looparrowright;": "\u21AC",
	"lopar;": "\u2985",
	"Lopf;": "\uD835\uDD43",
	"lopf;": "\uD835\uDD5D",
	"loplus;": "\u2A2D",
	"lotimes;": "\u2A34",
	"lowast;": "\u2217",
	"lowbar;": "\u005F",
	"LowerLeftArrow;": "\u2199",
	"LowerRightArrow;": "\u2198",
	"loz;": "\u25CA",
	"lozenge;": "\u25CA",
	"lozf;": "\u29EB",
	"lpar;": "\u0028",
	"lparlt;": "\u2993",
	"lrarr;": "\u21C6",
	"lrcorner;": "\u231F",
	"lrhar;": "\u21CB",
	"lrhard;": "\u296D",
	"lrm;": "\u200E",
	"lrtri;": "\u22BF",
	"lsaquo;": "\u2039",
	"lscr;": "\uD835\uDCC1",
	"Lscr;": "\u2112",
	"lsh;": "\u21B0",
	"Lsh;": "\u21B0",
	"lsim;": "\u2272",
	"lsime;": "\u2A8D",
	"lsimg;": "\u2A8F",
	"lsqb;": "\u005B",
	"lsquo;": "\u2018",
	"lsquor;": "\u201A",
	"Lstrok;": "\u0141",
	"lstrok;": "\u0142",
	"ltcc;": "\u2AA6",
	"ltcir;": "\u2A79",
	"lt;": "\u003C",
	"lt": "\u003C",
	"LT;": "\u003C",
	"LT": "\u003C",
	"Lt;": "\u226A",
	"ltdot;": "\u22D6",
	"lthree;": "\u22CB",
	"ltimes;": "\u22C9",
	"ltlarr;": "\u2976",
	"ltquest;": "\u2A7B",
	"ltri;": "\u25C3",
	"ltrie;": "\u22B4",
	"ltrif;": "\u25C2",
	"ltrPar;": "\u2996",
	"lurdshar;": "\u294A",
	"luruhar;": "\u2966",
	"lvertneqq;": "\u2268\uFE00",
	"lvnE;": "\u2268\uFE00",
	"macr;": "\u00AF",
	"macr": "\u00AF",
	"male;": "\u2642",
	"malt;": "\u2720",
	"maltese;": "\u2720",
	"Map;": "\u2905",
	"map;": "\u21A6",
	"mapsto;": "\u21A6",
	"mapstodown;": "\u21A7",
	"mapstoleft;": "\u21A4",
	"mapstoup;": "\u21A5",
	"marker;": "\u25AE",
	"mcomma;": "\u2A29",
	"Mcy;": "\u041C",
	"mcy;": "\u043C",
	"mdash;": "\u2014",
	"mDDot;": "\u223A",
	"measuredangle;": "\u2221",
	"MediumSpace;": "\u205F",
	"Mellintrf;": "\u2133",
	"Mfr;": "\uD835\uDD10",
	"mfr;": "\uD835\uDD2A",
	"mho;": "\u2127",
	"micro;": "\u00B5",
	"micro": "\u00B5",
	"midast;": "\u002A",
	"midcir;": "\u2AF0",
	"mid;": "\u2223",
	"middot;": "\u00B7",
	"middot": "\u00B7",
	"minusb;": "\u229F",
	"minus;": "\u2212",
	"minusd;": "\u2238",
	"minusdu;": "\u2A2A",
	"MinusPlus;": "\u2213",
	"mlcp;": "\u2ADB",
	"mldr;": "\u2026",
	"mnplus;": "\u2213",
	"models;": "\u22A7",
	"Mopf;": "\uD835\uDD44",
	"mopf;": "\uD835\uDD5E",
	"mp;": "\u2213",
	"mscr;": "\uD835\uDCC2",
	"Mscr;": "\u2133",
	"mstpos;": "\u223E",
	"Mu;": "\u039C",
	"mu;": "\u03BC",
	"multimap;": "\u22B8",
	"mumap;": "\u22B8",
	"nabla;": "\u2207",
	"Nacute;": "\u0143",
	"nacute;": "\u0144",
	"nang;": "\u2220\u20D2",
	"nap;": "\u2249",
	"napE;": "\u2A70\u0338",
	"napid;": "\u224B\u0338",
	"napos;": "\u0149",
	"napprox;": "\u2249",
	"natural;": "\u266E",
	"naturals;": "\u2115",
	"natur;": "\u266E",
	"nbsp;": "\u00A0",
	"nbsp": "\u00A0",
	"nbump;": "\u224E\u0338",
	"nbumpe;": "\u224F\u0338",
	"ncap;": "\u2A43",
	"Ncaron;": "\u0147",
	"ncaron;": "\u0148",
	"Ncedil;": "\u0145",
	"ncedil;": "\u0146",
	"ncong;": "\u2247",
	"ncongdot;": "\u2A6D\u0338",
	"ncup;": "\u2A42",
	"Ncy;": "\u041D",
	"ncy;": "\u043D",
	"ndash;": "\u2013",
	"nearhk;": "\u2924",
	"nearr;": "\u2197",
	"neArr;": "\u21D7",
	"nearrow;": "\u2197",
	"ne;": "\u2260",
	"nedot;": "\u2250\u0338",
	"NegativeMediumSpace;": "\u200B",
	"NegativeThickSpace;": "\u200B",
	"NegativeThinSpace;": "\u200B",
	"NegativeVeryThinSpace;": "\u200B",
	"nequiv;": "\u2262",
	"nesear;": "\u2928",
	"nesim;": "\u2242\u0338",
	"NestedGreaterGreater;": "\u226B",
	"NestedLessLess;": "\u226A",
	"NewLine;": "\u000A",
	"nexist;": "\u2204",
	"nexists;": "\u2204",
	"Nfr;": "\uD835\uDD11",
	"nfr;": "\uD835\uDD2B",
	"ngE;": "\u2267\u0338",
	"nge;": "\u2271",
	"ngeq;": "\u2271",
	"ngeqq;": "\u2267\u0338",
	"ngeqslant;": "\u2A7E\u0338",
	"nges;": "\u2A7E\u0338",
	"nGg;": "\u22D9\u0338",
	"ngsim;": "\u2275",
	"nGt;": "\u226B\u20D2",
	"ngt;": "\u226F",
	"ngtr;": "\u226F",
	"nGtv;": "\u226B\u0338",
	"nharr;": "\u21AE",
	"nhArr;": "\u21CE",
	"nhpar;": "\u2AF2",
	"ni;": "\u220B",
	"nis;": "\u22FC",
	"nisd;": "\u22FA",
	"niv;": "\u220B",
	"NJcy;": "\u040A",
	"njcy;": "\u045A",
	"nlarr;": "\u219A",
	"nlArr;": "\u21CD",
	"nldr;": "\u2025",
	"nlE;": "\u2266\u0338",
	"nle;": "\u2270",
	"nleftarrow;": "\u219A",
	"nLeftarrow;": "\u21CD",
	"nleftrightarrow;": "\u21AE",
	"nLeftrightarrow;": "\u21CE",
	"nleq;": "\u2270",
	"nleqq;": "\u2266\u0338",
	"nleqslant;": "\u2A7D\u0338",
	"nles;": "\u2A7D\u0338",
	"nless;": "\u226E",
	"nLl;": "\u22D8\u0338",
	"nlsim;": "\u2274",
	"nLt;": "\u226A\u20D2",
	"nlt;": "\u226E",
	"nltri;": "\u22EA",
	"nltrie;": "\u22EC",
	"nLtv;": "\u226A\u0338",
	"nmid;": "\u2224",
	"NoBreak;": "\u2060",
	"NonBreakingSpace;": "\u00A0",
	"nopf;": "\uD835\uDD5F",
	"Nopf;": "\u2115",
	"Not;": "\u2AEC",
	"not;": "\u00AC",
	"not": "\u00AC",
	"NotCongruent;": "\u2262",
	"NotCupCap;": "\u226D",
	"NotDoubleVerticalBar;": "\u2226",
	"NotElement;": "\u2209",
	"NotEqual;": "\u2260",
	"NotEqualTilde;": "\u2242\u0338",
	"NotExists;": "\u2204",
	"NotGreater;": "\u226F",
	"NotGreaterEqual;": "\u2271",
	"NotGreaterFullEqual;": "\u2267\u0338",
	"NotGreaterGreater;": "\u226B\u0338",
	"NotGreaterLess;": "\u2279",
	"NotGreaterSlantEqual;": "\u2A7E\u0338",
	"NotGreaterTilde;": "\u2275",
	"NotHumpDownHump;": "\u224E\u0338",
	"NotHumpEqual;": "\u224F\u0338",
	"notin;": "\u2209",
	"notindot;": "\u22F5\u0338",
	"notinE;": "\u22F9\u0338",
	"notinva;": "\u2209",
	"notinvb;": "\u22F7",
	"notinvc;": "\u22F6",
	"NotLeftTriangleBar;": "\u29CF\u0338",
	"NotLeftTriangle;": "\u22EA",
	"NotLeftTriangleEqual;": "\u22EC",
	"NotLess;": "\u226E",
	"NotLessEqual;": "\u2270",
	"NotLessGreater;": "\u2278",
	"NotLessLess;": "\u226A\u0338",
	"NotLessSlantEqual;": "\u2A7D\u0338",
	"NotLessTilde;": "\u2274",
	"NotNestedGreaterGreater;": "\u2AA2\u0338",
	"NotNestedLessLess;": "\u2AA1\u0338",
	"notni;": "\u220C",
	"notniva;": "\u220C",
	"notnivb;": "\u22FE",
	"notnivc;": "\u22FD",
	"NotPrecedes;": "\u2280",
	"NotPrecedesEqual;": "\u2AAF\u0338",
	"NotPrecedesSlantEqual;": "\u22E0",
	"NotReverseElement;": "\u220C",
	"NotRightTriangleBar;": "\u29D0\u0338",
	"NotRightTriangle;": "\u22EB",
	"NotRightTriangleEqual;": "\u22ED",
	"NotSquareSubset;": "\u228F\u0338",
	"NotSquareSubsetEqual;": "\u22E2",
	"NotSquareSuperset;": "\u2290\u0338",
	"NotSquareSupersetEqual;": "\u22E3",
	"NotSubset;": "\u2282\u20D2",
	"NotSubsetEqual;": "\u2288",
	"NotSucceeds;": "\u2281",
	"NotSucceedsEqual;": "\u2AB0\u0338",
	"NotSucceedsSlantEqual;": "\u22E1",
	"NotSucceedsTilde;": "\u227F\u0338",
	"NotSuperset;": "\u2283\u20D2",
	"NotSupersetEqual;": "\u2289",
	"NotTilde;": "\u2241",
	"NotTildeEqual;": "\u2244",
	"NotTildeFullEqual;": "\u2247",
	"NotTildeTilde;": "\u2249",
	"NotVerticalBar;": "\u2224",
	"nparallel;": "\u2226",
	"npar;": "\u2226",
	"nparsl;": "\u2AFD\u20E5",
	"npart;": "\u2202\u0338",
	"npolint;": "\u2A14",
	"npr;": "\u2280",
	"nprcue;": "\u22E0",
	"nprec;": "\u2280",
	"npreceq;": "\u2AAF\u0338",
	"npre;": "\u2AAF\u0338",
	"nrarrc;": "\u2933\u0338",
	"nrarr;": "\u219B",
	"nrArr;": "\u21CF",
	"nrarrw;": "\u219D\u0338",
	"nrightarrow;": "\u219B",
	"nRightarrow;": "\u21CF",
	"nrtri;": "\u22EB",
	"nrtrie;": "\u22ED",
	"nsc;": "\u2281",
	"nsccue;": "\u22E1",
	"nsce;": "\u2AB0\u0338",
	"Nscr;": "\uD835\uDCA9",
	"nscr;": "\uD835\uDCC3",
	"nshortmid;": "\u2224",
	"nshortparallel;": "\u2226",
	"nsim;": "\u2241",
	"nsime;": "\u2244",
	"nsimeq;": "\u2244",
	"nsmid;": "\u2224",
	"nspar;": "\u2226",
	"nsqsube;": "\u22E2",
	"nsqsupe;": "\u22E3",
	"nsub;": "\u2284",
	"nsubE;": "\u2AC5\u0338",
	"nsube;": "\u2288",
	"nsubset;": "\u2282\u20D2",
	"nsubseteq;": "\u2288",
	"nsubseteqq;": "\u2AC5\u0338",
	"nsucc;": "\u2281",
	"nsucceq;": "\u2AB0\u0338",
	"nsup;": "\u2285",
	"nsupE;": "\u2AC6\u0338",
	"nsupe;": "\u2289",
	"nsupset;": "\u2283\u20D2",
	"nsupseteq;": "\u2289",
	"nsupseteqq;": "\u2AC6\u0338",
	"ntgl;": "\u2279",
	"Ntilde;": "\u00D1",
	"Ntilde": "\u00D1",
	"ntilde;": "\u00F1",
	"ntilde": "\u00F1",
	"ntlg;": "\u2278",
	"ntriangleleft;": "\u22EA",
	"ntrianglelefteq;": "\u22EC",
	"ntriangleright;": "\u22EB",
	"ntrianglerighteq;": "\u22ED",
	"Nu;": "\u039D",
	"nu;": "\u03BD",
	"num;": "\u0023",
	"numero;": "\u2116",
	"numsp;": "\u2007",
	"nvap;": "\u224D\u20D2",
	"nvdash;": "\u22AC",
	"nvDash;": "\u22AD",
	"nVdash;": "\u22AE",
	"nVDash;": "\u22AF",
	"nvge;": "\u2265\u20D2",
	"nvgt;": "\u003E\u20D2",
	"nvHarr;": "\u2904",
	"nvinfin;": "\u29DE",
	"nvlArr;": "\u2902",
	"nvle;": "\u2264\u20D2",
	"nvlt;": "\u003C\u20D2",
	"nvltrie;": "\u22B4\u20D2",
	"nvrArr;": "\u2903",
	"nvrtrie;": "\u22B5\u20D2",
	"nvsim;": "\u223C\u20D2",
	"nwarhk;": "\u2923",
	"nwarr;": "\u2196",
	"nwArr;": "\u21D6",
	"nwarrow;": "\u2196",
	"nwnear;": "\u2927",
	"Oacute;": "\u00D3",
	"Oacute": "\u00D3",
	"oacute;": "\u00F3",
	"oacute": "\u00F3",
	"oast;": "\u229B",
	"Ocirc;": "\u00D4",
	"Ocirc": "\u00D4",
	"ocirc;": "\u00F4",
	"ocirc": "\u00F4",
	"ocir;": "\u229A",
	"Ocy;": "\u041E",
	"ocy;": "\u043E",
	"odash;": "\u229D",
	"Odblac;": "\u0150",
	"odblac;": "\u0151",
	"odiv;": "\u2A38",
	"odot;": "\u2299",
	"odsold;": "\u29BC",
	"OElig;": "\u0152",
	"oelig;": "\u0153",
	"ofcir;": "\u29BF",
	"Ofr;": "\uD835\uDD12",
	"ofr;": "\uD835\uDD2C",
	"ogon;": "\u02DB",
	"Ograve;": "\u00D2",
	"Ograve": "\u00D2",
	"ograve;": "\u00F2",
	"ograve": "\u00F2",
	"ogt;": "\u29C1",
	"ohbar;": "\u29B5",
	"ohm;": "\u03A9",
	"oint;": "\u222E",
	"olarr;": "\u21BA",
	"olcir;": "\u29BE",
	"olcross;": "\u29BB",
	"oline;": "\u203E",
	"olt;": "\u29C0",
	"Omacr;": "\u014C",
	"omacr;": "\u014D",
	"Omega;": "\u03A9",
	"omega;": "\u03C9",
	"Omicron;": "\u039F",
	"omicron;": "\u03BF",
	"omid;": "\u29B6",
	"ominus;": "\u2296",
	"Oopf;": "\uD835\uDD46",
	"oopf;": "\uD835\uDD60",
	"opar;": "\u29B7",
	"OpenCurlyDoubleQuote;": "\u201C",
	"OpenCurlyQuote;": "\u2018",
	"operp;": "\u29B9",
	"oplus;": "\u2295",
	"orarr;": "\u21BB",
	"Or;": "\u2A54",
	"or;": "\u2228",
	"ord;": "\u2A5D",
	"order;": "\u2134",
	"orderof;": "\u2134",
	"ordf;": "\u00AA",
	"ordf": "\u00AA",
	"ordm;": "\u00BA",
	"ordm": "\u00BA",
	"origof;": "\u22B6",
	"oror;": "\u2A56",
	"orslope;": "\u2A57",
	"orv;": "\u2A5B",
	"oS;": "\u24C8",
	"Oscr;": "\uD835\uDCAA",
	"oscr;": "\u2134",
	"Oslash;": "\u00D8",
	"Oslash": "\u00D8",
	"oslash;": "\u00F8",
	"oslash": "\u00F8",
	"osol;": "\u2298",
	"Otilde;": "\u00D5",
	"Otilde": "\u00D5",
	"otilde;": "\u00F5",
	"otilde": "\u00F5",
	"otimesas;": "\u2A36",
	"Otimes;": "\u2A37",
	"otimes;": "\u2297",
	"Ouml;": "\u00D6",
	"Ouml": "\u00D6",
	"ouml;": "\u00F6",
	"ouml": "\u00F6",
	"ovbar;": "\u233D",
	"OverBar;": "\u203E",
	"OverBrace;": "\u23DE",
	"OverBracket;": "\u23B4",
	"OverParenthesis;": "\u23DC",
	"para;": "\u00B6",
	"para": "\u00B6",
	"parallel;": "\u2225",
	"par;": "\u2225",
	"parsim;": "\u2AF3",
	"parsl;": "\u2AFD",
	"part;": "\u2202",
	"PartialD;": "\u2202",
	"Pcy;": "\u041F",
	"pcy;": "\u043F",
	"percnt;": "\u0025",
	"period;": "\u002E",
	"permil;": "\u2030",
	"perp;": "\u22A5",
	"pertenk;": "\u2031",
	"Pfr;": "\uD835\uDD13",
	"pfr;": "\uD835\uDD2D",
	"Phi;": "\u03A6",
	"phi;": "\u03C6",
	"phiv;": "\u03D5",
	"phmmat;": "\u2133",
	"phone;": "\u260E",
	"Pi;": "\u03A0",
	"pi;": "\u03C0",
	"pitchfork;": "\u22D4",
	"piv;": "\u03D6",
	"planck;": "\u210F",
	"planckh;": "\u210E",
	"plankv;": "\u210F",
	"plusacir;": "\u2A23",
	"plusb;": "\u229E",
	"pluscir;": "\u2A22",
	"plus;": "\u002B",
	"plusdo;": "\u2214",
	"plusdu;": "\u2A25",
	"pluse;": "\u2A72",
	"PlusMinus;": "\u00B1",
	"plusmn;": "\u00B1",
	"plusmn": "\u00B1",
	"plussim;": "\u2A26",
	"plustwo;": "\u2A27",
	"pm;": "\u00B1",
	"Poincareplane;": "\u210C",
	"pointint;": "\u2A15",
	"popf;": "\uD835\uDD61",
	"Popf;": "\u2119",
	"pound;": "\u00A3",
	"pound": "\u00A3",
	"prap;": "\u2AB7",
	"Pr;": "\u2ABB",
	"pr;": "\u227A",
	"prcue;": "\u227C",
	"precapprox;": "\u2AB7",
	"prec;": "\u227A",
	"preccurlyeq;": "\u227C",
	"Precedes;": "\u227A",
	"PrecedesEqual;": "\u2AAF",
	"PrecedesSlantEqual;": "\u227C",
	"PrecedesTilde;": "\u227E",
	"preceq;": "\u2AAF",
	"precnapprox;": "\u2AB9",
	"precneqq;": "\u2AB5",
	"precnsim;": "\u22E8",
	"pre;": "\u2AAF",
	"prE;": "\u2AB3",
	"precsim;": "\u227E",
	"prime;": "\u2032",
	"Prime;": "\u2033",
	"primes;": "\u2119",
	"prnap;": "\u2AB9",
	"prnE;": "\u2AB5",
	"prnsim;": "\u22E8",
	"prod;": "\u220F",
	"Product;": "\u220F",
	"profalar;": "\u232E",
	"profline;": "\u2312",
	"profsurf;": "\u2313",
	"prop;": "\u221D",
	"Proportional;": "\u221D",
	"Proportion;": "\u2237",
	"propto;": "\u221D",
	"prsim;": "\u227E",
	"prurel;": "\u22B0",
	"Pscr;": "\uD835\uDCAB",
	"pscr;": "\uD835\uDCC5",
	"Psi;": "\u03A8",
	"psi;": "\u03C8",
	"puncsp;": "\u2008",
	"Qfr;": "\uD835\uDD14",
	"qfr;": "\uD835\uDD2E",
	"qint;": "\u2A0C",
	"qopf;": "\uD835\uDD62",
	"Qopf;": "\u211A",
	"qprime;": "\u2057",
	"Qscr;": "\uD835\uDCAC",
	"qscr;": "\uD835\uDCC6",
	"quaternions;": "\u210D",
	"quatint;": "\u2A16",
	"quest;": "\u003F",
	"questeq;": "\u225F",
	"quot;": "\u0022",
	"quot": "\u0022",
	"QUOT;": "\u0022",
	"QUOT": "\u0022",
	"rAarr;": "\u21DB",
	"race;": "\u223D\u0331",
	"Racute;": "\u0154",
	"racute;": "\u0155",
	"radic;": "\u221A",
	"raemptyv;": "\u29B3",
	"rang;": "\u27E9",
	"Rang;": "\u27EB",
	"rangd;": "\u2992",
	"range;": "\u29A5",
	"rangle;": "\u27E9",
	"raquo;": "\u00BB",
	"raquo": "\u00BB",
	"rarrap;": "\u2975",
	"rarrb;": "\u21E5",
	"rarrbfs;": "\u2920",
	"rarrc;": "\u2933",
	"rarr;": "\u2192",
	"Rarr;": "\u21A0",
	"rArr;": "\u21D2",
	"rarrfs;": "\u291E",
	"rarrhk;": "\u21AA",
	"rarrlp;": "\u21AC",
	"rarrpl;": "\u2945",
	"rarrsim;": "\u2974",
	"Rarrtl;": "\u2916",
	"rarrtl;": "\u21A3",
	"rarrw;": "\u219D",
	"ratail;": "\u291A",
	"rAtail;": "\u291C",
	"ratio;": "\u2236",
	"rationals;": "\u211A",
	"rbarr;": "\u290D",
	"rBarr;": "\u290F",
	"RBarr;": "\u2910",
	"rbbrk;": "\u2773",
	"rbrace;": "\u007D",
	"rbrack;": "\u005D",
	"rbrke;": "\u298C",
	"rbrksld;": "\u298E",
	"rbrkslu;": "\u2990",
	"Rcaron;": "\u0158",
	"rcaron;": "\u0159",
	"Rcedil;": "\u0156",
	"rcedil;": "\u0157",
	"rceil;": "\u2309",
	"rcub;": "\u007D",
	"Rcy;": "\u0420",
	"rcy;": "\u0440",
	"rdca;": "\u2937",
	"rdldhar;": "\u2969",
	"rdquo;": "\u201D",
	"rdquor;": "\u201D",
	"rdsh;": "\u21B3",
	"real;": "\u211C",
	"realine;": "\u211B",
	"realpart;": "\u211C",
	"reals;": "\u211D",
	"Re;": "\u211C",
	"rect;": "\u25AD",
	"reg;": "\u00AE",
	"reg": "\u00AE",
	"REG;": "\u00AE",
	"REG": "\u00AE",
	"ReverseElement;": "\u220B",
	"ReverseEquilibrium;": "\u21CB",
	"ReverseUpEquilibrium;": "\u296F",
	"rfisht;": "\u297D",
	"rfloor;": "\u230B",
	"rfr;": "\uD835\uDD2F",
	"Rfr;": "\u211C",
	"rHar;": "\u2964",
	"rhard;": "\u21C1",
	"rharu;": "\u21C0",
	"rharul;": "\u296C",
	"Rho;": "\u03A1",
	"rho;": "\u03C1",
	"rhov;": "\u03F1",
	"RightAngleBracket;": "\u27E9",
	"RightArrowBar;": "\u21E5",
	"rightarrow;": "\u2192",
	"RightArrow;": "\u2192",
	"Rightarrow;": "\u21D2",
	"RightArrowLeftArrow;": "\u21C4",
	"rightarrowtail;": "\u21A3",
	"RightCeiling;": "\u2309",
	"RightDoubleBracket;": "\u27E7",
	"RightDownTeeVector;": "\u295D",
	"RightDownVectorBar;": "\u2955",
	"RightDownVector;": "\u21C2",
	"RightFloor;": "\u230B",
	"rightharpoondown;": "\u21C1",
	"rightharpoonup;": "\u21C0",
	"rightleftarrows;": "\u21C4",
	"rightleftharpoons;": "\u21CC",
	"rightrightarrows;": "\u21C9",
	"rightsquigarrow;": "\u219D",
	"RightTeeArrow;": "\u21A6",
	"RightTee;": "\u22A2",
	"RightTeeVector;": "\u295B",
	"rightthreetimes;": "\u22CC",
	"RightTriangleBar;": "\u29D0",
	"RightTriangle;": "\u22B3",
	"RightTriangleEqual;": "\u22B5",
	"RightUpDownVector;": "\u294F",
	"RightUpTeeVector;": "\u295C",
	"RightUpVectorBar;": "\u2954",
	"RightUpVector;": "\u21BE",
	"RightVectorBar;": "\u2953",
	"RightVector;": "\u21C0",
	"ring;": "\u02DA",
	"risingdotseq;": "\u2253",
	"rlarr;": "\u21C4",
	"rlhar;": "\u21CC",
	"rlm;": "\u200F",
	"rmoustache;": "\u23B1",
	"rmoust;": "\u23B1",
	"rnmid;": "\u2AEE",
	"roang;": "\u27ED",
	"roarr;": "\u21FE",
	"robrk;": "\u27E7",
	"ropar;": "\u2986",
	"ropf;": "\uD835\uDD63",
	"Ropf;": "\u211D",
	"roplus;": "\u2A2E",
	"rotimes;": "\u2A35",
	"RoundImplies;": "\u2970",
	"rpar;": "\u0029",
	"rpargt;": "\u2994",
	"rppolint;": "\u2A12",
	"rrarr;": "\u21C9",
	"Rrightarrow;": "\u21DB",
	"rsaquo;": "\u203A",
	"rscr;": "\uD835\uDCC7",
	"Rscr;": "\u211B",
	"rsh;": "\u21B1",
	"Rsh;": "\u21B1",
	"rsqb;": "\u005D",
	"rsquo;": "\u2019",
	"rsquor;": "\u2019",
	"rthree;": "\u22CC",
	"rtimes;": "\u22CA",
	"rtri;": "\u25B9",
	"rtrie;": "\u22B5",
	"rtrif;": "\u25B8",
	"rtriltri;": "\u29CE",
	"RuleDelayed;": "\u29F4",
	"ruluhar;": "\u2968",
	"rx;": "\u211E",
	"Sacute;": "\u015A",
	"sacute;": "\u015B",
	"sbquo;": "\u201A",
	"scap;": "\u2AB8",
	"Scaron;": "\u0160",
	"scaron;": "\u0161",
	"Sc;": "\u2ABC",
	"sc;": "\u227B",
	"sccue;": "\u227D",
	"sce;": "\u2AB0",
	"scE;": "\u2AB4",
	"Scedil;": "\u015E",
	"scedil;": "\u015F",
	"Scirc;": "\u015C",
	"scirc;": "\u015D",
	"scnap;": "\u2ABA",
	"scnE;": "\u2AB6",
	"scnsim;": "\u22E9",
	"scpolint;": "\u2A13",
	"scsim;": "\u227F",
	"Scy;": "\u0421",
	"scy;": "\u0441",
	"sdotb;": "\u22A1",
	"sdot;": "\u22C5",
	"sdote;": "\u2A66",
	"searhk;": "\u2925",
	"searr;": "\u2198",
	"seArr;": "\u21D8",
	"searrow;": "\u2198",
	"sect;": "\u00A7",
	"sect": "\u00A7",
	"semi;": "\u003B",
	"seswar;": "\u2929",
	"setminus;": "\u2216",
	"setmn;": "\u2216",
	"sext;": "\u2736",
	"Sfr;": "\uD835\uDD16",
	"sfr;": "\uD835\uDD30",
	"sfrown;": "\u2322",
	"sharp;": "\u266F",
	"SHCHcy;": "\u0429",
	"shchcy;": "\u0449",
	"SHcy;": "\u0428",
	"shcy;": "\u0448",
	"ShortDownArrow;": "\u2193",
	"ShortLeftArrow;": "\u2190",
	"shortmid;": "\u2223",
	"shortparallel;": "\u2225",
	"ShortRightArrow;": "\u2192",
	"ShortUpArrow;": "\u2191",
	"shy;": "\u00AD",
	"shy": "\u00AD",
	"Sigma;": "\u03A3",
	"sigma;": "\u03C3",
	"sigmaf;": "\u03C2",
	"sigmav;": "\u03C2",
	"sim;": "\u223C",
	"simdot;": "\u2A6A",
	"sime;": "\u2243",
	"simeq;": "\u2243",
	"simg;": "\u2A9E",
	"simgE;": "\u2AA0",
	"siml;": "\u2A9D",
	"simlE;": "\u2A9F",
	"simne;": "\u2246",
	"simplus;": "\u2A24",
	"simrarr;": "\u2972",
	"slarr;": "\u2190",
	"SmallCircle;": "\u2218",
	"smallsetminus;": "\u2216",
	"smashp;": "\u2A33",
	"smeparsl;": "\u29E4",
	"smid;": "\u2223",
	"smile;": "\u2323",
	"smt;": "\u2AAA",
	"smte;": "\u2AAC",
	"smtes;": "\u2AAC\uFE00",
	"SOFTcy;": "\u042C",
	"softcy;": "\u044C",
	"solbar;": "\u233F",
	"solb;": "\u29C4",
	"sol;": "\u002F",
	"Sopf;": "\uD835\uDD4A",
	"sopf;": "\uD835\uDD64",
	"spades;": "\u2660",
	"spadesuit;": "\u2660",
	"spar;": "\u2225",
	"sqcap;": "\u2293",
	"sqcaps;": "\u2293\uFE00",
	"sqcup;": "\u2294",
	"sqcups;": "\u2294\uFE00",
	"Sqrt;": "\u221A",
	"sqsub;": "\u228F",
	"sqsube;": "\u2291",
	"sqsubset;": "\u228F",
	"sqsubseteq;": "\u2291",
	"sqsup;": "\u2290",
	"sqsupe;": "\u2292",
	"sqsupset;": "\u2290",
	"sqsupseteq;": "\u2292",
	"square;": "\u25A1",
	"Square;": "\u25A1",
	"SquareIntersection;": "\u2293",
	"SquareSubset;": "\u228F",
	"SquareSubsetEqual;": "\u2291",
	"SquareSuperset;": "\u2290",
	"SquareSupersetEqual;": "\u2292",
	"SquareUnion;": "\u2294",
	"squarf;": "\u25AA",
	"squ;": "\u25A1",
	"squf;": "\u25AA",
	"srarr;": "\u2192",
	"Sscr;": "\uD835\uDCAE",
	"sscr;": "\uD835\uDCC8",
	"ssetmn;": "\u2216",
	"ssmile;": "\u2323",
	"sstarf;": "\u22C6",
	"Star;": "\u22C6",
	"star;": "\u2606",
	"starf;": "\u2605",
	"straightepsilon;": "\u03F5",
	"straightphi;": "\u03D5",
	"strns;": "\u00AF",
	"sub;": "\u2282",
	"Sub;": "\u22D0",
	"subdot;": "\u2ABD",
	"subE;": "\u2AC5",
	"sube;": "\u2286",
	"subedot;": "\u2AC3",
	"submult;": "\u2AC1",
	"subnE;": "\u2ACB",
	"subne;": "\u228A",
	"subplus;": "\u2ABF",
	"subrarr;": "\u2979",
	"subset;": "\u2282",
	"Subset;": "\u22D0",
	"subseteq;": "\u2286",
	"subseteqq;": "\u2AC5",
	"SubsetEqual;": "\u2286",
	"subsetneq;": "\u228A",
	"subsetneqq;": "\u2ACB",
	"subsim;": "\u2AC7",
	"subsub;": "\u2AD5",
	"subsup;": "\u2AD3",
	"succapprox;": "\u2AB8",
	"succ;": "\u227B",
	"succcurlyeq;": "\u227D",
	"Succeeds;": "\u227B",
	"SucceedsEqual;": "\u2AB0",
	"SucceedsSlantEqual;": "\u227D",
	"SucceedsTilde;": "\u227F",
	"succeq;": "\u2AB0",
	"succnapprox;": "\u2ABA",
	"succneqq;": "\u2AB6",
	"succnsim;": "\u22E9",
	"succsim;": "\u227F",
	"SuchThat;": "\u220B",
	"sum;": "\u2211",
	"Sum;": "\u2211",
	"sung;": "\u266A",
	"sup1;": "\u00B9",
	"sup1": "\u00B9",
	"sup2;": "\u00B2",
	"sup2": "\u00B2",
	"sup3;": "\u00B3",
	"sup3": "\u00B3",
	"sup;": "\u2283",
	"Sup;": "\u22D1",
	"supdot;": "\u2ABE",
	"supdsub;": "\u2AD8",
	"supE;": "\u2AC6",
	"supe;": "\u2287",
	"supedot;": "\u2AC4",
	"Superset;": "\u2283",
	"SupersetEqual;": "\u2287",
	"suphsol;": "\u27C9",
	"suphsub;": "\u2AD7",
	"suplarr;": "\u297B",
	"supmult;": "\u2AC2",
	"supnE;": "\u2ACC",
	"supne;": "\u228B",
	"supplus;": "\u2AC0",
	"supset;": "\u2283",
	"Supset;": "\u22D1",
	"supseteq;": "\u2287",
	"supseteqq;": "\u2AC6",
	"supsetneq;": "\u228B",
	"supsetneqq;": "\u2ACC",
	"supsim;": "\u2AC8",
	"supsub;": "\u2AD4",
	"supsup;": "\u2AD6",
	"swarhk;": "\u2926",
	"swarr;": "\u2199",
	"swArr;": "\u21D9",
	"swarrow;": "\u2199",
	"swnwar;": "\u292A",
	"szlig;": "\u00DF",
	"szlig": "\u00DF",
	"Tab;": "\u0009",
	"target;": "\u2316",
	"Tau;": "\u03A4",
	"tau;": "\u03C4",
	"tbrk;": "\u23B4",
	"Tcaron;": "\u0164",
	"tcaron;": "\u0165",
	"Tcedil;": "\u0162",
	"tcedil;": "\u0163",
	"Tcy;": "\u0422",
	"tcy;": "\u0442",
	"tdot;": "\u20DB",
	"telrec;": "\u2315",
	"Tfr;": "\uD835\uDD17",
	"tfr;": "\uD835\uDD31",
	"there4;": "\u2234",
	"therefore;": "\u2234",
	"Therefore;": "\u2234",
	"Theta;": "\u0398",
	"theta;": "\u03B8",
	"thetasym;": "\u03D1",
	"thetav;": "\u03D1",
	"thickapprox;": "\u2248",
	"thicksim;": "\u223C",
	"ThickSpace;": "\u205F\u200A",
	"ThinSpace;": "\u2009",
	"thinsp;": "\u2009",
	"thkap;": "\u2248",
	"thksim;": "\u223C",
	"THORN;": "\u00DE",
	"THORN": "\u00DE",
	"thorn;": "\u00FE",
	"thorn": "\u00FE",
	"tilde;": "\u02DC",
	"Tilde;": "\u223C",
	"TildeEqual;": "\u2243",
	"TildeFullEqual;": "\u2245",
	"TildeTilde;": "\u2248",
	"timesbar;": "\u2A31",
	"timesb;": "\u22A0",
	"times;": "\u00D7",
	"times": "\u00D7",
	"timesd;": "\u2A30",
	"tint;": "\u222D",
	"toea;": "\u2928",
	"topbot;": "\u2336",
	"topcir;": "\u2AF1",
	"top;": "\u22A4",
	"Topf;": "\uD835\uDD4B",
	"topf;": "\uD835\uDD65",
	"topfork;": "\u2ADA",
	"tosa;": "\u2929",
	"tprime;": "\u2034",
	"trade;": "\u2122",
	"TRADE;": "\u2122",
	"triangle;": "\u25B5",
	"triangledown;": "\u25BF",
	"triangleleft;": "\u25C3",
	"trianglelefteq;": "\u22B4",
	"triangleq;": "\u225C",
	"triangleright;": "\u25B9",
	"trianglerighteq;": "\u22B5",
	"tridot;": "\u25EC",
	"trie;": "\u225C",
	"triminus;": "\u2A3A",
	"TripleDot;": "\u20DB",
	"triplus;": "\u2A39",
	"trisb;": "\u29CD",
	"tritime;": "\u2A3B",
	"trpezium;": "\u23E2",
	"Tscr;": "\uD835\uDCAF",
	"tscr;": "\uD835\uDCC9",
	"TScy;": "\u0426",
	"tscy;": "\u0446",
	"TSHcy;": "\u040B",
	"tshcy;": "\u045B",
	"Tstrok;": "\u0166",
	"tstrok;": "\u0167",
	"twixt;": "\u226C",
	"twoheadleftarrow;": "\u219E",
	"twoheadrightarrow;": "\u21A0",
	"Uacute;": "\u00DA",
	"Uacute": "\u00DA",
	"uacute;": "\u00FA",
	"uacute": "\u00FA",
	"uarr;": "\u2191",
	"Uarr;": "\u219F",
	"uArr;": "\u21D1",
	"Uarrocir;": "\u2949",
	"Ubrcy;": "\u040E",
	"ubrcy;": "\u045E",
	"Ubreve;": "\u016C",
	"ubreve;": "\u016D",
	"Ucirc;": "\u00DB",
	"Ucirc": "\u00DB",
	"ucirc;": "\u00FB",
	"ucirc": "\u00FB",
	"Ucy;": "\u0423",
	"ucy;": "\u0443",
	"udarr;": "\u21C5",
	"Udblac;": "\u0170",
	"udblac;": "\u0171",
	"udhar;": "\u296E",
	"ufisht;": "\u297E",
	"Ufr;": "\uD835\uDD18",
	"ufr;": "\uD835\uDD32",
	"Ugrave;": "\u00D9",
	"Ugrave": "\u00D9",
	"ugrave;": "\u00F9",
	"ugrave": "\u00F9",
	"uHar;": "\u2963",
	"uharl;": "\u21BF",
	"uharr;": "\u21BE",
	"uhblk;": "\u2580",
	"ulcorn;": "\u231C",
	"ulcorner;": "\u231C",
	"ulcrop;": "\u230F",
	"ultri;": "\u25F8",
	"Umacr;": "\u016A",
	"umacr;": "\u016B",
	"uml;": "\u00A8",
	"uml": "\u00A8",
	"UnderBar;": "\u005F",
	"UnderBrace;": "\u23DF",
	"UnderBracket;": "\u23B5",
	"UnderParenthesis;": "\u23DD",
	"Union;": "\u22C3",
	"UnionPlus;": "\u228E",
	"Uogon;": "\u0172",
	"uogon;": "\u0173",
	"Uopf;": "\uD835\uDD4C",
	"uopf;": "\uD835\uDD66",
	"UpArrowBar;": "\u2912",
	"uparrow;": "\u2191",
	"UpArrow;": "\u2191",
	"Uparrow;": "\u21D1",
	"UpArrowDownArrow;": "\u21C5",
	"updownarrow;": "\u2195",
	"UpDownArrow;": "\u2195",
	"Updownarrow;": "\u21D5",
	"UpEquilibrium;": "\u296E",
	"upharpoonleft;": "\u21BF",
	"upharpoonright;": "\u21BE",
	"uplus;": "\u228E",
	"UpperLeftArrow;": "\u2196",
	"UpperRightArrow;": "\u2197",
	"upsi;": "\u03C5",
	"Upsi;": "\u03D2",
	"upsih;": "\u03D2",
	"Upsilon;": "\u03A5",
	"upsilon;": "\u03C5",
	"UpTeeArrow;": "\u21A5",
	"UpTee;": "\u22A5",
	"upuparrows;": "\u21C8",
	"urcorn;": "\u231D",
	"urcorner;": "\u231D",
	"urcrop;": "\u230E",
	"Uring;": "\u016E",
	"uring;": "\u016F",
	"urtri;": "\u25F9",
	"Uscr;": "\uD835\uDCB0",
	"uscr;": "\uD835\uDCCA",
	"utdot;": "\u22F0",
	"Utilde;": "\u0168",
	"utilde;": "\u0169",
	"utri;": "\u25B5",
	"utrif;": "\u25B4",
	"uuarr;": "\u21C8",
	"Uuml;": "\u00DC",
	"Uuml": "\u00DC",
	"uuml;": "\u00FC",
	"uuml": "\u00FC",
	"uwangle;": "\u29A7",
	"vangrt;": "\u299C",
	"varepsilon;": "\u03F5",
	"varkappa;": "\u03F0",
	"varnothing;": "\u2205",
	"varphi;": "\u03D5",
	"varpi;": "\u03D6",
	"varpropto;": "\u221D",
	"varr;": "\u2195",
	"vArr;": "\u21D5",
	"varrho;": "\u03F1",
	"varsigma;": "\u03C2",
	"varsubsetneq;": "\u228A\uFE00",
	"varsubsetneqq;": "\u2ACB\uFE00",
	"varsupsetneq;": "\u228B\uFE00",
	"varsupsetneqq;": "\u2ACC\uFE00",
	"vartheta;": "\u03D1",
	"vartriangleleft;": "\u22B2",
	"vartriangleright;": "\u22B3",
	"vBar;": "\u2AE8",
	"Vbar;": "\u2AEB",
	"vBarv;": "\u2AE9",
	"Vcy;": "\u0412",
	"vcy;": "\u0432",
	"vdash;": "\u22A2",
	"vDash;": "\u22A8",
	"Vdash;": "\u22A9",
	"VDash;": "\u22AB",
	"Vdashl;": "\u2AE6",
	"veebar;": "\u22BB",
	"vee;": "\u2228",
	"Vee;": "\u22C1",
	"veeeq;": "\u225A",
	"vellip;": "\u22EE",
	"verbar;": "\u007C",
	"Verbar;": "\u2016",
	"vert;": "\u007C",
	"Vert;": "\u2016",
	"VerticalBar;": "\u2223",
	"VerticalLine;": "\u007C",
	"VerticalSeparator;": "\u2758",
	"VerticalTilde;": "\u2240",
	"VeryThinSpace;": "\u200A",
	"Vfr;": "\uD835\uDD19",
	"vfr;": "\uD835\uDD33",
	"vltri;": "\u22B2",
	"vnsub;": "\u2282\u20D2",
	"vnsup;": "\u2283\u20D2",
	"Vopf;": "\uD835\uDD4D",
	"vopf;": "\uD835\uDD67",
	"vprop;": "\u221D",
	"vrtri;": "\u22B3",
	"Vscr;": "\uD835\uDCB1",
	"vscr;": "\uD835\uDCCB",
	"vsubnE;": "\u2ACB\uFE00",
	"vsubne;": "\u228A\uFE00",
	"vsupnE;": "\u2ACC\uFE00",
	"vsupne;": "\u228B\uFE00",
	"Vvdash;": "\u22AA",
	"vzigzag;": "\u299A",
	"Wcirc;": "\u0174",
	"wcirc;": "\u0175",
	"wedbar;": "\u2A5F",
	"wedge;": "\u2227",
	"Wedge;": "\u22C0",
	"wedgeq;": "\u2259",
	"weierp;": "\u2118",
	"Wfr;": "\uD835\uDD1A",
	"wfr;": "\uD835\uDD34",
	"Wopf;": "\uD835\uDD4E",
	"wopf;": "\uD835\uDD68",
	"wp;": "\u2118",
	"wr;": "\u2240",
	"wreath;": "\u2240",
	"Wscr;": "\uD835\uDCB2",
	"wscr;": "\uD835\uDCCC",
	"xcap;": "\u22C2",
	"xcirc;": "\u25EF",
	"xcup;": "\u22C3",
	"xdtri;": "\u25BD",
	"Xfr;": "\uD835\uDD1B",
	"xfr;": "\uD835\uDD35",
	"xharr;": "\u27F7",
	"xhArr;": "\u27FA",
	"Xi;": "\u039E",
	"xi;": "\u03BE",
	"xlarr;": "\u27F5",
	"xlArr;": "\u27F8",
	"xmap;": "\u27FC",
	"xnis;": "\u22FB",
	"xodot;": "\u2A00",
	"Xopf;": "\uD835\uDD4F",
	"xopf;": "\uD835\uDD69",
	"xoplus;": "\u2A01",
	"xotime;": "\u2A02",
	"xrarr;": "\u27F6",
	"xrArr;": "\u27F9",
	"Xscr;": "\uD835\uDCB3",
	"xscr;": "\uD835\uDCCD",
	"xsqcup;": "\u2A06",
	"xuplus;": "\u2A04",
	"xutri;": "\u25B3",
	"xvee;": "\u22C1",
	"xwedge;": "\u22C0",
	"Yacute;": "\u00DD",
	"Yacute": "\u00DD",
	"yacute;": "\u00FD",
	"yacute": "\u00FD",
	"YAcy;": "\u042F",
	"yacy;": "\u044F",
	"Ycirc;": "\u0176",
	"ycirc;": "\u0177",
	"Ycy;": "\u042B",
	"ycy;": "\u044B",
	"yen;": "\u00A5",
	"yen": "\u00A5",
	"Yfr;": "\uD835\uDD1C",
	"yfr;": "\uD835\uDD36",
	"YIcy;": "\u0407",
	"yicy;": "\u0457",
	"Yopf;": "\uD835\uDD50",
	"yopf;": "\uD835\uDD6A",
	"Yscr;": "\uD835\uDCB4",
	"yscr;": "\uD835\uDCCE",
	"YUcy;": "\u042E",
	"yucy;": "\u044E",
	"yuml;": "\u00FF",
	"yuml": "\u00FF",
	"Yuml;": "\u0178",
	"Zacute;": "\u0179",
	"zacute;": "\u017A",
	"Zcaron;": "\u017D",
	"zcaron;": "\u017E",
	"Zcy;": "\u0417",
	"zcy;": "\u0437",
	"Zdot;": "\u017B",
	"zdot;": "\u017C",
	"zeetrf;": "\u2128",
	"ZeroWidthSpace;": "\u200B",
	"Zeta;": "\u0396",
	"zeta;": "\u03B6",
	"zfr;": "\uD835\uDD37",
	"Zfr;": "\u2128",
	"ZHcy;": "\u0416",
	"zhcy;": "\u0436",
	"zigrarr;": "\u21DD",
	"zopf;": "\uD835\uDD6B",
	"Zopf;": "\u2124",
	"Zscr;": "\uD835\uDCB5",
	"zscr;": "\uD835\uDCCF",
	"zwj;": "\u200D",
	"zwnj;": "\u200C"
};

},
{}],
13:[function(_dereq_,module,exports){
// http://wiki.commonjs.org/wiki/Unit_Testing/1.0
//
// THIS IS NOT TESTED NOR LIKELY TO WORK OUTSIDE V8!
//
// Originally from narwhal.js (http://narwhaljs.org)
// Copyright (c) 2009 Thomas Robinson <280north.com>
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the 'Software'), to
// deal in the Software without restriction, including without limitation the
// rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
// sell copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
// ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
// WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

// when used in node, this will actually load the util module we depend on
// versus loading the builtin util module as happens otherwise
// this is a bug in node module loading as far as I am concerned
var util = _dereq_('util/');

var pSlice = Array.prototype.slice;
var hasOwn = Object.prototype.hasOwnProperty;

// 1. The assert module provides functions that throw
// AssertionError's when particular conditions are not met. The
// assert module must conform to the following interface.

var assert = module.exports = ok;

// 2. The AssertionError is defined in assert.
// new assert.AssertionError({ message: message,
//                             actual: actual,
//                             expected: expected })

assert.AssertionError = function AssertionError(options) {
  this.name = 'AssertionError';
  this.actual = options.actual;
  this.expected = options.expected;
  this.operator = options.operator;
  if (options.message) {
    this.message = options.message;
    this.generatedMessage = false;
  } else {
    this.message = getMessage(this);
    this.generatedMessage = true;
  }
  var stackStartFunction = options.stackStartFunction || fail;

  if (Error.captureStackTrace) {
    Error.captureStackTrace(this, stackStartFunction);
  }
  else {
    // non v8 browsers so we can have a stacktrace
    var err = new Error();
    if (err.stack) {
      var out = err.stack;

      // try to strip useless frames
      var fn_name = stackStartFunction.name;
      var idx = out.indexOf('\n' + fn_name);
      if (idx >= 0) {
        // once we have located the function frame
        // we need to strip out everything before it (and its line)
        var next_line = out.indexOf('\n', idx + 1);
        out = out.substring(next_line + 1);
      }

      this.stack = out;
    }
  }
};

// assert.AssertionError instanceof Error
util.inherits(assert.AssertionError, Error);

function replacer(key, value) {
  if (util.isUndefined(value)) {
    return '' + value;
  }
  if (util.isNumber(value) && (isNaN(value) || !isFinite(value))) {
    return value.toString();
  }
  if (util.isFunction(value) || util.isRegExp(value)) {
    return value.toString();
  }
  return value;
}

function truncate(s, n) {
  if (util.isString(s)) {
    return s.length < n ? s : s.slice(0, n);
  } else {
    return s;
  }
}

function getMessage(self) {
  return truncate(JSON.stringify(self.actual, replacer), 128) + ' ' +
         self.operator + ' ' +
         truncate(JSON.stringify(self.expected, replacer), 128);
}

// At present only the three keys mentioned above are used and
// understood by the spec. Implementations or sub modules can pass
// other keys to the AssertionError's constructor - they will be
// ignored.

// 3. All of the following functions must throw an AssertionError
// when a corresponding condition is not met, with a message that
// may be undefined if not provided.  All assertion methods provide
// both the actual and expected values to the assertion error for
// display purposes.

function fail(actual, expected, message, operator, stackStartFunction) {
  throw new assert.AssertionError({
    message: message,
    actual: actual,
    expected: expected,
    operator: operator,
    stackStartFunction: stackStartFunction
  });
}

// EXTENSION! allows for well behaved errors defined elsewhere.
assert.fail = fail;

// 4. Pure assertion tests whether a value is truthy, as determined
// by !!guard.
// assert.ok(guard, message_opt);
// This statement is equivalent to assert.equal(true, !!guard,
// message_opt);. To test strictly for the value true, use
// assert.strictEqual(true, guard, message_opt);.

function ok(value, message) {
  if (!value) fail(value, true, message, '==', assert.ok);
}
assert.ok = ok;

// 5. The equality assertion tests shallow, coercive equality with
// ==.
// assert.equal(actual, expected, message_opt);

assert.equal = function equal(actual, expected, message) {
  if (actual != expected) fail(actual, expected, message, '==', assert.equal);
};

// 6. The non-equality assertion tests for whether two objects are not equal
// with != assert.notEqual(actual, expected, message_opt);

assert.notEqual = function notEqual(actual, expected, message) {
  if (actual == expected) {
    fail(actual, expected, message, '!=', assert.notEqual);
  }
};

// 7. The equivalence assertion tests a deep equality relation.
// assert.deepEqual(actual, expected, message_opt);

assert.deepEqual = function deepEqual(actual, expected, message) {
  if (!_deepEqual(actual, expected)) {
    fail(actual, expected, message, 'deepEqual', assert.deepEqual);
  }
};

function _deepEqual(actual, expected) {
  // 7.1. All identical values are equivalent, as determined by ===.
  if (actual === expected) {
    return true;

  } else if (util.isBuffer(actual) && util.isBuffer(expected)) {
    if (actual.length != expected.length) return false;

    for (var i = 0; i < actual.length; i++) {
      if (actual[i] !== expected[i]) return false;
    }

    return true;

  // 7.2. If the expected value is a Date object, the actual value is
  // equivalent if it is also a Date object that refers to the same time.
  } else if (util.isDate(actual) && util.isDate(expected)) {
    return actual.getTime() === expected.getTime();

  // 7.3 If the expected value is a RegExp object, the actual value is
  // equivalent if it is also a RegExp object with the same source and
  // properties (`global`, `multiline`, `lastIndex`, `ignoreCase`).
  } else if (util.isRegExp(actual) && util.isRegExp(expected)) {
    return actual.source === expected.source &&
           actual.global === expected.global &&
           actual.multiline === expected.multiline &&
           actual.lastIndex === expected.lastIndex &&
           actual.ignoreCase === expected.ignoreCase;

  // 7.4. Other pairs that do not both pass typeof value == 'object',
  // equivalence is determined by ==.
  } else if (!util.isObject(actual) && !util.isObject(expected)) {
    return actual == expected;

  // 7.5 For all other Object pairs, including Array objects, equivalence is
  // determined by having the same number of owned properties (as verified
  // with Object.prototype.hasOwnProperty.call), the same set of keys
  // (although not necessarily the same order), equivalent values for every
  // corresponding key, and an identical 'prototype' property. Note: this
  // accounts for both named and indexed properties on Arrays.
  } else {
    return objEquiv(actual, expected);
  }
}

function isArguments(object) {
  return Object.prototype.toString.call(object) == '[object Arguments]';
}

function objEquiv(a, b) {
  if (util.isNullOrUndefined(a) || util.isNullOrUndefined(b))
    return false;
  // an identical 'prototype' property.
  if (a.prototype !== b.prototype) return false;
  //~~~I've managed to break Object.keys through screwy arguments passing.
  //   Converting to array solves the problem.
  if (isArguments(a)) {
    if (!isArguments(b)) {
      return false;
    }
    a = pSlice.call(a);
    b = pSlice.call(b);
    return _deepEqual(a, b);
  }
  try {
    var ka = objectKeys(a),
        kb = objectKeys(b),
        key, i;
  } catch (e) {//happens when one is a string literal and the other isn't
    return false;
  }
  // having the same number of owned properties (keys incorporates
  // hasOwnProperty)
  if (ka.length != kb.length)
    return false;
  //the same set of keys (although not necessarily the same order),
  ka.sort();
  kb.sort();
  //~~~cheap key test
  for (i = ka.length - 1; i >= 0; i--) {
    if (ka[i] != kb[i])
      return false;
  }
  //equivalent values for every corresponding key, and
  //~~~possibly expensive deep test
  for (i = ka.length - 1; i >= 0; i--) {
    key = ka[i];
    if (!_deepEqual(a[key], b[key])) return false;
  }
  return true;
}

// 8. The non-equivalence assertion tests for any deep inequality.
// assert.notDeepEqual(actual, expected, message_opt);

assert.notDeepEqual = function notDeepEqual(actual, expected, message) {
  if (_deepEqual(actual, expected)) {
    fail(actual, expected, message, 'notDeepEqual', assert.notDeepEqual);
  }
};

// 9. The strict equality assertion tests strict equality, as determined by ===.
// assert.strictEqual(actual, expected, message_opt);

assert.strictEqual = function strictEqual(actual, expected, message) {
  if (actual !== expected) {
    fail(actual, expected, message, '===', assert.strictEqual);
  }
};

// 10. The strict non-equality assertion tests for strict inequality, as
// determined by !==.  assert.notStrictEqual(actual, expected, message_opt);

assert.notStrictEqual = function notStrictEqual(actual, expected, message) {
  if (actual === expected) {
    fail(actual, expected, message, '!==', assert.notStrictEqual);
  }
};

function expectedException(actual, expected) {
  if (!actual || !expected) {
    return false;
  }

  if (Object.prototype.toString.call(expected) == '[object RegExp]') {
    return expected.test(actual);
  } else if (actual instanceof expected) {
    return true;
  } else if (expected.call({}, actual) === true) {
    return true;
  }

  return false;
}

function _throws(shouldThrow, block, expected, message) {
  var actual;

  if (util.isString(expected)) {
    message = expected;
    expected = null;
  }

  try {
    block();
  } catch (e) {
    actual = e;
  }

  message = (expected && expected.name ? ' (' + expected.name + ').' : '.') +
            (message ? ' ' + message : '.');

  if (shouldThrow && !actual) {
    fail(actual, expected, 'Missing expected exception' + message);
  }

  if (!shouldThrow && expectedException(actual, expected)) {
    fail(actual, expected, 'Got unwanted exception' + message);
  }

  if ((shouldThrow && actual && expected &&
      !expectedException(actual, expected)) || (!shouldThrow && actual)) {
    throw actual;
  }
}

// 11. Expected to throw an error:
// assert.throws(block, Error_opt, message_opt);

assert.throws = function(block, /*optional*/error, /*optional*/message) {
  _throws.apply(this, [true].concat(pSlice.call(arguments)));
};

// EXTENSION! This is annoying to write outside this module.
assert.doesNotThrow = function(block, /*optional*/message) {
  _throws.apply(this, [false].concat(pSlice.call(arguments)));
};

assert.ifError = function(err) { if (err) {throw err;}};

var objectKeys = Object.keys || function (obj) {
  var keys = [];
  for (var key in obj) {
    if (hasOwn.call(obj, key)) keys.push(key);
  }
  return keys;
};

},
{"util/":15}],
14:[function(_dereq_,module,exports){
module.exports = function isBuffer(arg) {
  return arg && typeof arg === 'object'
    && typeof arg.copy === 'function'
    && typeof arg.fill === 'function'
    && typeof arg.readUInt8 === 'function';
}
},
{}],
15:[function(_dereq_,module,exports){
(function (process,global){
// Copyright Joyent, Inc. and other Node contributors.
//
// Permission is hereby granted, free of charge, to any person obtaining a
// copy of this software and associated documentation files (the
// "Software"), to deal in the Software without restriction, including
// without limitation the rights to use, copy, modify, merge, publish,
// distribute, sublicense, and/or sell copies of the Software, and to permit
// persons to whom the Software is furnished to do so, subject to the
// following conditions:
//
// The above copyright notice and this permission notice shall be included
// in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
// OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
// NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
// DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
// OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
// USE OR OTHER DEALINGS IN THE SOFTWARE.

var formatRegExp = /%[sdj%]/g;
exports.format = function(f) {
  if (!isString(f)) {
    var objects = [];
    for (var i = 0; i < arguments.length; i++) {
      objects.push(inspect(arguments[i]));
    }
    return objects.join(' ');
  }

  var i = 1;
  var args = arguments;
  var len = args.length;
  var str = String(f).replace(formatRegExp, function(x) {
    if (x === '%%') return '%';
    if (i >= len) return x;
    switch (x) {
      case '%s': return String(args[i++]);
      case '%d': return Number(args[i++]);
      case '%j':
        try {
          return JSON.stringify(args[i++]);
        } catch (_) {
          return '[Circular]';
        }
      default:
        return x;
    }
  });
  for (var x = args[i]; i < len; x = args[++i]) {
    if (isNull(x) || !isObject(x)) {
      str += ' ' + x;
    } else {
      str += ' ' + inspect(x);
    }
  }
  return str;
};


// Mark that a method should not be used.
// Returns a modified function which warns once by default.
// If --no-deprecation is set, then it is a no-op.
exports.deprecate = function(fn, msg) {
  // Allow for deprecating things in the process of starting up.
  if (isUndefined(global.process)) {
    return function() {
      return exports.deprecate(fn, msg).apply(this, arguments);
    };
  }

  if (process.noDeprecation === true) {
    return fn;
  }

  var warned = false;
  function deprecated() {
    if (!warned) {
      if (process.throwDeprecation) {
        throw new Error(msg);
      } else if (process.traceDeprecation) {
        console.trace(msg);
      } else {
        console.error(msg);
      }
      warned = true;
    }
    return fn.apply(this, arguments);
  }

  return deprecated;
};


var debugs = {};
var debugEnviron;
exports.debuglog = function(set) {
  if (isUndefined(debugEnviron))
    debugEnviron = process.env.NODE_DEBUG || '';
  set = set.toUpperCase();
  if (!debugs[set]) {
    if (new RegExp('\\b' + set + '\\b', 'i').test(debugEnviron)) {
      var pid = process.pid;
      debugs[set] = function() {
        var msg = exports.format.apply(exports, arguments);
        console.error('%s %d: %s', set, pid, msg);
      };
    } else {
      debugs[set] = function() {};
    }
  }
  return debugs[set];
};


/**
 * Echos the value of a value. Trys to print the value out
 * in the best way possible given the different types.
 *
 * @param {Object} obj The object to print out.
 * @param {Object} opts Optional options object that alters the output.
 */
/* legacy: obj, showHidden, depth, colors*/
function inspect(obj, opts) {
  // default options
  var ctx = {
    seen: [],
    stylize: stylizeNoColor
  };
  // legacy...
  if (arguments.length >= 3) ctx.depth = arguments[2];
  if (arguments.length >= 4) ctx.colors = arguments[3];
  if (isBoolean(opts)) {
    // legacy...
    ctx.showHidden = opts;
  } else if (opts) {
    // got an "options" object
    exports._extend(ctx, opts);
  }
  // set default options
  if (isUndefined(ctx.showHidden)) ctx.showHidden = false;
  if (isUndefined(ctx.depth)) ctx.depth = 2;
  if (isUndefined(ctx.colors)) ctx.colors = false;
  if (isUndefined(ctx.customInspect)) ctx.customInspect = true;
  if (ctx.colors) ctx.stylize = stylizeWithColor;
  return formatValue(ctx, obj, ctx.depth);
}
exports.inspect = inspect;


// http://en.wikipedia.org/wiki/ANSI_escape_code#graphics
inspect.colors = {
  'bold' : [1, 22],
  'italic' : [3, 23],
  'underline' : [4, 24],
  'inverse' : [7, 27],
  'white' : [37, 39],
  'grey' : [90, 39],
  'black' : [30, 39],
  'blue' : [34, 39],
  'cyan' : [36, 39],
  'green' : [32, 39],
  'magenta' : [35, 39],
  'red' : [31, 39],
  'yellow' : [33, 39]
};

// Don't use 'blue' not visible on cmd.exe
inspect.styles = {
  'special': 'cyan',
  'number': 'yellow',
  'boolean': 'yellow',
  'undefined': 'grey',
  'null': 'bold',
  'string': 'green',
  'date': 'magenta',
  // "name": intentionally not styling
  'regexp': 'red'
};


function stylizeWithColor(str, styleType) {
  var style = inspect.styles[styleType];

  if (style) {
    return '\u001b[' + inspect.colors[style][0] + 'm' + str +
           '\u001b[' + inspect.colors[style][1] + 'm';
  } else {
    return str;
  }
}


function stylizeNoColor(str, styleType) {
  return str;
}


function arrayToHash(array) {
  var hash = {};

  array.forEach(function(val, idx) {
    hash[val] = true;
  });

  return hash;
}


function formatValue(ctx, value, recurseTimes) {
  // Provide a hook for user-specified inspect functions.
  // Check that value is an object with an inspect function on it
  if (ctx.customInspect &&
      value &&
      isFunction(value.inspect) &&
      // Filter out the util module, it's inspect function is special
      value.inspect !== exports.inspect &&
      // Also filter out any prototype objects using the circular check.
      !(value.constructor && value.constructor.prototype === value)) {
    var ret = value.inspect(recurseTimes, ctx);
    if (!isString(ret)) {
      ret = formatValue(ctx, ret, recurseTimes);
    }
    return ret;
  }

  // Primitive types cannot have properties
  var primitive = formatPrimitive(ctx, value);
  if (primitive) {
    return primitive;
  }

  // Look up the keys of the object.
  var keys = Object.keys(value);
  var visibleKeys = arrayToHash(keys);

  if (ctx.showHidden) {
    keys = Object.getOwnPropertyNames(value);
  }

  // IE doesn't make error fields non-enumerable
  // http://msdn.microsoft.com/en-us/library/ie/dww52sbt(v=vs.94).aspx
  if (isError(value)
      && (keys.indexOf('message') >= 0 || keys.indexOf('description') >= 0)) {
    return formatError(value);
  }

  // Some type of object without properties can be shortcutted.
  if (keys.length === 0) {
    if (isFunction(value)) {
      var name = value.name ? ': ' + value.name : '';
      return ctx.stylize('[Function' + name + ']', 'special');
    }
    if (isRegExp(value)) {
      return ctx.stylize(RegExp.prototype.toString.call(value), 'regexp');
    }
    if (isDate(value)) {
      return ctx.stylize(Date.prototype.toString.call(value), 'date');
    }
    if (isError(value)) {
      return formatError(value);
    }
  }

  var base = '', array = false, braces = ['{', '}'];

  // Make Array say that they are Array
  if (isArray(value)) {
    array = true;
    braces = ['[', ']'];
  }

  // Make functions say that they are functions
  if (isFunction(value)) {
    var n = value.name ? ': ' + value.name : '';
    base = ' [Function' + n + ']';
  }

  // Make RegExps say that they are RegExps
  if (isRegExp(value)) {
    base = ' ' + RegExp.prototype.toString.call(value);
  }

  // Make dates with properties first say the date
  if (isDate(value)) {
    base = ' ' + Date.prototype.toUTCString.call(value);
  }

  // Make error with message first say the error
  if (isError(value)) {
    base = ' ' + formatError(value);
  }

  if (keys.length === 0 && (!array || value.length == 0)) {
    return braces[0] + base + braces[1];
  }

  if (recurseTimes < 0) {
    if (isRegExp(value)) {
      return ctx.stylize(RegExp.prototype.toString.call(value), 'regexp');
    } else {
      return ctx.stylize('[Object]', 'special');
    }
  }

  ctx.seen.push(value);

  var output;
  if (array) {
    output = formatArray(ctx, value, recurseTimes, visibleKeys, keys);
  } else {
    output = keys.map(function(key) {
      return formatProperty(ctx, value, recurseTimes, visibleKeys, key, array);
    });
  }

  ctx.seen.pop();

  return reduceToSingleString(output, base, braces);
}


function formatPrimitive(ctx, value) {
  if (isUndefined(value))
    return ctx.stylize('undefined', 'undefined');
  if (isString(value)) {
    var simple = '\'' + JSON.stringify(value).replace(/^"|"$/g, '')
                                             .replace(/'/g, "\\'")
                                             .replace(/\\"/g, '"') + '\'';
    return ctx.stylize(simple, 'string');
  }
  if (isNumber(value))
    return ctx.stylize('' + value, 'number');
  if (isBoolean(value))
    return ctx.stylize('' + value, 'boolean');
  // For some reason typeof null is "object", so special case here.
  if (isNull(value))
    return ctx.stylize('null', 'null');
}


function formatError(value) {
  return '[' + Error.prototype.toString.call(value) + ']';
}


function formatArray(ctx, value, recurseTimes, visibleKeys, keys) {
  var output = [];
  for (var i = 0, l = value.length; i < l; ++i) {
    if (hasOwnProperty(value, String(i))) {
      output.push(formatProperty(ctx, value, recurseTimes, visibleKeys,
          String(i), true));
    } else {
      output.push('');
    }
  }
  keys.forEach(function(key) {
    if (!key.match(/^\d+$/)) {
      output.push(formatProperty(ctx, value, recurseTimes, visibleKeys,
          key, true));
    }
  });
  return output;
}


function formatProperty(ctx, value, recurseTimes, visibleKeys, key, array) {
  var name, str, desc;
  desc = Object.getOwnPropertyDescriptor(value, key) || { value: value[key] };
  if (desc.get) {
    if (desc.set) {
      str = ctx.stylize('[Getter/Setter]', 'special');
    } else {
      str = ctx.stylize('[Getter]', 'special');
    }
  } else {
    if (desc.set) {
      str = ctx.stylize('[Setter]', 'special');
    }
  }
  if (!hasOwnProperty(visibleKeys, key)) {
    name = '[' + key + ']';
  }
  if (!str) {
    if (ctx.seen.indexOf(desc.value) < 0) {
      if (isNull(recurseTimes)) {
        str = formatValue(ctx, desc.value, null);
      } else {
        str = formatValue(ctx, desc.value, recurseTimes - 1);
      }
      if (str.indexOf('\n') > -1) {
        if (array) {
          str = str.split('\n').map(function(line) {
            return '  ' + line;
          }).join('\n').substr(2);
        } else {
          str = '\n' + str.split('\n').map(function(line) {
            return '   ' + line;
          }).join('\n');
        }
      }
    } else {
      str = ctx.stylize('[Circular]', 'special');
    }
  }
  if (isUndefined(name)) {
    if (array && key.match(/^\d+$/)) {
      return str;
    }
    name = JSON.stringify('' + key);
    if (name.match(/^"([a-zA-Z_][a-zA-Z_0-9]*)"$/)) {
      name = name.substr(1, name.length - 2);
      name = ctx.stylize(name, 'name');
    } else {
      name = name.replace(/'/g, "\\'")
                 .replace(/\\"/g, '"')
                 .replace(/(^"|"$)/g, "'");
      name = ctx.stylize(name, 'string');
    }
  }

  return name + ': ' + str;
}


function reduceToSingleString(output, base, braces) {
  var numLinesEst = 0;
  var length = output.reduce(function(prev, cur) {
    numLinesEst++;
    if (cur.indexOf('\n') >= 0) numLinesEst++;
    return prev + cur.replace(/\u001b\[\d\d?m/g, '').length + 1;
  }, 0);

  if (length > 60) {
    return braces[0] +
           (base === '' ? '' : base + '\n ') +
           ' ' +
           output.join(',\n  ') +
           ' ' +
           braces[1];
  }

  return braces[0] + base + ' ' + output.join(', ') + ' ' + braces[1];
}


// NOTE: These type checking functions intentionally don't use `instanceof`
// because it is fragile and can be easily faked with `Object.create()`.
function isArray(ar) {
  return Array.isArray(ar);
}
exports.isArray = isArray;

function isBoolean(arg) {
  return typeof arg === 'boolean';
}
exports.isBoolean = isBoolean;

function isNull(arg) {
  return arg === null;
}
exports.isNull = isNull;

function isNullOrUndefined(arg) {
  return arg == null;
}
exports.isNullOrUndefined = isNullOrUndefined;

function isNumber(arg) {
  return typeof arg === 'number';
}
exports.isNumber = isNumber;

function isString(arg) {
  return typeof arg === 'string';
}
exports.isString = isString;

function isSymbol(arg) {
  return typeof arg === 'symbol';
}
exports.isSymbol = isSymbol;

function isUndefined(arg) {
  return arg === void 0;
}
exports.isUndefined = isUndefined;

function isRegExp(re) {
  return isObject(re) && objectToString(re) === '[object RegExp]';
}
exports.isRegExp = isRegExp;

function isObject(arg) {
  return typeof arg === 'object' && arg !== null;
}
exports.isObject = isObject;

function isDate(d) {
  return isObject(d) && objectToString(d) === '[object Date]';
}
exports.isDate = isDate;

function isError(e) {
  return isObject(e) &&
      (objectToString(e) === '[object Error]' || e instanceof Error);
}
exports.isError = isError;

function isFunction(arg) {
  return typeof arg === 'function';
}
exports.isFunction = isFunction;

function isPrimitive(arg) {
  return arg === null ||
         typeof arg === 'boolean' ||
         typeof arg === 'number' ||
         typeof arg === 'string' ||
         typeof arg === 'symbol' ||  // ES6 symbol
         typeof arg === 'undefined';
}
exports.isPrimitive = isPrimitive;

exports.isBuffer = _dereq_('./support/isBuffer');

function objectToString(o) {
  return Object.prototype.toString.call(o);
}


function pad(n) {
  return n < 10 ? '0' + n.toString(10) : n.toString(10);
}


var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
              'Oct', 'Nov', 'Dec'];

// 26 Feb 16:19:34
function timestamp() {
  var d = new Date();
  var time = [pad(d.getHours()),
              pad(d.getMinutes()),
              pad(d.getSeconds())].join(':');
  return [d.getDate(), months[d.getMonth()], time].join(' ');
}


// log is just a thin wrapper to console.log that prepends a timestamp
exports.log = function() {
  console.log('%s - %s', timestamp(), exports.format.apply(exports, arguments));
};


/**
 * Inherit the prototype methods from one constructor into another.
 *
 * The Function.prototype.inherits from lang.js rewritten as a standalone
 * function (not on Function.prototype). NOTE: If this file is to be loaded
 * during bootstrapping this function needs to be rewritten using some native
 * functions as prototype setup using normal JavaScript does not work as
 * expected during bootstrapping (see mirror.js in r114903).
 *
 * @param {function} ctor Constructor function which needs to inherit the
 *     prototype.
 * @param {function} superCtor Constructor function to inherit prototype from.
 */
exports.inherits = _dereq_('inherits');

exports._extend = function(origin, add) {
  // Don't do anything if add isn't an object
  if (!add || !isObject(add)) return origin;

  var keys = Object.keys(add);
  var i = keys.length;
  while (i--) {
    origin[keys[i]] = add[keys[i]];
  }
  return origin;
};

function hasOwnProperty(obj, prop) {
  return Object.prototype.hasOwnProperty.call(obj, prop);
}

}).call(this,_dereq_("/usr/local/lib/node_modules/browserify/node_modules/insert-module-globals/node_modules/process/browser.js"),typeof self !== "undefined" ? self : typeof window !== "undefined" ? window : {})
},
{"./support/isBuffer":14,"/usr/local/lib/node_modules/browserify/node_modules/insert-module-globals/node_modules/process/browser.js":18,"inherits":17}],
16:[function(_dereq_,module,exports){
// Copyright Joyent, Inc. and other Node contributors.
//
// Permission is hereby granted, free of charge, to any person obtaining a
// copy of this software and associated documentation files (the
// "Software"), to deal in the Software without restriction, including
// without limitation the rights to use, copy, modify, merge, publish,
// distribute, sublicense, and/or sell copies of the Software, and to permit
// persons to whom the Software is furnished to do so, subject to the
// following conditions:
//
// The above copyright notice and this permission notice shall be included
// in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
// OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
// NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
// DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
// OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
// USE OR OTHER DEALINGS IN THE SOFTWARE.

function EventEmitter() {
  this._events = this._events || {};
  this._maxListeners = this._maxListeners || undefined;
}
module.exports = EventEmitter;

// Backwards-compat with node 0.10.x
EventEmitter.EventEmitter = EventEmitter;

EventEmitter.prototype._events = undefined;
EventEmitter.prototype._maxListeners = undefined;

// By default EventEmitters will print a warning if more than 10 listeners are
// added to it. This is a useful default which helps finding memory leaks.
EventEmitter.defaultMaxListeners = 10;

// Obviously not all Emitters should be limited to 10. This function allows
// that to be increased. Set to zero for unlimited.
EventEmitter.prototype.setMaxListeners = function(n) {
  if (!isNumber(n) || n < 0 || isNaN(n))
    throw TypeError('n must be a positive number');
  this._maxListeners = n;
  return this;
};

EventEmitter.prototype.emit = function(type) {
  var er, handler, len, args, i, listeners;

  if (!this._events)
    this._events = {};

  // If there is no 'error' event listener then throw.
  if (type === 'error') {
    if (!this._events.error ||
        (isObject(this._events.error) && !this._events.error.length)) {
      er = arguments[1];
      if (er instanceof Error) {
        throw er; // Unhandled 'error' event
      } else {
        throw TypeError('Uncaught, unspecified "error" event.');
      }
      return false;
    }
  }

  handler = this._events[type];

  if (isUndefined(handler))
    return false;

  if (isFunction(handler)) {
    switch (arguments.length) {
      // fast cases
      case 1:
        handler.call(this);
        break;
      case 2:
        handler.call(this, arguments[1]);
        break;
      case 3:
        handler.call(this, arguments[1], arguments[2]);
        break;
      // slower
      default:
        len = arguments.length;
        args = new Array(len - 1);
        for (i = 1; i < len; i++)
          args[i - 1] = arguments[i];
        handler.apply(this, args);
    }
  } else if (isObject(handler)) {
    len = arguments.length;
    args = new Array(len - 1);
    for (i = 1; i < len; i++)
      args[i - 1] = arguments[i];

    listeners = handler.slice();
    len = listeners.length;
    for (i = 0; i < len; i++)
      listeners[i].apply(this, args);
  }

  return true;
};

EventEmitter.prototype.addListener = function(type, listener) {
  var m;

  if (!isFunction(listener))
    throw TypeError('listener must be a function');

  if (!this._events)
    this._events = {};

  // To avoid recursion in the case that type === "newListener"! Before
  // adding it to the listeners, first emit "newListener".
  if (this._events.newListener)
    this.emit('newListener', type,
              isFunction(listener.listener) ?
              listener.listener : listener);

  if (!this._events[type])
    // Optimize the case of one listener. Don't need the extra array object.
    this._events[type] = listener;
  else if (isObject(this._events[type]))
    // If we've already got an array, just append.
    this._events[type].push(listener);
  else
    // Adding the second element, need to change to array.
    this._events[type] = [this._events[type], listener];

  // Check for listener leak
  if (isObject(this._events[type]) && !this._events[type].warned) {
    var m;
    if (!isUndefined(this._maxListeners)) {
      m = this._maxListeners;
    } else {
      m = EventEmitter.defaultMaxListeners;
    }

    if (m && m > 0 && this._events[type].length > m) {
      this._events[type].warned = true;
      console.error('(node) warning: possible EventEmitter memory ' +
                    'leak detected. %d listeners added. ' +
                    'Use emitter.setMaxListeners() to increase limit.',
                    this._events[type].length);
      console.trace();
    }
  }

  return this;
};

EventEmitter.prototype.on = EventEmitter.prototype.addListener;

EventEmitter.prototype.once = function(type, listener) {
  if (!isFunction(listener))
    throw TypeError('listener must be a function');

  var fired = false;

  function g() {
    this.removeListener(type, g);

    if (!fired) {
      fired = true;
      listener.apply(this, arguments);
    }
  }

  g.listener = listener;
  this.on(type, g);

  return this;
};

// emits a 'removeListener' event iff the listener was removed
EventEmitter.prototype.removeListener = function(type, listener) {
  var list, position, length, i;

  if (!isFunction(listener))
    throw TypeError('listener must be a function');

  if (!this._events || !this._events[type])
    return this;

  list = this._events[type];
  length = list.length;
  position = -1;

  if (list === listener ||
      (isFunction(list.listener) && list.listener === listener)) {
    delete this._events[type];
    if (this._events.removeListener)
      this.emit('removeListener', type, listener);

  } else if (isObject(list)) {
    for (i = length; i-- > 0;) {
      if (list[i] === listener ||
          (list[i].listener && list[i].listener === listener)) {
        position = i;
        break;
      }
    }

    if (position < 0)
      return this;

    if (list.length === 1) {
      list.length = 0;
      delete this._events[type];
    } else {
      list.splice(position, 1);
    }

    if (this._events.removeListener)
      this.emit('removeListener', type, listener);
  }

  return this;
};

EventEmitter.prototype.removeAllListeners = function(type) {
  var key, listeners;

  if (!this._events)
    return this;

  // not listening for removeListener, no need to emit
  if (!this._events.removeListener) {
    if (arguments.length === 0)
      this._events = {};
    else if (this._events[type])
      delete this._events[type];
    return this;
  }

  // emit removeListener for all listeners on all events
  if (arguments.length === 0) {
    for (key in this._events) {
      if (key === 'removeListener') continue;
      this.removeAllListeners(key);
    }
    this.removeAllListeners('removeListener');
    this._events = {};
    return this;
  }

  listeners = this._events[type];

  if (isFunction(listeners)) {
    this.removeListener(type, listeners);
  } else {
    // LIFO order
    while (listeners.length)
      this.removeListener(type, listeners[listeners.length - 1]);
  }
  delete this._events[type];

  return this;
};

EventEmitter.prototype.listeners = function(type) {
  var ret;
  if (!this._events || !this._events[type])
    ret = [];
  else if (isFunction(this._events[type]))
    ret = [this._events[type]];
  else
    ret = this._events[type].slice();
  return ret;
};

EventEmitter.listenerCount = function(emitter, type) {
  var ret;
  if (!emitter._events || !emitter._events[type])
    ret = 0;
  else if (isFunction(emitter._events[type]))
    ret = 1;
  else
    ret = emitter._events[type].length;
  return ret;
};

function isFunction(arg) {
  return typeof arg === 'function';
}

function isNumber(arg) {
  return typeof arg === 'number';
}

function isObject(arg) {
  return typeof arg === 'object' && arg !== null;
}

function isUndefined(arg) {
  return arg === void 0;
}

},
{}],
17:[function(_dereq_,module,exports){
if (typeof Object.create === 'function') {
  // implementation from standard node.js 'util' module
  module.exports = function inherits(ctor, superCtor) {
    ctor.super_ = superCtor
    ctor.prototype = Object.create(superCtor.prototype, {
      constructor: {
        value: ctor,
        enumerable: false,
        writable: true,
        configurable: true
      }
    });
  };
} else {
  // old school shim for old browsers
  module.exports = function inherits(ctor, superCtor) {
    ctor.super_ = superCtor
    var TempCtor = function () {}
    TempCtor.prototype = superCtor.prototype
    ctor.prototype = new TempCtor()
    ctor.prototype.constructor = ctor
  }
}

},
{}],
18:[function(_dereq_,module,exports){
// shim for using process in browser

var process = module.exports = {};

process.nextTick = (function () {
    var canSetImmediate = typeof window !== 'undefined'
    && window.setImmediate;
    var canPost = typeof window !== 'undefined'
    && window.postMessage && window.addEventListener
    ;

    if (canSetImmediate) {
        return function (f) { return window.setImmediate(f) };
    }

    if (canPost) {
        var queue = [];
        window.addEventListener('message', function (ev) {
            var source = ev.source;
            if ((source === window || source === null) && ev.data === 'process-tick') {
                ev.stopPropagation();
                if (queue.length > 0) {
                    var fn = queue.shift();
                    fn();
                }
            }
        }, true);

        return function nextTick(fn) {
            queue.push(fn);
            window.postMessage('process-tick', '*');
        };
    }

    return function nextTick(fn) {
        setTimeout(fn, 0);
    };
})();

process.title = 'browser';
process.browser = true;
process.env = {};
process.argv = [];

function noop() {}

process.on = noop;
process.once = noop;
process.off = noop;
process.emit = noop;

process.binding = function (name) {
    throw new Error('process.binding is not supported');
}

// TODO(shtylman)
process.cwd = function () { return '/' };
process.chdir = function (dir) {
    throw new Error('process.chdir is not supported');
};

},
{}],
19:[function(_dereq_,module,exports){
module.exports=_dereq_(14)
},
{}],
20:[function(_dereq_,module,exports){
module.exports=_dereq_(15)
},
{"./support/isBuffer":19,"/usr/local/lib/node_modules/browserify/node_modules/insert-module-globals/node_modules/process/browser.js":18,"inherits":17}]},{},[9])
(9)

});