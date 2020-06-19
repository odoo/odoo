# The MIT License
#
# Copyright 2014, 2015 Piotr Dabkowski
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the 'Software'),
# to deal in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so, subject
# to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
#  OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
from __future__ import unicode_literals
from .pyjsparserdata import *
from .std_nodes import *
from pprint import pprint
import sys

__all__ = ['PyJsParser', 'parse', 'ENABLE_JS2PY_ERRORS', 'ENABLE_PYIMPORT', 'JsSyntaxError']
REGEXP_SPECIAL_SINGLE = ('\\', '^', '$', '*', '+', '?', '.', '[', ']', '(', ')', '{', '{', '|', '-')
ENABLE_PYIMPORT = False
ENABLE_JS2PY_ERRORS = False
ESPRIMA_VERSION = '2.2.0'

DEBUG = False
# Small naming convention changes
# len -> leng
# id -> d
# type -> typ
# str -> st
true = True
false = False
null = None


class PyJsParser:
    """ Usage:
        parser = PyJsParser()
        parser.parse('var JavaScriptCode = 5.1')
    """

    def __init__(self):
        self.clean()

    def test(self, code):
        pprint(self.parse(code))

    def clean(self):
        self.strict = None
        self.sourceType = None
        self.index = 0
        self.lineNumber = 1
        self.lineStart = 0
        self.hasLineTerminator = None
        self.lastIndex = None
        self.lastLineNumber = None
        self.lastLineStart = None
        self.startIndex = None
        self.startLineNumber = None
        self.startLineStart = None
        self.scanning = None
        self.lookahead = None
        self.state = None
        self.extra = None
        self.isBindingElement = None
        self.isAssignmentTarget = None
        self.firstCoverInitializedNameError = None

    # 7.4 Comments

    def skipSingleLineComment(self, offset):
        start = self.index - offset;
        while self.index < self.length:
            ch = self.source[self.index];
            self.index += 1
            if isLineTerminator(ch):
                if (ord(ch) == 13 and ord(self.source[self.index]) == 10):
                    self.index += 1
                self.lineNumber += 1
                self.hasLineTerminator = True
                self.lineStart = self.index
                return {
                    'type': 'Line',
                    'value': self.source[start + offset:self.index-2],
                    'leading': True,
                    'trailing': False,
                    'loc': None,
                }

    def skipMultiLineComment(self):
        start = self.index
        while self.index < self.length:
            ch = ord(self.source[self.index])
            if isLineTerminator(ch):
                if (ch == 0x0D and ord(self.source[self.index + 1]) == 0x0A):
                    self.index += 1
                self.lineNumber += 1
                self.index += 1
                self.hasLineTerminator = True
                self.lineStart = self.index
            elif ch == 0x2A:
                # Block comment ends with '*/'.
                if ord(self.source[self.index + 1]) == 0x2F:
                    self.index += 2
                    return {
                        'type': 'Block',
                        'value': self.source[start:self.index-2],
                        'leading': True,
                        'trailing': False,
                        'loc': None,
                    }
                self.index += 1
            else:
                self.index += 1
        self.tolerateUnexpectedToken()

    def skipComment(self):
        self.hasLineTerminator = False
        startIndex = self.index
        start = (self.index == 0)
        comments = []
        while self.index < self.length:
            ch = ord(self.source[self.index])
            if isWhiteSpace(ch):
                self.index += 1
            elif isLineTerminator(ch):
                self.hasLineTerminator = True
                self.index += 1
                if (ch == 0x0D and ord(self.source[self.index]) == 0x0A):
                    self.index += 1
                self.lineNumber += 1
                self.lineStart = self.index
                start = True
            elif (ch == 0x2F):  # U+002F is '/'
                ch = ord(self.source[self.index + 1])
                if (ch == 0x2F):
                    self.index += 2
                    comments.append(self.skipSingleLineComment(2))
                    start = True
                elif (ch == 0x2A):  # U+002A is '*'
                    self.index += 2
                    comments.append(self.skipMultiLineComment())
                else:
                    break
            elif (start and ch == 0x2D):  # U+002D is '-'
                # U+003E is '>'
                if (ord(self.source[self.index + 1]) == 0x2D) and (ord(self.source[self.index + 2]) == 0x3E):
                    # '-->' is a single-line comment
                    self.index += 3
                    self.skipSingleLineComment(3)
                else:
                    break
            elif (ch == 0x3C):  # U+003C is '<'
                if self.source[self.index + 1: self.index + 4] == '!--':
                    # <!--
                    self.index += 4
                    self.skipSingleLineComment(4)
                else:
                    break
            else:
                break
        return [c for c in comments if c]

    def scanHexEscape(self, prefix):
        code = 0
        leng = 4 if (prefix == 'u') else 2
        for i in range(leng):
            if self.index < self.length and isHexDigit(self.source[self.index]):
                ch = self.source[self.index]
                self.index += 1
                code = code * 16 + HEX_CONV[ch]
            else:
                return ''
        return chr(code)

    def scanUnicodeCodePointEscape(self):
        ch = self.source[self.index]
        code = 0
        # At least, one hex digit is required.
        if ch == '}':
            self.throwUnexpectedToken()
        while (self.index < self.length):
            ch = self.source[self.index]
            self.index += 1
            if not isHexDigit(ch):
                break
            code = code * 16 + HEX_CONV[ch]
        if code > 0x10FFFF or ch != '}':
            self.throwUnexpectedToken()
        # UTF-16 Encoding
        if (code <= 0xFFFF):
            return chr(code)
        cu1 = ((code - 0x10000) >> 10) + 0xD800;
        cu2 = ((code - 0x10000) & 1023) + 0xDC00;
        return chr(cu1) + chr(cu2)

    def ccode(self, offset=0):
        return ord(self.source[self.index + offset])

    def log_err_case(self):
        if not DEBUG:
            return
        print('INDEX', self.index)
        print(self.source[self.index - 10:self.index + 10])
        print('')

    def at(self, loc):
        return None if loc >= self.length else self.source[loc]

    def substr(self, le, offset=0):
        return self.source[self.index + offset:self.index + offset + le]

    def getEscapedIdentifier(self):
        d = self.source[self.index]
        ch = ord(d)
        self.index += 1
        # '\u' (U+005C, U+0075) denotes an escaped character.
        if (ch == 0x5C):
            if (ord(self.source[self.index]) != 0x75):
                self.throwUnexpectedToken()
            self.index += 1
            ch = self.scanHexEscape('u')
            if not ch or ch == '\\' or not isIdentifierStart(ch[0]):
                self.throwUnexpectedToken()
            d = ch
        while (self.index < self.length):
            ch = self.ccode()
            if not isIdentifierPart(ch):
                break
            self.index += 1
            d += unichr(ch)

            # '\u' (U+005C, U+0075) denotes an escaped character.
            if (ch == 0x5C):
                d = d[0: len(d) - 1]
                if (self.ccode() != 0x75):
                    self.throwUnexpectedToken()
                self.index += 1
                ch = self.scanHexEscape('u');
                if (not ch or ch == '\\' or not isIdentifierPart(ch[0])):
                    self.throwUnexpectedToken()
                d += ch
        return d

    def getIdentifier(self):
        start = self.index
        self.index += 1
        while (self.index < self.length):
            ch = self.ccode()
            if (ch == 0x5C):
                # Blackslash (U+005C) marks Unicode escape sequence.
                self.index = start
                return self.getEscapedIdentifier()
            if (isIdentifierPart(ch)):
                self.index += 1
            else:
                break
        return self.source[start: self.index]

    def scanIdentifier(self):
        start = self.index

        # Backslash (U+005C) starts an escaped character.
        d = self.getEscapedIdentifier() if (self.ccode() == 0x5C) else self.getIdentifier()

        # There is no keyword or literal with only one character.
        # Thus, it must be an identifier.
        if (len(d) == 1):
            type = Token.Identifier
        elif (isKeyword(d)):
            type = Token.Keyword
        elif (d == 'null'):
            type = Token.NullLiteral
        elif (d == 'true' or d == 'false'):
            type = Token.BooleanLiteral
        else:
            type = Token.Identifier;
        return {
            'type': type,
            'value': d,
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index
        }

    # 7.7 Punctuators

    def scanPunctuator(self):
        token = {
            'type': Token.Punctuator,
            'value': '',
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': self.index,
            'end': self.index
        }
        # Check for most common single-character punctuators.
        st = self.source[self.index]
        if st == '{':
            self.state['curlyStack'].append('{')
            self.index += 1
        elif st == '}':
            self.index += 1
            self.state['curlyStack'].pop()
        elif st in ('.', '(', ')', ';', ',', '[', ']', ':', '?', '~'):
            self.index += 1
        else:
            # 4-character punctuator.
            st = self.substr(4)
            if (st == '>>>='):
                self.index += 4
            else:
                # 3-character punctuators.
                st = st[0:3]
                if st in ('===', '!==', '>>>', '<<=', '>>='):
                    self.index += 3
                else:
                    # 2-character punctuators.
                    st = st[0:2]
                    if st in ('&&', '||', '==', '!=', '+=', '-=', '*=', '/=', '++', '--', '<<', '>>', '&=', '|=', '^=',
                              '%=', '<=', '>=', '=>'):
                        self.index += 2
                    else:
                        # 1-character punctuators.
                        st = self.source[self.index]
                        if st in ('<', '>', '=', '!', '+', '-', '*', '%', '&', '|', '^', '/'):
                            self.index += 1
        if self.index == token['start']:
            self.throwUnexpectedToken()
        token['end'] = self.index;
        token['value'] = st
        return token

    # 7.8.3 Numeric Literals

    def scanHexLiteral(self, start):
        number = ''
        while (self.index < self.length):
            if (not isHexDigit(self.source[self.index])):
                break
            number += self.source[self.index]
            self.index += 1
        if not number:
            self.throwUnexpectedToken()
        if isIdentifierStart(self.ccode()):
            self.throwUnexpectedToken()
        return {
            'type': Token.NumericLiteral,
            'value': int(number, 16),
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index}

    def scanBinaryLiteral(self, start):
        number = ''
        while (self.index < self.length):
            ch = self.source[self.index]
            if (ch != '0' and ch != '1'):
                break
            number += self.source[self.index]
            self.index += 1

        if not number:
            # only 0b or 0B
            self.throwUnexpectedToken()
        if (self.index < self.length):
            ch = self.source[self.index]
            # istanbul ignore else
            if (isIdentifierStart(ch) or isDecimalDigit(ch)):
                self.throwUnexpectedToken();
        return {
            'type': Token.NumericLiteral,
            'value': int(number, 2),
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index}

    def scanOctalLiteral(self, prefix, start):
        if isOctalDigit(prefix):
            octal = True
            number = '0' + self.source[self.index]
            self.index += 1
        else:
            octal = False
            self.index += 1
            number = ''
        while (self.index < self.length):
            if (not isOctalDigit(self.source[self.index])):
                break
            number += self.source[self.index]
            self.index += 1
        if (not octal and not number):
            # only 0o or 0O
            self.throwUnexpectedToken()
        if (isIdentifierStart(self.ccode()) or isDecimalDigit(self.ccode())):
            self.throwUnexpectedToken()
        return {
            'type': Token.NumericLiteral,
            'value': int(number, 8),
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index}

    def octalToDecimal(self, ch):
        # \0 is not octal escape sequence
        octal = (ch != '0')
        code = int(ch, 8)

        if (self.index < self.length and isOctalDigit(self.source[self.index])):
            octal = True
            code = code * 8 + int(self.source[self.index], 8)
            self.index += 1

            # 3 digits are only allowed when string starts
            # with 0, 1, 2, 3
            if (ch in '0123' and self.index < self.length and isOctalDigit(self.source[self.index])):
                code = code * 8 + int((self.source[self.index]), 8)
                self.index += 1
        return {
            'code': code,
            'octal': octal}

    def isImplicitOctalLiteral(self):
        # Implicit octal, unless there is a non-octal digit.
        # (Annex B.1.1 on Numeric Literals)
        for i in range(self.index + 1, self.length):
            ch = self.source[i];
            if (ch == '8' or ch == '9'):
                return False;
            if (not isOctalDigit(ch)):
                return True
        return True

    def scanNumericLiteral(self):
        ch = self.source[self.index]
        assert isDecimalDigit(ch) or (ch == '.'), 'Numeric literal must start with a decimal digit or a decimal point'
        start = self.index
        number = ''
        if ch != '.':
            number = self.source[self.index]
            self.index += 1
            ch = self.source[self.index]
            # Hex number starts with '0x'.
            # Octal number starts with '0'.
            # Octal number in ES6 starts with '0o'.
            # Binary number in ES6 starts with '0b'.
            if (number == '0'):
                if (ch == 'x' or ch == 'X'):
                    self.index += 1
                    return self.scanHexLiteral(start);
                if (ch == 'b' or ch == 'B'):
                    self.index += 1
                    return self.scanBinaryLiteral(start)
                if (ch == 'o' or ch == 'O'):
                    return self.scanOctalLiteral(ch, start)
                if (isOctalDigit(ch)):
                    if (self.isImplicitOctalLiteral()):
                        return self.scanOctalLiteral(ch, start);
            while (isDecimalDigit(self.ccode())):
                number += self.source[self.index]
                self.index += 1
            ch = self.source[self.index];
        if (ch == '.'):
            number += self.source[self.index]
            self.index += 1
            while (isDecimalDigit(self.source[self.index])):
                number += self.source[self.index]
                self.index += 1
            ch = self.source[self.index]
        if (ch == 'e' or ch == 'E'):
            number += self.source[self.index]
            self.index += 1
            ch = self.source[self.index]
            if (ch == '+' or ch == '-'):
                number += self.source[self.index]
                self.index += 1
            if (isDecimalDigit(self.source[self.index])):
                while (isDecimalDigit(self.source[self.index])):
                    number += self.source[self.index]
                    self.index += 1
            else:
                self.throwUnexpectedToken()
        if (isIdentifierStart(self.source[self.index])):
            self.throwUnexpectedToken();
        return {
            'type': Token.NumericLiteral,
            'value': float(number),
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index}

    # 7.8.4 String Literals

    def _interpret_regexp(self, string, flags):
        '''Perform sctring escape - for regexp literals'''
        self.index = 0
        self.length = len(string)
        self.source = string
        self.lineNumber = 0
        self.lineStart = 0
        octal = False
        st = ''
        inside_square = 0
        while (self.index < self.length):
            template = '[%s]' if not inside_square else '%s'
            ch = self.source[self.index]
            self.index += 1
            if ch == '\\':
                ch = self.source[self.index]
                self.index += 1
                if (not isLineTerminator(ch)):
                    if ch == 'u':
                        digs = self.source[self.index:self.index + 4]
                        if len(digs) == 4 and all(isHexDigit(d) for d in digs):
                            st += template % chr(int(digs, 16))
                            self.index += 4
                        else:
                            st += 'u'
                    elif ch == 'x':
                        digs = self.source[self.index:self.index + 2]
                        if len(digs) == 2 and all(isHexDigit(d) for d in digs):
                            st += template % chr(int(digs, 16))
                            self.index += 2
                        else:
                            st += 'x'
                    # special meaning - single char.
                    elif ch == '0':
                        st += '\\0'
                    elif ch == 'n':
                        st += '\\n'
                    elif ch == 'r':
                        st += '\\r'
                    elif ch == 't':
                        st += '\\t'
                    elif ch == 'f':
                        st += '\\f'
                    elif ch == 'v':
                        st += '\\v'

                    # unescape special single characters like . so that they are interpreted literally
                    elif ch in REGEXP_SPECIAL_SINGLE:
                        st += '\\' + ch

                    # character groups
                    elif ch == 'b':
                        st += '\\b'
                    elif ch == 'B':
                        st += '\\B'
                    elif ch == 'w':
                        st += '\\w'
                    elif ch == 'W':
                        st += '\\W'
                    elif ch == 'd':
                        st += '\\d'
                    elif ch == 'D':
                        st += '\\D'
                    elif ch == 's':
                        st += template % u' \f\n\r\t\v\u00a0\u1680\u180e\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff'
                    elif ch == 'S':
                        st += template % u'\u0000-\u0008\u000e-\u001f\u0021-\u009f\u00a1-\u167f\u1681-\u180d\u180f-\u1fff\u200b-\u2027\u202a-\u202e\u2030-\u205e\u2060-\u2fff\u3001-\ufefe\uff00-\uffff'
                    else:
                        if isDecimalDigit(ch):
                            num = ch
                            while self.index < self.length and isDecimalDigit(self.source[self.index]):
                                num += self.source[self.index]
                                self.index += 1
                            st += '\\' + num

                        else:
                            st += ch  # DONT ESCAPE!!!
                else:
                    self.lineNumber += 1
                    if (ch == '\r' and self.source[self.index] == '\n'):
                        self.index += 1
                    self.lineStart = self.index
            else:
                if ch == '[':
                    inside_square = True
                elif ch == ']':
                    inside_square = False
                st += ch
        # print string, 'was transformed to', st
        return st

    def scanStringLiteral(self):
        st = ''
        octal = False

        quote = self.source[self.index]
        assert quote == '\'' or quote == '"', 'String literal must starts with a quote'
        start = self.index;
        self.index += 1

        while (self.index < self.length):
            ch = self.source[self.index]
            self.index += 1
            if (ch == quote):
                quote = ''
                break
            elif (ch == '\\'):
                ch = self.source[self.index]
                self.index += 1
                if (not isLineTerminator(ch)):
                    if ch in 'ux':
                        if (self.source[self.index] == '{'):
                            self.index += 1
                            st += self.scanUnicodeCodePointEscape()
                        else:
                            unescaped = self.scanHexEscape(ch)
                            if (not unescaped):
                                self.throwUnexpectedToken()  # with throw I don't know whats the difference
                            st += unescaped
                    elif ch == 'n':
                        st += '\n';
                    elif ch == 'r':
                        st += '\r';
                    elif ch == 't':
                        st += '\t';
                    elif ch == 'b':
                        st += '\b';
                    elif ch == 'f':
                        st += '\f';
                    elif ch == 'v':
                        st += '\x0B'
                    # elif ch in '89':
                    #    self.throwUnexpectedToken() # again with throw....
                    else:
                        if isOctalDigit(ch):
                            octToDec = self.octalToDecimal(ch)
                            octal = octToDec.get('octal') or octal
                            st += unichr(octToDec['code'])
                        else:
                            st += ch
                else:
                    self.lineNumber += 1
                    if (ch == '\r' and self.source[self.index] == '\n'):
                        self.index += 1
                    self.lineStart = self.index
            elif isLineTerminator(ch):
                break
            else:
                st += ch;
        if (quote != ''):
            self.throwUnexpectedToken()
        return {
            'type': Token.StringLiteral,
            'value': st,
            'octal': octal,
            'lineNumber': self.lineNumber,
            'lineStart': self.startLineStart,
            'start': start,
            'end': self.index}

    def scanTemplate(self):
        cooked = ''
        terminated = False
        tail = False
        start = self.index
        head = (self.source[self.index] == '`')
        rawOffset = 2

        self.index += 1

        while (self.index < self.length):
            ch = self.source[self.index]
            self.index += 1
            if (ch == '`'):
                rawOffset = 1;
                tail = True
                terminated = True
                break
            elif (ch == '$'):
                if (self.source[self.index] == '{'):
                    self.state['curlyStack'].append('${')
                    self.index += 1
                    terminated = True
                    break;
                cooked += ch
            elif (ch == '\\'):
                ch = self.source[self.index]
                self.index += 1
                if (not isLineTerminator(ch)):
                    if ch == 'n':
                        cooked += '\n'
                    elif ch == 'r':
                        cooked += '\r'
                    elif ch == 't':
                        cooked += '\t'
                    elif ch in 'ux':
                        if (self.source[self.index] == '{'):
                            self.index += 1
                            cooked += self.scanUnicodeCodePointEscape()
                        else:
                            restore = self.index
                            unescaped = self.scanHexEscape(ch)
                            if (unescaped):
                                cooked += unescaped
                            else:
                                self.index = restore
                                cooked += ch
                    elif ch == 'b':
                        cooked += '\b'
                    elif ch == 'f':
                        cooked += '\f'
                    elif ch == 'v':
                        cooked += '\v'
                    else:
                        if (ch == '0'):
                            if isDecimalDigit(self.ccode()):
                                # Illegal: \01 \02 and so on
                                self.throwError(Messages.TemplateOctalLiteral)
                            cooked += '\0'
                        elif (isOctalDigit(ch)):
                            # Illegal: \1 \2
                            self.throwError(Messages.TemplateOctalLiteral)
                        else:
                            cooked += ch
                else:
                    self.lineNumber += 1
                    if (ch == '\r' and self.source[self.index] == '\n'):
                        self.index += 1
                    self.lineStart = self.index
            elif (isLineTerminator(ch)):
                self.lineNumber += 1
                if (ch == '\r' and self.source[self.index] == '\n'):
                    self.index += 1
                self.lineStart = self.index
                cooked += '\n'
            else:
                cooked += ch;
        if (not terminated):
            self.throwUnexpectedToken()

        if (not head):
            self.state['curlyStack'].pop();

        return {
            'type': Token.Template,
            'value': {
                'cooked': cooked,
                'raw': self.source[start + 1:self.index - rawOffset]},
            'head': head,
            'tail': tail,
            'lineNumber': self.lineNumber,
            'lineStart': self.lineStart,
            'start': start,
            'end': self.index}

    def testRegExp(self, pattern, flags):
        # todo: you should return python regexp object
        return (pattern, flags)

    def scanRegExpBody(self):
        ch = self.source[self.index]
        assert ch == '/', 'Regular expression literal must start with a slash'
        st = ch
        self.index += 1

        classMarker = False
        terminated = False
        while (self.index < self.length):
            ch = self.source[self.index]
            self.index += 1
            st += ch
            if (ch == '\\'):
                ch = self.source[self.index]
                self.index += 1
                # ECMA-262 7.8.5
                if (isLineTerminator(ch)):
                    self.throwUnexpectedToken(None, Messages.UnterminatedRegExp)
                st += ch
            elif (isLineTerminator(ch)):
                self.throwUnexpectedToken(None, Messages.UnterminatedRegExp)
            elif (classMarker):
                if (ch == ']'):
                    classMarker = False
            else:
                if (ch == '/'):
                    terminated = True
                    break
                elif (ch == '['):
                    classMarker = True;
        if (not terminated):
            self.throwUnexpectedToken(None, Messages.UnterminatedRegExp)

        # Exclude leading and trailing slash.
        body = st[1:-1]
        return {
            'value': body,
            'literal': st}

    def scanRegExpFlags(self):
        st = ''
        flags = ''
        while (self.index < self.length):
            ch = self.source[self.index]
            if (not isIdentifierPart(ch)):
                break
            self.index += 1
            if (ch == '\\' and self.index < self.length):
                ch = self.source[self.index]
                if (ch == 'u'):
                    self.index += 1
                    restore = self.index
                    ch = self.scanHexEscape('u')
                    if (ch):
                        flags += ch
                        st += '\\u'
                        while restore < self.index:
                            st += self.source[restore]
                            restore += 1
                    else:
                        self.index = restore
                        flags += 'u'
                        st += '\\u'
                    self.tolerateUnexpectedToken()
                else:
                    st += '\\'
                    self.tolerateUnexpectedToken()
            else:
                flags += ch
                st += ch
        return {
            'value': flags,
            'literal': st}

    def scanRegExp(self, comments):
        self.scanning = True
        self.lookahead = None
        comments.extend(self.skipComment())
        start = self.index

        body = self.scanRegExpBody()
        flags = self.scanRegExpFlags()
        value = self.testRegExp(body['value'], flags['value'])
        scanning = False
        return {
            'literal': body['literal'] + flags['literal'],
            'value': value,
            'regex': {
                'pattern': body['value'],
                'flags': flags['value']
            },
            'start': start,
            'end': self.index,
            'comments': comments}

    def collectRegex(self):
        return self.scanRegExp(self.skipComment())

    def isIdentifierName(self, token):
        return token['type'] in (1, 3, 4, 5)

    # def advanceSlash(self): ???

    def advanceWithComments(self, comments):
        token = self.advance()
        token['comments'] = comments
        return token

    def advance(self):
        if (self.index >= self.length):
            return {
                'type': Token.EOF,
                'lineNumber': self.lineNumber,
                'lineStart': self.lineStart,
                'start': self.index,
                'end': self.index}
        ch = self.ccode()

        if isIdentifierStart(ch):
            token = self.scanIdentifier()
            if (self.strict and isStrictModeReservedWord(token['value'])):
                token['type'] = Token.Keyword
            return token
        # Very common: ( and ) and ;
        if (ch == 0x28 or ch == 0x29 or ch == 0x3B):
            return self.scanPunctuator()

        # String literal starts with single quote (U+0027) or double quote (U+0022).
        if (ch == 0x27 or ch == 0x22):
            return self.scanStringLiteral()

        # Dot (.) U+002E can also start a floating-point number, hence the need
        # to check the next character.
        if (ch == 0x2E):
            if (isDecimalDigit(self.ccode(1))):
                return self.scanNumericLiteral()
            return self.scanPunctuator();

        if (isDecimalDigit(ch)):
            return self.scanNumericLiteral()

        # Slash (/) U+002F can also start a regex.
        # if (extra.tokenize && ch == 0x2F):
        #    return advanceSlash();

        # Template literals start with ` (U+0060) for template head
        # or } (U+007D) for template middle or template tail.
        if (ch == 0x60 or (ch == 0x7D and self.state['curlyStack'][len(self.state['curlyStack']) - 1] == '${')):
            return self.scanTemplate()
        return self.scanPunctuator();

    # def collectToken(self):
    #    loc = {
    #        'start': {
    #            'line': self.lineNumber,
    #            'column': self.index - self.lineStart}}
    #
    #    token = self.advance()
    #
    #    loc['end'] = {
    #        'line': self.lineNumber,
    #        'column': self.index - self.lineStart}
    #    if (token['type'] != Token.EOF):
    #        value = self.source[token['start']: token['end']]
    #        entry = {
    #            'type': TokenName[token['type']],
    #            'value': value,
    #            'range': [token['start'], token['end']],
    #            'loc': loc}
    #        if (token.get('regex')):
    #            entry['regex'] = {
    #                'pattern': token['regex']['pattern'],
    #                'flags': token['regex']['flags']}
    #        self.extra['tokens'].append(entry)
    #    return token;


    def lex(self):
        self.scanning = True

        self.lastIndex = self.index
        self.lastLineNumber = self.lineNumber
        self.lastLineStart = self.lineStart

        comments = self.skipComment()

        token = self.lookahead

        self.startIndex = self.index
        self.startLineNumber = self.lineNumber
        self.startLineStart = self.lineStart

        self.lookahead = self.advanceWithComments(comments)
        self.scanning = False
        return token

    def peek(self):
        self.scanning = True

        comments = self.skipComment()

        self.lastIndex = self.index
        self.lastLineNumber = self.lineNumber
        self.lastLineStart = self.lineStart

        self.startIndex = self.index
        self.startLineNumber = self.lineNumber
        self.startLineStart = self.lineStart

        self.lookahead = self.advanceWithComments(comments)
        self.scanning = False

    def createError(self, line, pos, description):
        global ENABLE_PYIMPORT
        if ENABLE_JS2PY_ERRORS:
            old_pyimport = ENABLE_PYIMPORT  # ENABLE_PYIMPORT will be affected by js2py import
            self.log_err_case()
            try:
                from js2py.base import ERRORS, Js, JsToPyException
            except:
                raise Exception("ENABLE_JS2PY_ERRORS was set to True, but Js2Py was not found!")
            ENABLE_PYIMPORT = old_pyimport
            error = ERRORS['SyntaxError']('Line ' + str(line) + ': ' + str(description))
            error.put('index', Js(pos))
            error.put('lineNumber', Js(line))
            error.put('column', Js(pos - (self.lineStart if self.scanning else self.lastLineStart) + 1))
            error.put('description', Js(description))
            return JsToPyException(error)
        else:
            return JsSyntaxError('Line ' + str(line) + ': ' + str(description))


    # Throw an exception

    def throwError(self, messageFormat, *args):
        msg = messageFormat % tuple(str(e) for e in args)
        raise self.createError(self.lastLineNumber, self.lastIndex, msg);

    def tolerateError(self, messageFormat, *args):
        return self.throwError(messageFormat, *args)

    # Throw an exception because of the token.

    def unexpectedTokenError(self, token={}, message=''):
        msg = message or Messages.UnexpectedToken
        if (token):
            typ = token['type']
            if (not message):
                if typ == Token.EOF:
                    msg = Messages.UnexpectedEOS
                elif (typ == Token.Identifier):
                    msg = Messages.UnexpectedIdentifier
                elif (typ == Token.NumericLiteral):
                    msg = Messages.UnexpectedNumber
                elif (typ == Token.StringLiteral):
                    msg = Messages.UnexpectedString
                elif (typ == Token.Template):
                    msg = Messages.UnexpectedTemplate
                else:
                    msg = Messages.UnexpectedToken;
                if (typ == Token.Keyword):
                    if (isFutureReservedWord(token['value'])):
                        msg = Messages.UnexpectedReserved
                    elif (self.strict and isStrictModeReservedWord(token['value'])):
                        msg = Messages.StrictReservedWord
            value = token['value']['raw'] if (typ == Token.Template)  else token.get('value')
        else:
            value = 'ILLEGAL'
        msg = msg.replace('%s', str(value))

        return (self.createError(token['lineNumber'], token['start'], msg) if (token and token.get('lineNumber')) else
                self.createError(self.lineNumber if self.scanning else self.lastLineNumber,
                                 self.index if self.scanning else self.lastIndex, msg))

    def throwUnexpectedToken(self, token={}, message=''):
        raise self.unexpectedTokenError(token, message)

    def tolerateUnexpectedToken(self, token={}, message=''):
        self.throwUnexpectedToken(token, message)

    # Expect the next token to match the specified punctuator.
    # If not, an exception will be thrown.

    def expect(self, value):
        token = self.lex()
        if (token['type'] != Token.Punctuator or token['value'] != value):
            self.throwUnexpectedToken(token)

    # /**
    # * @name expectCommaSeparator
    # * @description Quietly expect a comma when in tolerant mode, otherwise delegates
    # * to <code>expect(value)</code>
    # * @since 2.0
    # */
    def expectCommaSeparator(self):
        self.expect(',')

    # Expect the next token to match the specified keyword.
    # If not, an exception will be thrown.

    def expectKeyword(self, keyword):
        token = self.lex();
        if (token['type'] != Token.Keyword or token['value'] != keyword):
            self.throwUnexpectedToken(token)

    # Return true if the next token matches the specified punctuator.

    def match(self, value):
        return self.lookahead['type'] == Token.Punctuator and self.lookahead['value'] == value

    # Return true if the next token matches the specified keyword

    def matchKeyword(self, keyword):
        return self.lookahead['type'] == Token.Keyword and self.lookahead['value'] == keyword

    # Return true if the next token matches the specified contextual keyword
    # (where an identifier is sometimes a keyword depending on the context)

    def matchContextualKeyword(self, keyword):
        return self.lookahead['type'] == Token.Identifier and self.lookahead['value'] == keyword

    # Return true if the next token is an assignment operator

    def matchAssign(self):
        if (self.lookahead['type'] != Token.Punctuator):
            return False;
        op = self.lookahead['value']
        return op in ('=', '*=', '/=', '%=', '+=', '-=', '<<=', '>>=', '>>>=', '&=', '^=', '|=')

    def consumeSemicolon(self):
        # Catch the very common case first: immediately a semicolon (U+003B).

        if (self.at(self.startIndex) == ';' or self.match(';')):
            self.lex()
            return

        if (self.hasLineTerminator):
            return

        # TODO: FIXME(ikarienator): this is seemingly an issue in the previous location info convention.
        self.lastIndex = self.startIndex
        self.lastLineNumber = self.startLineNumber
        self.lastLineStart = self.startLineStart

        if (self.lookahead['type'] != Token.EOF and not self.match('}')):
            self.throwUnexpectedToken(self.lookahead)

    # // Cover grammar support.
    # //
    # // When an assignment expression position starts with an left parenthesis, the determination of the type
    # // of the syntax is to be deferred arbitrarily long until the end of the parentheses pair (plus a lookahead)
    # // or the first comma. This situation also defers the determination of all the expressions nested in the pair.
    # //
    # // There are three productions that can be parsed in a parentheses pair that needs to be determined
    # // after the outermost pair is closed. They are:
    # //
    # //   1. AssignmentExpression
    # //   2. BindingElements
    # //   3. AssignmentTargets
    # //
    # // In order to avoid exponential backtracking, we use two flags to denote if the production can be
    # // binding element or assignment target.
    # //
    # // The three productions have the relationship:
    # //
    # //   BindingElements <= AssignmentTargets <= AssignmentExpression
    # //
    # // with a single exception that CoverInitializedName when used directly in an Expression, generates
    # // an early error. Therefore, we need the third state, firstCoverInitializedNameError, to track the
    # // first usage of CoverInitializedName and report it when we reached the end of the parentheses pair.
    # //
    # // isolateCoverGrammar function runs the given parser function with a new cover grammar context, and it does not
    # // effect the current flags. This means the production the parser parses is only used as an expression. Therefore
    # // the CoverInitializedName check is conducted.
    # //
    # // inheritCoverGrammar function runs the given parse function with a new cover grammar context, and it propagates
    # // the flags outside of the parser. This means the production the parser parses is used as a part of a potential
    # // pattern. The CoverInitializedName check is deferred.

    def isolateCoverGrammar(self, parser):
        oldIsBindingElement = self.isBindingElement
        oldIsAssignmentTarget = self.isAssignmentTarget
        oldFirstCoverInitializedNameError = self.firstCoverInitializedNameError
        self.isBindingElement = true
        self.isAssignmentTarget = true
        self.firstCoverInitializedNameError = null
        result = parser()
        if (self.firstCoverInitializedNameError != null):
            self.throwUnexpectedToken(self.firstCoverInitializedNameError)
        self.isBindingElement = oldIsBindingElement
        self.isAssignmentTarget = oldIsAssignmentTarget
        self.firstCoverInitializedNameError = oldFirstCoverInitializedNameError
        return result

    def inheritCoverGrammar(self, parser):
        oldIsBindingElement = self.isBindingElement
        oldIsAssignmentTarget = self.isAssignmentTarget
        oldFirstCoverInitializedNameError = self.firstCoverInitializedNameError
        self.isBindingElement = true
        self.isAssignmentTarget = true
        self.firstCoverInitializedNameError = null
        result = parser()
        self.isBindingElement = self.isBindingElement and oldIsBindingElement
        self.isAssignmentTarget = self.isAssignmentTarget and oldIsAssignmentTarget
        self.firstCoverInitializedNameError = oldFirstCoverInitializedNameError or self.firstCoverInitializedNameError
        return result

    def parseArrayPattern(self):
        node = Node()
        elements = []
        self.expect('[');
        while (not self.match(']')):
            if (self.match(',')):
                self.lex()
                elements.append(null)
            else:
                if (self.match('...')):
                    restNode = Node()
                    self.lex()
                    rest = self.parseVariableIdentifier()
                    elements.append(restNode.finishRestElement(rest))
                    break
                else:
                    elements.append(self.parsePatternWithDefault())
                if (not self.match(']')):
                    self.expect(',')
        self.expect(']')
        return node.finishArrayPattern(elements)

    def parsePropertyPattern(self):
        node = Node()
        computed = self.match('[')
        if (self.lookahead['type'] == Token.Identifier):
            key = self.parseVariableIdentifier()
            if (self.match('=')):
                self.lex();
                init = self.parseAssignmentExpression()
                return node.finishProperty(
                    'init', key, false, WrappingNode(key).finishAssignmentPattern(key, init), false, false)
            elif (not self.match(':')):
                return node.finishProperty('init', key, false, key, false, true)
        else:
            key = self.parseObjectPropertyKey()
        self.expect(':')
        init = self.parsePatternWithDefault()
        return node.finishProperty('init', key, computed, init, false, false)

    def parseObjectPattern(self):
        node = Node()
        properties = []
        self.expect('{')
        while (not self.match('}')):
            properties.append(self.parsePropertyPattern())
            if (not self.match('}')):
                self.expect(',')
        self.lex()
        return node.finishObjectPattern(properties)

    def parsePattern(self):
        if (self.lookahead['type'] == Token.Identifier):
            return self.parseVariableIdentifier()
        elif (self.match('[')):
            return self.parseArrayPattern()
        elif (self.match('{')):
            return self.parseObjectPattern()
        self.throwUnexpectedToken(self.lookahead)

    def parsePatternWithDefault(self):
        startToken = self.lookahead

        pattern = self.parsePattern()
        if (self.match('=')):
            self.lex()
            right = self.isolateCoverGrammar(self.parseAssignmentExpression)
            pattern = WrappingNode(startToken).finishAssignmentPattern(pattern, right)
        return pattern

    # 11.1.4 Array Initialiser

    def parseArrayInitialiser(self):
        elements = []
        node = Node()

        self.expect('[')

        while (not self.match(']')):
            if (self.match(',')):
                self.lex()
                elements.append(null)
            elif (self.match('...')):
                restSpread = Node()
                self.lex()
                restSpread.finishSpreadElement(self.inheritCoverGrammar(self.parseAssignmentExpression))
                if (not self.match(']')):
                    self.isAssignmentTarget = self.isBindingElement = false
                    self.expect(',')
                elements.append(restSpread)
            else:
                elements.append(self.inheritCoverGrammar(self.parseAssignmentExpression))
                if (not self.match(']')):
                    self.expect(',')
        self.lex();

        return node.finishArrayExpression(elements)

    # 11.1.5 Object Initialiser

    def parsePropertyFunction(self, node, paramInfo):

        self.isAssignmentTarget = self.isBindingElement = false;

        previousStrict = self.strict;
        body = self.isolateCoverGrammar(self.parseFunctionSourceElements);

        if (self.strict and paramInfo['firstRestricted']):
            self.tolerateUnexpectedToken(paramInfo['firstRestricted'], paramInfo.get('message'))
        if (self.strict and paramInfo.get('stricted')):
            self.tolerateUnexpectedToken(paramInfo.get('stricted'), paramInfo.get('message'));

        self.strict = previousStrict;
        return node.finishFunctionExpression(null, paramInfo.get('params'), paramInfo.get('defaults'), body)

    def parsePropertyMethodFunction(self):
        node = Node();

        params = self.parseParams(null);
        method = self.parsePropertyFunction(node, params);
        return method;

    def parseObjectPropertyKey(self):
        node = Node()

        token = self.lex();

        # // Note: This function is called only from parseObjectProperty(), where
        # // EOF and Punctuator tokens are already filtered out.

        typ = token['type']

        if typ in [Token.StringLiteral, Token.NumericLiteral]:
            if self.strict and token.get('octal'):
                self.tolerateUnexpectedToken(token, Messages.StrictOctalLiteral);
            return node.finishLiteral(token);
        elif typ in (Token.Identifier, Token.BooleanLiteral, Token.NullLiteral, Token.Keyword):
            return node.finishIdentifier(token['value']);
        elif typ == Token.Punctuator:
            if (token['value'] == '['):
                expr = self.isolateCoverGrammar(self.parseAssignmentExpression)
                self.expect(']')
                return expr
        self.throwUnexpectedToken(token)

    def lookaheadPropertyName(self):
        typ = self.lookahead['type']
        if typ in (Token.Identifier, Token.StringLiteral, Token.BooleanLiteral, Token.NullLiteral, Token.NumericLiteral,
                   Token.Keyword):
            return true
        if typ == Token.Punctuator:
            return self.lookahead['value'] == '['
        return false

    # // This function is to try to parse a MethodDefinition as defined in 14.3. But in the case of object literals,
    # // it might be called at a position where there is in fact a short hand identifier pattern or a data property.
    # // This can only be determined after we consumed up to the left parentheses.
    # //
    # // In order to avoid back tracking, it returns `null` if the position is not a MethodDefinition and the caller
    # // is responsible to visit other options.
    def tryParseMethodDefinition(self, token, key, computed, node):
        if (token['type'] == Token.Identifier):
            # check for `get` and `set`;

            if (token['value'] == 'get' and self.lookaheadPropertyName()):
                computed = self.match('[');
                key = self.parseObjectPropertyKey()
                methodNode = Node()
                self.expect('(')
                self.expect(')')
                value = self.parsePropertyFunction(methodNode, {
                    'params': [],
                    'defaults': [],
                    'stricted': null,
                    'firstRestricted': null,
                    'message': null
                })
                return node.finishProperty('get', key, computed, value, false, false)
            elif (token['value'] == 'set' and self.lookaheadPropertyName()):
                computed = self.match('[')
                key = self.parseObjectPropertyKey()
                methodNode = Node()
                self.expect('(')

                options = {
                    'params': [],
                    'defaultCount': 0,
                    'defaults': [],
                    'firstRestricted': null,
                    'paramSet': {}
                }
                if (self.match(')')):
                    self.tolerateUnexpectedToken(self.lookahead);
                else:
                    self.parseParam(options);
                    if (options['defaultCount'] == 0):
                        options['defaults'] = []
                self.expect(')')

                value = self.parsePropertyFunction(methodNode, options);
                return node.finishProperty('set', key, computed, value, false, false);
        if (self.match('(')):
            value = self.parsePropertyMethodFunction();
            return node.finishProperty('init', key, computed, value, true, false)
        return null;

    def checkProto(self, key, computed, hasProto):
        if (computed == false and (key['type'] == Syntax.Identifier and key['name'] == '__proto__' or
                                               key['type'] == Syntax.Literal and key['value'] == '__proto__')):
            if (hasProto['value']):
                self.tolerateError(Messages.DuplicateProtoProperty);
            else:
                hasProto['value'] = true;

    def parseObjectProperty(self, hasProto):
        token = self.lookahead
        node = Node()
        node.comments = self.lookahead.get('comments', [])

        computed = self.match('[');
        key = self.parseObjectPropertyKey();
        maybeMethod = self.tryParseMethodDefinition(token, key, computed, node)

        if (maybeMethod):
            self.checkProto(maybeMethod['key'], maybeMethod['computed'], hasProto);
            return maybeMethod;

        # // init property or short hand property.
        self.checkProto(key, computed, hasProto);

        if (self.match(':')):
            self.lex();
            value = self.inheritCoverGrammar(self.parseAssignmentExpression)
            return node.finishProperty('init', key, computed, value, false, false)

        if (token['type'] == Token.Identifier):
            if (self.match('=')):
                self.firstCoverInitializedNameError = self.lookahead;
                self.lex();
                value = self.isolateCoverGrammar(self.parseAssignmentExpression);
                return node.finishProperty('init', key, computed,
                                           WrappingNode(token).finishAssignmentPattern(key, value), false, true)
            return node.finishProperty('init', key, computed, key, false, true)
        self.throwUnexpectedToken(self.lookahead)

    def parseObjectInitialiser(self):
        properties = []
        hasProto = {'value': false}
        node = Node();
        node.comments = self.lookahead.get('comments', [])
        self.expect('{');
        while (not self.match('}')):
            properties.append(self.parseObjectProperty(hasProto));

            if (not self.match('}')):
                self.expectCommaSeparator()
        self.expect('}');
        return node.finishObjectExpression(properties)

    def reinterpretExpressionAsPattern(self, expr):
        typ = (expr['type'])
        if typ in (Syntax.Identifier, Syntax.MemberExpression, Syntax.RestElement, Syntax.AssignmentPattern):
            pass
        elif typ == Syntax.SpreadElement:
            expr['type'] = Syntax.RestElement
            self.reinterpretExpressionAsPattern(expr.argument)
        elif typ == Syntax.ArrayExpression:
            expr['type'] = Syntax.ArrayPattern
            for i in range(len(expr['elements'])):
                if (expr['elements'][i] != null):
                    self.reinterpretExpressionAsPattern(expr['elements'][i])
        elif typ == Syntax.ObjectExpression:
            expr['type'] = Syntax.ObjectPattern
            for i in range(len(expr['properties'])):
                self.reinterpretExpressionAsPattern(expr['properties'][i]['value']);
        elif Syntax.AssignmentExpression:
            expr['type'] = Syntax.AssignmentPattern;
            self.reinterpretExpressionAsPattern(expr['left'])
        else:
            # // Allow other node type for tolerant parsing.
            return

    def parseTemplateElement(self, option):

        if (self.lookahead['type'] != Token.Template or (option['head'] and not self.lookahead['head'])):
            self.throwUnexpectedToken()

        node = Node();
        token = self.lex();

        return node.finishTemplateElement({'raw': token['value']['raw'], 'cooked': token['value']['cooked']},
                                          token['tail'])

    def parseTemplateLiteral(self):
        node = Node()

        quasi = self.parseTemplateElement({'head': true})
        quasis = [quasi]
        expressions = []

        while (not quasi['tail']):
            expressions.append(self.parseExpression());
            quasi = self.parseTemplateElement({'head': false});
            quasis.append(quasi)
        return node.finishTemplateLiteral(quasis, expressions)

    # 11.1.6 The Grouping Operator

    def parseGroupExpression(self):
        self.expect('(');

        if (self.match(')')):
            self.lex();
            if (not self.match('=>')):
                self.expect('=>')
            return {
                'type': PlaceHolders.ArrowParameterPlaceHolder,
                'params': []}

        startToken = self.lookahead
        if (self.match('...')):
            expr = self.parseRestElement();
            self.expect(')');
            if (not self.match('=>')):
                self.expect('=>')
            return {
                'type': PlaceHolders.ArrowParameterPlaceHolder,
                'params': [expr]}

        self.isBindingElement = true;
        expr = self.inheritCoverGrammar(self.parseAssignmentExpression);

        if (self.match(',')):
            self.isAssignmentTarget = false;
            expressions = [expr]

            while (self.startIndex < self.length):
                if (not self.match(',')):
                    break
                self.lex();

                if (self.match('...')):
                    if (not self.isBindingElement):
                        self.throwUnexpectedToken(self.lookahead)
                    expressions.append(self.parseRestElement())
                    self.expect(')');
                    if (not self.match('=>')):
                        self.expect('=>');
                    self.isBindingElement = false
                    for i in range(len(expressions)):
                        self.reinterpretExpressionAsPattern(expressions[i])
                    return {
                        'type': PlaceHolders.ArrowParameterPlaceHolder,
                        'params': expressions}
                expressions.append(self.inheritCoverGrammar(self.parseAssignmentExpression))
            expr = WrappingNode(startToken).finishSequenceExpression(expressions);
        self.expect(')')

        if (self.match('=>')):
            if (not self.isBindingElement):
                self.throwUnexpectedToken(self.lookahead);
            if (expr['type'] == Syntax.SequenceExpression):
                for i in range(len(expr.expressions)):
                    self.reinterpretExpressionAsPattern(expr['expressions'][i])
            else:
                self.reinterpretExpressionAsPattern(expr);
            expr = {
                'type': PlaceHolders.ArrowParameterPlaceHolder,
                'params': expr['expressions'] if expr['type'] == Syntax.SequenceExpression  else [expr]}
        self.isBindingElement = false
        return expr

    # 11.1 Primary Expressions

    def parsePrimaryExpression(self):
        if (self.match('(')):
            self.isBindingElement = false;
            return self.inheritCoverGrammar(self.parseGroupExpression)
        if (self.match('[')):
            return self.inheritCoverGrammar(self.parseArrayInitialiser)

        if (self.match('{')):
            return self.inheritCoverGrammar(self.parseObjectInitialiser)

        typ = self.lookahead['type']
        node = Node();
        node.comments = self.lookahead.get('comments', [])

        if (typ == Token.Identifier):
            expr = node.finishIdentifier(self.lex()['value']);
        elif (typ == Token.StringLiteral or typ == Token.NumericLiteral):
            self.isAssignmentTarget = self.isBindingElement = false
            if (self.strict and self.lookahead.get('octal')):
                self.tolerateUnexpectedToken(self.lookahead, Messages.StrictOctalLiteral)
            expr = node.finishLiteral(self.lex())
        elif (typ == Token.Keyword):
            self.isAssignmentTarget = self.isBindingElement = false
            if (self.matchKeyword('function')):
                return self.parseFunctionExpression()
            if (self.matchKeyword('this')):
                self.lex()
                return node.finishThisExpression()
            if (self.matchKeyword('class')):
                return self.parseClassExpression()
            self.throwUnexpectedToken(self.lex())
        elif (typ == Token.BooleanLiteral):
            isAssignmentTarget = self.isBindingElement = false
            token = self.lex();
            token['value'] = (token['value'] == 'true')
            expr = node.finishLiteral(token)
        elif (typ == Token.NullLiteral):
            self.isAssignmentTarget = self.isBindingElement = false
            token = self.lex()
            token['value'] = null;
            expr = node.finishLiteral(token)
        elif (self.match('/') or self.match('/=')):
            self.isAssignmentTarget = self.isBindingElement = false;
            self.index = self.startIndex;
            token = self.scanRegExp([]);  # hehe, here you are!
            self.lex();
            expr = node.finishLiteral(token);
        elif (typ == Token.Template):
            expr = self.parseTemplateLiteral()
        else:
            self.throwUnexpectedToken(self.lex());
        return expr;

    # 11.2 Left-Hand-Side Expressions

    def parseArguments(self):
        args = [];

        self.expect('(');
        if (not self.match(')')):
            while (self.startIndex < self.length):
                args.append(self.isolateCoverGrammar(self.parseAssignmentExpression))
                if (self.match(')')):
                    break
                self.expectCommaSeparator()
        self.expect(')')
        return args;

    def parseNonComputedProperty(self):
        node = Node()

        token = self.lex();

        if (not self.isIdentifierName(token)):
            self.throwUnexpectedToken(token)
        return node.finishIdentifier(token['value'])

    def parseNonComputedMember(self):
        self.expect('.')
        return self.parseNonComputedProperty();

    def parseComputedMember(self):
        self.expect('[')

        expr = self.isolateCoverGrammar(self.parseExpression)
        self.expect(']')

        return expr

    def parseNewExpression(self):
        node = Node()
        self.expectKeyword('new')
        callee = self.isolateCoverGrammar(self.parseLeftHandSideExpression)
        args = self.parseArguments() if self.match('(') else []

        self.isAssignmentTarget = self.isBindingElement = false

        return node.finishNewExpression(callee, args)

    def parseLeftHandSideExpressionAllowCall(self):
        previousAllowIn = self.state['allowIn']

        startToken = self.lookahead;
        self.state['allowIn'] = true;

        if (self.matchKeyword('super') and self.state['inFunctionBody']):
            expr = Node();
            self.lex();
            expr = expr.finishSuper()
            if (not self.match('(') and not self.match('.') and not self.match('[')):
                self.throwUnexpectedToken(self.lookahead);
        else:
            expr = self.inheritCoverGrammar(
                self.parseNewExpression if self.matchKeyword('new') else self.parsePrimaryExpression)
        while True:
            if (self.match('.')):
                self.isBindingElement = false;
                self.isAssignmentTarget = true;
                property = self.parseNonComputedMember();
                expr = WrappingNode(startToken).finishMemberExpression('.', expr, property)
            elif (self.match('(')):
                self.isBindingElement = false;
                self.isAssignmentTarget = false;
                args = self.parseArguments();
                expr = WrappingNode(startToken).finishCallExpression(expr, args)
            elif (self.match('[')):
                self.isBindingElement = false;
                self.isAssignmentTarget = true;
                property = self.parseComputedMember();
                expr = WrappingNode(startToken).finishMemberExpression('[', expr, property)
            elif (self.lookahead['type'] == Token.Template and self.lookahead['head']):
                quasi = self.parseTemplateLiteral()
                expr = WrappingNode(startToken).finishTaggedTemplateExpression(expr, quasi)
            else:
                break
        self.state['allowIn'] = previousAllowIn

        return expr

    def parseLeftHandSideExpression(self):
        assert self.state['allowIn'], 'callee of new expression always allow in keyword.'

        startToken = self.lookahead

        if (self.matchKeyword('super') and self.state['inFunctionBody']):
            expr = Node();
            self.lex();
            expr = expr.finishSuper();
            if (not self.match('[') and not self.match('.')):
                self.throwUnexpectedToken(self.lookahead)
        else:
            expr = self.inheritCoverGrammar(
                self.parseNewExpression if self.matchKeyword('new') else self.parsePrimaryExpression);

        while True:
            if (self.match('[')):
                self.isBindingElement = false;
                self.isAssignmentTarget = true;
                property = self.parseComputedMember();
                expr = WrappingNode(startToken).finishMemberExpression('[', expr, property)
            elif (self.match('.')):
                self.isBindingElement = false;
                self.isAssignmentTarget = true;
                property = self.parseNonComputedMember();
                expr = WrappingNode(startToken).finishMemberExpression('.', expr, property);
            elif (self.lookahead['type'] == Token.Template and self.lookahead['head']):
                quasi = self.parseTemplateLiteral();
                expr = WrappingNode(startToken).finishTaggedTemplateExpression(expr, quasi)
            else:
                break
        return expr

    # 11.3 Postfix Expressions

    def parsePostfixExpression(self):
        startToken = self.lookahead

        expr = self.inheritCoverGrammar(self.parseLeftHandSideExpressionAllowCall)

        if (not self.hasLineTerminator and self.lookahead['type'] == Token.Punctuator):
            if (self.match('++') or self.match('--')):
                # 11.3.1, 11.3.2
                if (self.strict and expr.type == Syntax.Identifier and isRestrictedWord(expr.name)):
                    self.tolerateError(Messages.StrictLHSPostfix)
                if (not self.isAssignmentTarget):
                    self.tolerateError(Messages.InvalidLHSInAssignment);
                self.isAssignmentTarget = self.isBindingElement = false;

                token = self.lex();
                expr = WrappingNode(startToken).finishPostfixExpression(token['value'], expr);
        return expr;

    # 11.4 Unary Operators

    def parseUnaryExpression(self):

        if (self.lookahead['type'] != Token.Punctuator and self.lookahead['type'] != Token.Keyword):
            expr = self.parsePostfixExpression();
        elif (self.match('++') or self.match('--')):
            startToken = self.lookahead;
            token = self.lex();
            expr = self.inheritCoverGrammar(self.parseUnaryExpression);
            # 11.4.4, 11.4.5
            if (self.strict and expr.type == Syntax.Identifier and isRestrictedWord(expr.name)):
                self.tolerateError(Messages.StrictLHSPrefix)
            if (not self.isAssignmentTarget):
                self.tolerateError(Messages.InvalidLHSInAssignment)
            expr = WrappingNode(startToken).finishUnaryExpression(token['value'], expr)
            self.isAssignmentTarget = self.isBindingElement = false
        elif (self.match('+') or self.match('-') or self.match('~') or self.match('!')):
            startToken = self.lookahead;
            token = self.lex();
            expr = self.inheritCoverGrammar(self.parseUnaryExpression);
            expr = WrappingNode(startToken).finishUnaryExpression(token['value'], expr)
            self.isAssignmentTarget = self.isBindingElement = false;
        elif (self.matchKeyword('delete') or self.matchKeyword('void') or self.matchKeyword('typeof')):
            startToken = self.lookahead;
            token = self.lex();
            expr = self.inheritCoverGrammar(self.parseUnaryExpression);
            expr = WrappingNode(startToken).finishUnaryExpression(token['value'], expr);
            if (self.strict and expr.operator == 'delete' and expr.argument.type == Syntax.Identifier):
                self.tolerateError(Messages.StrictDelete)
            self.isAssignmentTarget = self.isBindingElement = false;
        else:
            expr = self.parsePostfixExpression()
        return expr

    def binaryPrecedence(self, token, allowIn):
        prec = 0;
        typ = token['type']
        if (typ != Token.Punctuator and typ != Token.Keyword):
            return 0;
        val = token['value']
        if val == 'in' and not allowIn:
            return 0
        return PRECEDENCE.get(val, 0)

    # 11.5 Multiplicative Operators
    # 11.6 Additive Operators
    # 11.7 Bitwise Shift Operators
    # 11.8 Relational Operators
    # 11.9 Equality Operators
    # 11.10 Binary Bitwise Operators
    # 11.11 Binary Logical Operators

    def parseBinaryExpression(self):

        marker = self.lookahead;
        left = self.inheritCoverGrammar(self.parseUnaryExpression);

        token = self.lookahead;
        prec = self.binaryPrecedence(token, self.state['allowIn']);
        if (prec == 0):
            return left
        self.isAssignmentTarget = self.isBindingElement = false;
        token['prec'] = prec
        self.lex()

        markers = [marker, self.lookahead];
        right = self.isolateCoverGrammar(self.parseUnaryExpression);

        stack = [left, token, right];

        while True:
            prec = self.binaryPrecedence(self.lookahead, self.state['allowIn'])
            if not prec > 0:
                break
            # Reduce: make a binary expression from the three topmost entries.
            while ((len(stack) > 2) and (prec <= stack[len(stack) - 2]['prec'])):
                right = stack.pop();
                operator = stack.pop()['value']
                left = stack.pop()
                markers.pop()
                expr = WrappingNode(markers[len(markers) - 1]).finishBinaryExpression(operator, left, right)
                stack.append(expr)

            # Shift
            token = self.lex();
            token['prec'] = prec;
            stack.append(token);
            markers.append(self.lookahead);
            expr = self.isolateCoverGrammar(self.parseUnaryExpression);
            stack.append(expr);

        # Final reduce to clean-up the stack.
        i = len(stack) - 1;
        expr = stack[i]
        markers.pop()
        while (i > 1):
            expr = WrappingNode(markers.pop()).finishBinaryExpression(stack[i - 1]['value'], stack[i - 2], expr);
            i -= 2
        return expr

    # 11.12 Conditional Operator

    def parseConditionalExpression(self):

        startToken = self.lookahead

        expr = self.inheritCoverGrammar(self.parseBinaryExpression);
        if (self.match('?')):
            self.lex()
            previousAllowIn = self.state['allowIn']
            self.state['allowIn'] = true;
            consequent = self.isolateCoverGrammar(self.parseAssignmentExpression);
            self.state['allowIn'] = previousAllowIn;
            self.expect(':');
            alternate = self.isolateCoverGrammar(self.parseAssignmentExpression)

            expr = WrappingNode(startToken).finishConditionalExpression(expr, consequent, alternate);
            self.isAssignmentTarget = self.isBindingElement = false;
        return expr

    # [ES6] 14.2 Arrow Function

    def parseConciseBody(self):
        if (self.match('{')):
            return self.parseFunctionSourceElements()
        return self.isolateCoverGrammar(self.parseAssignmentExpression)

    def checkPatternParam(self, options, param):
        typ = param.type
        if typ == Syntax.Identifier:
            self.validateParam(options, param, param.name);
        elif typ == Syntax.RestElement:
            self.checkPatternParam(options, param.argument)
        elif typ == Syntax.AssignmentPattern:
            self.checkPatternParam(options, param.left)
        elif typ == Syntax.ArrayPattern:
            for i in range(len(param.elements)):
                if (param.elements[i] != null):
                    self.checkPatternParam(options, param.elements[i]);
        else:
            assert typ == Syntax.ObjectPattern, 'Invalid type'
            for i in range(len(param.properties)):
                self.checkPatternParam(options, param.properties[i]['value']);

    def reinterpretAsCoverFormalsList(self, expr):
        defaults = [];
        defaultCount = 0;
        params = [expr];
        typ = expr.type
        if typ == Syntax.Identifier:
            pass
        elif typ == PlaceHolders.ArrowParameterPlaceHolder:
            params = expr.params
        else:
            return null
        options = {
            'paramSet': {}}
        le = len(params)
        for i in range(le):
            param = params[i]
            if param.type == Syntax.AssignmentPattern:
                params[i] = param.left;
                defaults.append(param.right);
                defaultCount += 1
                self.checkPatternParam(options, param.left);
            else:
                self.checkPatternParam(options, param);
                params[i] = param;
                defaults.append(null);
        if (options.get('message') == Messages.StrictParamDupe):
            token = options.get('stricted') if self.strict else options['firstRestricted']
            self.throwUnexpectedToken(token, options.get('message'));
        if (defaultCount == 0):
            defaults = []
        return {
            'params': params,
            'defaults': defaults,
            'stricted': options['stricted'],
            'firstRestricted': options['firstRestricted'],
            'message': options.get('message')}

    def parseArrowFunctionExpression(self, options, node):
        if (self.hasLineTerminator):
            self.tolerateUnexpectedToken(self.lookahead)
        self.expect('=>')
        previousStrict = self.strict;

        body = self.parseConciseBody();

        if (self.strict and options['firstRestricted']):
            self.throwUnexpectedToken(options['firstRestricted'], options.get('message'));
        if (self.strict and options['stricted']):
            self.tolerateUnexpectedToken(options['stricted'], options['message']);

        self.strict = previousStrict

        return node.finishArrowFunctionExpression(options['params'], options['defaults'], body,
                                                  body.type != Syntax.BlockStatement)

    # 11.13 Assignment Operators

    def parseAssignmentExpression(self):
        startToken = self.lookahead;
        token = self.lookahead;

        expr = self.parseConditionalExpression();

        if (expr.type == PlaceHolders.ArrowParameterPlaceHolder or self.match('=>')):
            self.isAssignmentTarget = self.isBindingElement = false;
            lis = self.reinterpretAsCoverFormalsList(expr)

            if (lis):
                self.firstCoverInitializedNameError = null;
                return self.parseArrowFunctionExpression(lis, WrappingNode(startToken))
            return expr

        if (self.matchAssign()):
            if (not self.isAssignmentTarget):
                self.tolerateError(Messages.InvalidLHSInAssignment)
            # 11.13.1

            if (self.strict and expr.type == Syntax.Identifier and isRestrictedWord(expr.name)):
                self.tolerateUnexpectedToken(token, Messages.StrictLHSAssignment);
            if (not self.match('=')):
                self.isAssignmentTarget = self.isBindingElement = false;
            else:
                self.reinterpretExpressionAsPattern(expr)
            token = self.lex();
            right = self.isolateCoverGrammar(self.parseAssignmentExpression)
            expr = WrappingNode(startToken).finishAssignmentExpression(token['value'], expr, right);
            self.firstCoverInitializedNameError = null
        return expr

    # 11.14 Comma Operator

    def parseExpression(self):
        startToken = self.lookahead
        expr = self.isolateCoverGrammar(self.parseAssignmentExpression)

        if (self.match(',')):
            expressions = [expr];

            while (self.startIndex < self.length):
                if (not self.match(',')):
                    break
                self.lex();
                expressions.append(self.isolateCoverGrammar(self.parseAssignmentExpression))
            expr = WrappingNode(startToken).finishSequenceExpression(expressions);
        return expr

    # 12.1 Block

    def parseStatementListItem(self):
        if (self.lookahead['type'] == Token.Keyword):
            val = (self.lookahead['value'])
            if val == 'export':
                if (self.sourceType != 'module'):
                    self.tolerateUnexpectedToken(self.lookahead, Messages.IllegalExportDeclaration)
                return self.parseExportDeclaration();
            elif val == 'import':
                if (self.sourceType != 'module'):
                    self.tolerateUnexpectedToken(self.lookahead, Messages.IllegalImportDeclaration);
                return self.parseImportDeclaration();
            elif val == 'const' or val == 'let':
                return self.parseLexicalDeclaration({'inFor': false});
            elif val == 'function':
                return self.parseFunctionDeclaration(Node());
            elif val == 'class':
                return self.parseClassDeclaration();
            elif ENABLE_PYIMPORT and val == 'pyimport':  # <<<<< MODIFIED HERE
                return self.parsePyimportStatement()
        return self.parseStatement();

    def parsePyimportStatement(self):
        print(ENABLE_PYIMPORT)
        assert ENABLE_PYIMPORT
        n = Node()
        self.lex()
        n.finishPyimport(self.parseVariableIdentifier())
        self.consumeSemicolon()
        return n

    def parseStatementList(self):
        list = [];
        while (self.startIndex < self.length):
            if (self.match('}')):
                break
            list.append(self.parseStatementListItem())
        return list

    def parseBlock(self):
        node = Node();

        self.expect('{');

        block = self.parseStatementList()

        self.expect('}');

        return node.finishBlockStatement(block);

    # 12.2 Variable Statement

    def parseVariableIdentifier(self):
        node = Node()

        token = self.lex()

        if (token['type'] != Token.Identifier):
            if (self.strict and token['type'] == Token.Keyword and isStrictModeReservedWord(token['value'])):
                self.tolerateUnexpectedToken(token, Messages.StrictReservedWord);
            else:
                self.throwUnexpectedToken(token)
        return node.finishIdentifier(token['value'])

    def parseVariableDeclaration(self):
        init = null
        node = Node();
        d = self.parsePattern();

        # 12.2.1
        if (self.strict and isRestrictedWord(d.name)):
            self.tolerateError(Messages.StrictVarName);

        if (self.match('=')):
            self.lex();
            init = self.isolateCoverGrammar(self.parseAssignmentExpression);
        elif (d.type != Syntax.Identifier):
            self.expect('=')
        return node.finishVariableDeclarator(d, init)

    def parseVariableDeclarationList(self):
        lis = []

        while True:
            lis.append(self.parseVariableDeclaration())
            if (not self.match(',')):
                break
            self.lex();
            if not (self.startIndex < self.length):
                break

        return lis;

    def parseVariableStatement(self, node):
        self.expectKeyword('var')
        declarations = self.parseVariableDeclarationList()

        self.consumeSemicolon()

        return node.finishVariableDeclaration(declarations)

    def parseLexicalBinding(self, kind, options):
        init = null
        node = Node()

        d = self.parsePattern();

        # 12.2.1
        if (self.strict and d.type == Syntax.Identifier and isRestrictedWord(d.name)):
            self.tolerateError(Messages.StrictVarName);

        if (kind == 'const'):
            if (not self.matchKeyword('in')):
                self.expect('=')
                init = self.isolateCoverGrammar(self.parseAssignmentExpression)
        elif ((not options['inFor'] and d.type != Syntax.Identifier) or self.match('=')):
            self.expect('=');
            init = self.isolateCoverGrammar(self.parseAssignmentExpression);
        return node.finishVariableDeclarator(d, init)

    def parseBindingList(self, kind, options):
        list = [];

        while True:
            list.append(self.parseLexicalBinding(kind, options));
            if (not self.match(',')):
                break
            self.lex();
            if not (self.startIndex < self.length):
                break
        return list;

    def parseLexicalDeclaration(self, options):
        node = Node();

        kind = self.lex()['value']
        assert kind == 'let' or kind == 'const', 'Lexical declaration must be either let or const'
        declarations = self.parseBindingList(kind, options);
        self.consumeSemicolon();
        return node.finishLexicalDeclaration(declarations, kind);

    def parseRestElement(self):
        node = Node();

        self.lex();

        if (self.match('{')):
            self.throwError(Messages.ObjectPatternAsRestParameter)
        param = self.parseVariableIdentifier();
        if (self.match('=')):
            self.throwError(Messages.DefaultRestParameter);

        if (not self.match(')')):
            self.throwError(Messages.ParameterAfterRestParameter);
        return node.finishRestElement(param);

    # 12.3 Empty Statement

    def parseEmptyStatement(self, node):
        self.expect(';');
        return node.finishEmptyStatement()

    # 12.4 Expression Statement

    def parseExpressionStatement(self, node):
        expr = self.parseExpression();
        self.consumeSemicolon();
        return node.finishExpressionStatement(expr);

    # 12.5 If statement

    def parseIfStatement(self, node):
        self.expectKeyword('if');

        self.expect('(');

        test = self.parseExpression();

        self.expect(')');

        consequent = self.parseStatement();

        if (self.matchKeyword('else')):
            self.lex();
            alternate = self.parseStatement();
        else:
            alternate = null;
        return node.finishIfStatement(test, consequent, alternate)

    # 12.6 Iteration Statements

    def parseDoWhileStatement(self, node):

        self.expectKeyword('do')

        oldInIteration = self.state['inIteration']
        self.state['inIteration'] = true

        body = self.parseStatement();

        self.state['inIteration'] = oldInIteration;

        self.expectKeyword('while');

        self.expect('(');

        test = self.parseExpression();

        self.expect(')')

        if (self.match(';')):
            self.lex()
        return node.finishDoWhileStatement(body, test)

    def parseWhileStatement(self, node):

        self.expectKeyword('while')

        self.expect('(')

        test = self.parseExpression()

        self.expect(')')

        oldInIteration = self.state['inIteration']
        self.state['inIteration'] = true

        body = self.parseStatement()

        self.state['inIteration'] = oldInIteration

        return node.finishWhileStatement(test, body)

    def parseForStatement(self, node):
        previousAllowIn = self.state['allowIn']

        init = test = update = null

        self.expectKeyword('for')

        self.expect('(')

        if (self.match(';')):
            self.lex()
        else:
            if (self.matchKeyword('var')):
                init = Node()
                self.lex()

                self.state['allowIn'] = false;
                init = init.finishVariableDeclaration(self.parseVariableDeclarationList())
                self.state['allowIn'] = previousAllowIn

                if (len(init.declarations) == 1 and self.matchKeyword('in')):
                    self.lex()
                    left = init
                    right = self.parseExpression()
                    init = null
                else:
                    self.expect(';')
            elif (self.matchKeyword('const') or self.matchKeyword('let')):
                init = Node()
                kind = self.lex()['value']

                self.state['allowIn'] = false
                declarations = self.parseBindingList(kind, {'inFor': true})
                self.state['allowIn'] = previousAllowIn

                if (len(declarations) == 1 and declarations[0].init == null and self.matchKeyword('in')):
                    init = init.finishLexicalDeclaration(declarations, kind);
                    self.lex();
                    left = init;
                    right = self.parseExpression();
                    init = null;
                else:
                    self.consumeSemicolon();
                    init = init.finishLexicalDeclaration(declarations, kind);
            else:
                initStartToken = self.lookahead
                self.state['allowIn'] = false
                init = self.inheritCoverGrammar(self.parseAssignmentExpression);
                self.state['allowIn'] = previousAllowIn;

                if (self.matchKeyword('in')):
                    if (not self.isAssignmentTarget):
                        self.tolerateError(Messages.InvalidLHSInForIn)
                    self.lex();
                    self.reinterpretExpressionAsPattern(init);
                    left = init;
                    right = self.parseExpression();
                    init = null;
                else:
                    if (self.match(',')):
                        initSeq = [init];
                        while (self.match(',')):
                            self.lex();
                            initSeq.append(self.isolateCoverGrammar(self.parseAssignmentExpression))
                        init = WrappingNode(initStartToken).finishSequenceExpression(initSeq)
                    self.expect(';');

        if ('left' not in locals()):
            if (not self.match(';')):
                test = self.parseExpression();

            self.expect(';');

            if (not self.match(')')):
                update = self.parseExpression();

        self.expect(')');

        oldInIteration = self.state['inIteration']
        self.state['inIteration'] = true;

        body = self.isolateCoverGrammar(self.parseStatement)

        self.state['inIteration'] = oldInIteration;

        return node.finishForStatement(init, test, update, body) if (
        'left' not in locals()) else node.finishForInStatement(left, right, body);

    # 12.7 The continue statement

    def parseContinueStatement(self, node):
        label = null

        self.expectKeyword('continue');

        # Optimize the most common form: 'continue;'.
        if ord(self.source[self.startIndex]) == 0x3B:
            self.lex();
            if (not self.state['inIteration']):
                self.throwError(Messages.IllegalContinue)
            return node.finishContinueStatement(null)
        if (self.hasLineTerminator):
            if (not self.state['inIteration']):
                self.throwError(Messages.IllegalContinue);
            return node.finishContinueStatement(null);

        if (self.lookahead['type'] == Token.Identifier):
            label = self.parseVariableIdentifier();

            key = '$' + label.name;
            if not key in self.state['labelSet']:  # todo make sure its correct!
                self.throwError(Messages.UnknownLabel, label.name);
        self.consumeSemicolon()

        if (label == null and not self.state['inIteration']):
            self.throwError(Messages.IllegalContinue)
        return node.finishContinueStatement(label)

    # 12.8 The break statement

    def parseBreakStatement(self, node):
        label = null

        self.expectKeyword('break');

        # Catch the very common case first: immediately a semicolon (U+003B).
        if (ord(self.source[self.lastIndex]) == 0x3B):
            self.lex();

            if (not (self.state['inIteration'] or self.state['inSwitch'])):
                self.throwError(Messages.IllegalBreak)
            return node.finishBreakStatement(null)
        if (self.hasLineTerminator):
            if (not (self.state['inIteration'] or self.state['inSwitch'])):
                self.throwError(Messages.IllegalBreak);
            return node.finishBreakStatement(null);
        if (self.lookahead['type'] == Token.Identifier):
            label = self.parseVariableIdentifier();

            key = '$' + label.name;
            if not (key in self.state['labelSet']):
                self.throwError(Messages.UnknownLabel, label.name);
        self.consumeSemicolon();

        if (label == null and not (self.state['inIteration'] or self.state['inSwitch'])):
            self.throwError(Messages.IllegalBreak)
        return node.finishBreakStatement(label);

    # 12.9 The return statement

    def parseReturnStatement(self, node):
        argument = null;

        self.expectKeyword('return');

        if (not self.state['inFunctionBody']):
            self.tolerateError(Messages.IllegalReturn);

        # 'return' followed by a space and an identifier is very common.
        if (ord(self.source[self.lastIndex]) == 0x20):
            if (isIdentifierStart(self.source[self.lastIndex + 1])):
                argument = self.parseExpression();
                self.consumeSemicolon();
                return node.finishReturnStatement(argument)
        if (self.hasLineTerminator):
            # HACK
            return node.finishReturnStatement(null)

        if (not self.match(';')):
            if (not self.match('}') and self.lookahead['type'] != Token.EOF):
                argument = self.parseExpression();
        self.consumeSemicolon();

        return node.finishReturnStatement(argument);

    # 12.10 The with statement

    def parseWithStatement(self, node):
        if (self.strict):
            self.tolerateError(Messages.StrictModeWith)

        self.expectKeyword('with');

        self.expect('(');

        obj = self.parseExpression();

        self.expect(')');

        body = self.parseStatement();

        return node.finishWithStatement(obj, body);

    # 12.10 The swith statement

    def parseSwitchCase(self):
        consequent = []
        node = Node();

        if (self.matchKeyword('default')):
            self.lex();
            test = null;
        else:
            self.expectKeyword('case');
            test = self.parseExpression();

        self.expect(':');

        while (self.startIndex < self.length):
            if (self.match('}') or self.matchKeyword('default') or self.matchKeyword('case')):
                break
            statement = self.parseStatementListItem()
            consequent.append(statement)
        return node.finishSwitchCase(test, consequent)

    def parseSwitchStatement(self, node):

        self.expectKeyword('switch');

        self.expect('(');

        discriminant = self.parseExpression();

        self.expect(')');

        self.expect('{');

        cases = [];

        if (self.match('}')):
            self.lex();
            return node.finishSwitchStatement(discriminant, cases);

        oldInSwitch = self.state['inSwitch'];
        self.state['inSwitch'] = true;
        defaultFound = false;

        while (self.startIndex < self.length):
            if (self.match('}')):
                break;
            clause = self.parseSwitchCase();
            if (clause.test == null):
                if (defaultFound):
                    self.throwError(Messages.MultipleDefaultsInSwitch);
                defaultFound = true;
            cases.append(clause);

        self.state['inSwitch'] = oldInSwitch;

        self.expect('}');

        return node.finishSwitchStatement(discriminant, cases);

    # 12.13 The throw statement

    def parseThrowStatement(self, node):

        self.expectKeyword('throw');

        if (self.hasLineTerminator):
            self.throwError(Messages.NewlineAfterThrow);

        argument = self.parseExpression();

        self.consumeSemicolon();

        return node.finishThrowStatement(argument);

    # 12.14 The try statement

    def parseCatchClause(self):
        node = Node();

        self.expectKeyword('catch');

        self.expect('(');
        if (self.match(')')):
            self.throwUnexpectedToken(self.lookahead);
        param = self.parsePattern();

        # 12.14.1
        if (self.strict and isRestrictedWord(param.name)):
            self.tolerateError(Messages.StrictCatchVariable);

        self.expect(')');
        body = self.parseBlock();
        return node.finishCatchClause(param, body);

    def parseTryStatement(self, node):
        handler = null
        finalizer = null;

        self.expectKeyword('try');

        block = self.parseBlock();

        if (self.matchKeyword('catch')):
            handler = self.parseCatchClause()

        if (self.matchKeyword('finally')):
            self.lex();
            finalizer = self.parseBlock();

        if (not handler and not finalizer):
            self.throwError(Messages.NoCatchOrFinally)

        return node.finishTryStatement(block, handler, finalizer)

    # 12.15 The debugger statement

    def parseDebuggerStatement(self, node):
        self.expectKeyword('debugger');

        self.consumeSemicolon();

        return node.finishDebuggerStatement();

    # 12 Statements

    def parseStatement(self):
        typ = self.lookahead['type']

        if (typ == Token.EOF):
            self.throwUnexpectedToken(self.lookahead)

        if (typ == Token.Punctuator and self.lookahead['value'] == '{'):
            return self.parseBlock()

        self.isAssignmentTarget = self.isBindingElement = true;
        node = Node();
        node.comments = self.lookahead.get('comments', [])
        val = self.lookahead['value']

        if (typ == Token.Punctuator):
            if val == ';':
                return self.parseEmptyStatement(node);
            elif val == '(':
                return self.parseExpressionStatement(node);
        elif (typ == Token.Keyword):
            if val == 'break':
                return self.parseBreakStatement(node);
            elif val == 'continue':
                return self.parseContinueStatement(node);
            elif val == 'debugger':
                return self.parseDebuggerStatement(node);
            elif val == 'do':
                return self.parseDoWhileStatement(node);
            elif val == 'for':
                return self.parseForStatement(node);
            elif val == 'function':
                return self.parseFunctionDeclaration(node);
            elif val == 'if':
                return self.parseIfStatement(node);
            elif val == 'return':
                return self.parseReturnStatement(node);
            elif val == 'switch':
                return self.parseSwitchStatement(node);
            elif val == 'throw':
                return self.parseThrowStatement(node);
            elif val == 'try':
                return self.parseTryStatement(node);
            elif val == 'var':
                return self.parseVariableStatement(node);
            elif val == 'while':
                return self.parseWhileStatement(node);
            elif val == 'with':
                return self.parseWithStatement(node);

        expr = self.parseExpression();

        # 12.12 Labelled Statements
        if ((expr.type == Syntax.Identifier) and self.match(':')):
            self.lex();

            key = '$' + expr.name
            if key in self.state['labelSet']:
                self.throwError(Messages.Redeclaration, 'Label', expr.name);
            self.state['labelSet'][key] = true
            labeledBody = self.parseStatement()
            del self.state['labelSet'][key]
            return node.finishLabeledStatement(expr, labeledBody)
        self.consumeSemicolon();
        return node.finishExpressionStatement(expr)

    # 13 Function Definition

    def parseFunctionSourceElements(self):
        body = []
        node = Node()
        firstRestricted = None

        self.expect('{')

        while (self.startIndex < self.length):
            if (self.lookahead['type'] != Token.StringLiteral):
                break
            token = self.lookahead;

            statement = self.parseStatementListItem()
            body.append(statement)
            if (statement.expression.type != Syntax.Literal):
                # this is not directive
                break
            directive = self.source[token['start'] + 1: token['end'] - 1]
            if (directive == 'use strict'):
                self.strict = true;
                if (firstRestricted):
                    self.tolerateUnexpectedToken(firstRestricted, Messages.StrictOctalLiteral);
            else:
                if (not firstRestricted and token.get('octal')):
                    firstRestricted = token;

        oldLabelSet = self.state['labelSet']
        oldInIteration = self.state['inIteration']
        oldInSwitch = self.state['inSwitch']
        oldInFunctionBody = self.state['inFunctionBody']
        oldParenthesisCount = self.state['parenthesizedCount']

        self.state['labelSet'] = {}
        self.state['inIteration'] = false
        self.state['inSwitch'] = false
        self.state['inFunctionBody'] = true
        self.state['parenthesizedCount'] = 0

        while (self.startIndex < self.length):
            if (self.match('}')):
                break
            body.append(self.parseStatementListItem())
        self.expect('}')

        self.state['labelSet'] = oldLabelSet;
        self.state['inIteration'] = oldInIteration;
        self.state['inSwitch'] = oldInSwitch;
        self.state['inFunctionBody'] = oldInFunctionBody;
        self.state['parenthesizedCount'] = oldParenthesisCount;

        return node.finishBlockStatement(body)

    def validateParam(self, options, param, name):
        key = '$' + name
        if (self.strict):
            if (isRestrictedWord(name)):
                options['stricted'] = param;
                options['message'] = Messages.StrictParamName
            if key in options['paramSet']:
                options['stricted'] = param;
                options['message'] = Messages.StrictParamDupe;
        elif (not options['firstRestricted']):
            if (isRestrictedWord(name)):
                options['firstRestricted'] = param;
                options['message'] = Messages.StrictParamName;
            elif (isStrictModeReservedWord(name)):
                options['firstRestricted'] = param;
                options['message'] = Messages.StrictReservedWord;
            elif key in options['paramSet']:
                options['firstRestricted'] = param
                options['message'] = Messages.StrictParamDupe;
        options['paramSet'][key] = true

    def parseParam(self, options):
        token = self.lookahead
        de = None
        if (token['value'] == '...'):
            param = self.parseRestElement();
            self.validateParam(options, param.argument, param.argument.name);
            options['params'].append(param);
            options['defaults'].append(null);
            return false
        param = self.parsePatternWithDefault();
        self.validateParam(options, token, token['value']);

        if (param.type == Syntax.AssignmentPattern):
            de = param.right;
            param = param.left;
            options['defaultCount'] += 1
        options['params'].append(param);
        options['defaults'].append(de)
        return not self.match(')')

    def parseParams(self, firstRestricted):
        options = {
            'params': [],
            'defaultCount': 0,
            'defaults': [],
            'firstRestricted': firstRestricted}

        self.expect('(');

        if (not self.match(')')):
            options['paramSet'] = {};
            while (self.startIndex < self.length):
                if (not self.parseParam(options)):
                    break
                self.expect(',');
        self.expect(')');

        if (options['defaultCount'] == 0):
            options['defaults'] = [];

        return {
            'params': options['params'],
            'defaults': options['defaults'],
            'stricted': options.get('stricted'),
            'firstRestricted': options.get('firstRestricted'),
            'message': options.get('message')}

    def parseFunctionDeclaration(self, node, identifierIsOptional=None):
        node.comments = self.lookahead.get('comments', [])
        d = null
        params = []
        defaults = []
        message = None
        firstRestricted = None

        self.expectKeyword('function');
        if (identifierIsOptional or not self.match('(')):
            token = self.lookahead;
            d = self.parseVariableIdentifier();
            if (self.strict):
                if (isRestrictedWord(token['value'])):
                    self.tolerateUnexpectedToken(token, Messages.StrictFunctionName);
            else:
                if (isRestrictedWord(token['value'])):
                    firstRestricted = token;
                    message = Messages.StrictFunctionName;
                elif (isStrictModeReservedWord(token['value'])):
                    firstRestricted = token;
                    message = Messages.StrictReservedWord;

        tmp = self.parseParams(firstRestricted);
        params = tmp['params']
        defaults = tmp['defaults']
        stricted = tmp.get('stricted')
        firstRestricted = tmp['firstRestricted']
        if (tmp.get('message')):
            message = tmp['message'];

        previousStrict = self.strict;
        body = self.parseFunctionSourceElements();
        if (self.strict and firstRestricted):
            self.throwUnexpectedToken(firstRestricted, message);

        if (self.strict and stricted):
            self.tolerateUnexpectedToken(stricted, message);
        self.strict = previousStrict;

        return node.finishFunctionDeclaration(d, params, defaults, body);

    def parseFunctionExpression(self):
        id = null
        params = []
        defaults = []
        node = Node();
        node.comments = self.lookahead.get('comments', [])
        firstRestricted = None
        message = None

        self.expectKeyword('function');

        if (not self.match('(')):
            token = self.lookahead;
            id = self.parseVariableIdentifier();
            if (self.strict):
                if (isRestrictedWord(token['value'])):
                    self.tolerateUnexpectedToken(token, Messages.StrictFunctionName);
            else:
                if (isRestrictedWord(token['value'])):
                    firstRestricted = token;
                    message = Messages.StrictFunctionName;
                elif (isStrictModeReservedWord(token['value'])):
                    firstRestricted = token;
                    message = Messages.StrictReservedWord;
        tmp = self.parseParams(firstRestricted);
        params = tmp['params']
        defaults = tmp['defaults']
        stricted = tmp.get('stricted')
        firstRestricted = tmp['firstRestricted']
        if (tmp.get('message')):
            message = tmp['message']

        previousStrict = self.strict;
        body = self.parseFunctionSourceElements();
        if (self.strict and firstRestricted):
            self.throwUnexpectedToken(firstRestricted, message);
        if (self.strict and stricted):
            self.tolerateUnexpectedToken(stricted, message);
        self.strict = previousStrict;

        return node.finishFunctionExpression(id, params, defaults, body);

    # todo Translate parse class functions!

    def parseClassExpression(self):
        raise NotImplementedError()

    def parseClassDeclaration(self):
        raise NotImplementedError()

    # 14 Program

    def parseScriptBody(self):
        body = []
        firstRestricted = None

        while (self.startIndex < self.length):
            token = self.lookahead;
            if (token['type'] != Token.StringLiteral):
                break
            statement = self.parseStatementListItem();
            body.append(statement);
            if (statement.expression.type != Syntax.Literal):
                # this is not directive
                break
            directive = self.source[token['start'] + 1: token['end'] - 1]
            if (directive == 'use strict'):
                self.strict = true;
                if (firstRestricted):
                    self.tolerateUnexpectedToken(firstRestricted, Messages.StrictOctalLiteral)
            else:
                if (not firstRestricted and token.get('octal')):
                    firstRestricted = token;
        while (self.startIndex < self.length):
            statement = self.parseStatementListItem();
            # istanbul ignore if
            if (statement is None):
                break
            body.append(statement);
        return body;

    def parseProgram(self):
        self.peek()
        node = Node()

        body = self.parseScriptBody()
        return node.finishProgram(body)

    # DONE!!!
    def parse(self, code, options={}):
        if options:
            raise NotImplementedError('Options not implemented! You can only use default settings.')

        self.clean()
        self.source = str(code) + ' \n ; //END'  # I have to add it in order not to check for EOF every time
        self.index = 0
        self.lineNumber = 1 if len(self.source) > 0 else 0
        self.lineStart = 0
        self.startIndex = self.index
        self.startLineNumber = self.lineNumber;
        self.startLineStart = self.lineStart;
        self.length = len(self.source)
        self.lookahead = null;
        self.state = {
            'allowIn': true,
            'labelSet': {},
            'inFunctionBody': false,
            'inIteration': false,
            'inSwitch': false,
            'lastCommentStart': -1,
            'curlyStack': [],
            'parenthesizedCount': None}
        self.sourceType = 'script';
        self.strict = false;
        program = self.parseProgram();
        return node_to_dict(program)



def parse(javascript_code):
    """Returns syntax tree of javascript_code.
       Same as PyJsParser().parse  For your convenience :) """
    p = PyJsParser()
    return p.parse(javascript_code)


if __name__ == '__main__':
    import time

    test_path = None
    if test_path:
        f = open(test_path, 'rb')
        x = f.read()
        f.close()
    else:
        x = 'var $ = "Hello!"'
    p = PyJsParser()
    t = time.time()
    res = p.parse(x)
    dt = time.time() - t + 0.000000001
    if test_path:
        print(len(res))
    else:
        pprint(res)
    print()
    print('Parsed everyting in', round(dt, 5), 'seconds.')
    print('Thats %d characters per second' % int(len(x) / dt))



