/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */
/* Copyright 2012 Mozilla Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/* globals FONT_IDENTITY_MATRIX, FontType, warn, GlyphsUnicode, error, string32,
           readUint32, Stream, FontRendererFactory, shadow, stringToBytes,
           bytesToString, info, assert, IdentityCMap, Name, CMapFactory, PDFJS,
           isNum, Lexer, isArray, ISOAdobeCharset, ExpertCharset,
           ExpertSubsetCharset, Util, DingbatsGlyphsUnicode */

'use strict';

// Unicode Private Use Area
var PRIVATE_USE_OFFSET_START = 0xE000;
var PRIVATE_USE_OFFSET_END = 0xF8FF;
var SKIP_PRIVATE_USE_RANGE_F000_TO_F01F = false;

// PDF Glyph Space Units are one Thousandth of a TextSpace Unit
// except for Type 3 fonts
var PDF_GLYPH_SPACE_UNITS = 1000;

// Hinting is currently disabled due to unknown problems on windows
// in tracemonkey and various other pdfs with type1 fonts.
var HINTING_ENABLED = false;

// Accented charactars are not displayed properly on windows, using this flag
// to control analysis of seac charstrings.
var SEAC_ANALYSIS_ENABLED = false;

var FontFlags = {
  FixedPitch: 1,
  Serif: 2,
  Symbolic: 4,
  Script: 8,
  Nonsymbolic: 32,
  Italic: 64,
  AllCap: 65536,
  SmallCap: 131072,
  ForceBold: 262144
};

var Encodings = {
  ExpertEncoding: ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    'space', 'exclamsmall', 'Hungarumlautsmall', '', 'dollaroldstyle',
    'dollarsuperior', 'ampersandsmall', 'Acutesmall', 'parenleftsuperior',
    'parenrightsuperior', 'twodotenleader', 'onedotenleader', 'comma',
    'hyphen', 'period', 'fraction', 'zerooldstyle', 'oneoldstyle',
    'twooldstyle', 'threeoldstyle', 'fouroldstyle', 'fiveoldstyle',
    'sixoldstyle', 'sevenoldstyle', 'eightoldstyle', 'nineoldstyle', 'colon',
    'semicolon', 'commasuperior', 'threequartersemdash', 'periodsuperior',
    'questionsmall', '', 'asuperior', 'bsuperior', 'centsuperior', 'dsuperior',
    'esuperior', '', '', 'isuperior', '', '', 'lsuperior', 'msuperior',
    'nsuperior', 'osuperior', '', '', 'rsuperior', 'ssuperior', 'tsuperior',
    '', 'ff', 'fi', 'fl', 'ffi', 'ffl', 'parenleftinferior', '',
    'parenrightinferior', 'Circumflexsmall', 'hyphensuperior', 'Gravesmall',
    'Asmall', 'Bsmall', 'Csmall', 'Dsmall', 'Esmall', 'Fsmall', 'Gsmall',
    'Hsmall', 'Ismall', 'Jsmall', 'Ksmall', 'Lsmall', 'Msmall', 'Nsmall',
    'Osmall', 'Psmall', 'Qsmall', 'Rsmall', 'Ssmall', 'Tsmall', 'Usmall',
    'Vsmall', 'Wsmall', 'Xsmall', 'Ysmall', 'Zsmall', 'colonmonetary',
    'onefitted', 'rupiah', 'Tildesmall', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', 'exclamdownsmall', 'centoldstyle', 'Lslashsmall',
    '', '', 'Scaronsmall', 'Zcaronsmall', 'Dieresissmall', 'Brevesmall',
    'Caronsmall', '', 'Dotaccentsmall', '', '', 'Macronsmall', '', '',
    'figuredash', 'hypheninferior', '', '', 'Ogoneksmall', 'Ringsmall',
    'Cedillasmall', '', '', '', 'onequarter', 'onehalf', 'threequarters',
    'questiondownsmall', 'oneeighth', 'threeeighths', 'fiveeighths',
    'seveneighths', 'onethird', 'twothirds', '', '', 'zerosuperior',
    'onesuperior', 'twosuperior', 'threesuperior', 'foursuperior',
    'fivesuperior', 'sixsuperior', 'sevensuperior', 'eightsuperior',
    'ninesuperior', 'zeroinferior', 'oneinferior', 'twoinferior',
    'threeinferior', 'fourinferior', 'fiveinferior', 'sixinferior',
    'seveninferior', 'eightinferior', 'nineinferior', 'centinferior',
    'dollarinferior', 'periodinferior', 'commainferior', 'Agravesmall',
    'Aacutesmall', 'Acircumflexsmall', 'Atildesmall', 'Adieresissmall',
    'Aringsmall', 'AEsmall', 'Ccedillasmall', 'Egravesmall', 'Eacutesmall',
    'Ecircumflexsmall', 'Edieresissmall', 'Igravesmall', 'Iacutesmall',
    'Icircumflexsmall', 'Idieresissmall', 'Ethsmall', 'Ntildesmall',
    'Ogravesmall', 'Oacutesmall', 'Ocircumflexsmall', 'Otildesmall',
    'Odieresissmall', 'OEsmall', 'Oslashsmall', 'Ugravesmall', 'Uacutesmall',
    'Ucircumflexsmall', 'Udieresissmall', 'Yacutesmall', 'Thornsmall',
    'Ydieresissmall'],
  MacExpertEncoding: ['', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    'space', 'exclamsmall', 'Hungarumlautsmall', 'centoldstyle',
    'dollaroldstyle', 'dollarsuperior', 'ampersandsmall', 'Acutesmall',
    'parenleftsuperior', 'parenrightsuperior', 'twodotenleader',
    'onedotenleader', 'comma', 'hyphen', 'period', 'fraction', 'zerooldstyle',
    'oneoldstyle', 'twooldstyle', 'threeoldstyle', 'fouroldstyle',
    'fiveoldstyle', 'sixoldstyle', 'sevenoldstyle', 'eightoldstyle',
    'nineoldstyle', 'colon', 'semicolon', '', 'threequartersemdash', '',
    'questionsmall', '', '', '', '', 'Ethsmall', '', '', 'onequarter',
    'onehalf', 'threequarters', 'oneeighth', 'threeeighths', 'fiveeighths',
    'seveneighths', 'onethird', 'twothirds', '', '', '', '', '', '', 'ff',
    'fi', 'fl', 'ffi', 'ffl', 'parenleftinferior', '', 'parenrightinferior',
    'Circumflexsmall', 'hypheninferior', 'Gravesmall', 'Asmall', 'Bsmall',
    'Csmall', 'Dsmall', 'Esmall', 'Fsmall', 'Gsmall', 'Hsmall', 'Ismall',
    'Jsmall', 'Ksmall', 'Lsmall', 'Msmall', 'Nsmall', 'Osmall', 'Psmall',
    'Qsmall', 'Rsmall', 'Ssmall', 'Tsmall', 'Usmall', 'Vsmall', 'Wsmall',
    'Xsmall', 'Ysmall', 'Zsmall', 'colonmonetary', 'onefitted', 'rupiah',
    'Tildesmall', '', '', 'asuperior', 'centsuperior', '', '', '', '',
    'Aacutesmall', 'Agravesmall', 'Acircumflexsmall', 'Adieresissmall',
    'Atildesmall', 'Aringsmall', 'Ccedillasmall', 'Eacutesmall', 'Egravesmall',
    'Ecircumflexsmall', 'Edieresissmall', 'Iacutesmall', 'Igravesmall',
    'Icircumflexsmall', 'Idieresissmall', 'Ntildesmall', 'Oacutesmall',
    'Ogravesmall', 'Ocircumflexsmall', 'Odieresissmall', 'Otildesmall',
    'Uacutesmall', 'Ugravesmall', 'Ucircumflexsmall', 'Udieresissmall', '',
    'eightsuperior', 'fourinferior', 'threeinferior', 'sixinferior',
    'eightinferior', 'seveninferior', 'Scaronsmall', '', 'centinferior',
    'twoinferior', '', 'Dieresissmall', '', 'Caronsmall', 'osuperior',
    'fiveinferior', '', 'commainferior', 'periodinferior', 'Yacutesmall', '',
    'dollarinferior', '', 'Thornsmall', '', 'nineinferior', 'zeroinferior',
    'Zcaronsmall', 'AEsmall', 'Oslashsmall', 'questiondownsmall',
    'oneinferior', 'Lslashsmall', '', '', '', '', '', '', 'Cedillasmall', '',
    '', '', '', '', 'OEsmall', 'figuredash', 'hyphensuperior', '', '', '', '',
    'exclamdownsmall', '', 'Ydieresissmall', '', 'onesuperior', 'twosuperior',
    'threesuperior', 'foursuperior', 'fivesuperior', 'sixsuperior',
    'sevensuperior', 'ninesuperior', 'zerosuperior', '', 'esuperior',
    'rsuperior', 'tsuperior', '', '', 'isuperior', 'ssuperior', 'dsuperior',
    '', '', '', '', '', 'lsuperior', 'Ogoneksmall', 'Brevesmall',
    'Macronsmall', 'bsuperior', 'nsuperior', 'msuperior', 'commasuperior',
    'periodsuperior', 'Dotaccentsmall', 'Ringsmall'],
  MacRomanEncoding: ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    'space', 'exclam', 'quotedbl', 'numbersign', 'dollar', 'percent',
    'ampersand', 'quotesingle', 'parenleft', 'parenright', 'asterisk', 'plus',
    'comma', 'hyphen', 'period', 'slash', 'zero', 'one', 'two', 'three',
    'four', 'five', 'six', 'seven', 'eight', 'nine', 'colon', 'semicolon',
    'less', 'equal', 'greater', 'question', 'at', 'A', 'B', 'C', 'D', 'E', 'F',
    'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U',
    'V', 'W', 'X', 'Y', 'Z', 'bracketleft', 'backslash', 'bracketright',
    'asciicircum', 'underscore', 'grave', 'a', 'b', 'c', 'd', 'e', 'f', 'g',
    'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v',
    'w', 'x', 'y', 'z', 'braceleft', 'bar', 'braceright', 'asciitilde', '',
    'Adieresis', 'Aring', 'Ccedilla', 'Eacute', 'Ntilde', 'Odieresis',
    'Udieresis', 'aacute', 'agrave', 'acircumflex', 'adieresis', 'atilde',
    'aring', 'ccedilla', 'eacute', 'egrave', 'ecircumflex', 'edieresis',
    'iacute', 'igrave', 'icircumflex', 'idieresis', 'ntilde', 'oacute',
    'ograve', 'ocircumflex', 'odieresis', 'otilde', 'uacute', 'ugrave',
    'ucircumflex', 'udieresis', 'dagger', 'degree', 'cent', 'sterling',
    'section', 'bullet', 'paragraph', 'germandbls', 'registered', 'copyright',
    'trademark', 'acute', 'dieresis', 'notequal', 'AE', 'Oslash', 'infinity',
    'plusminus', 'lessequal', 'greaterequal', 'yen', 'mu', 'partialdiff',
    'summation', 'product', 'pi', 'integral', 'ordfeminine', 'ordmasculine',
    'Omega', 'ae', 'oslash', 'questiondown', 'exclamdown', 'logicalnot',
    'radical', 'florin', 'approxequal', 'Delta', 'guillemotleft',
    'guillemotright', 'ellipsis', 'space', 'Agrave', 'Atilde', 'Otilde', 'OE',
    'oe', 'endash', 'emdash', 'quotedblleft', 'quotedblright', 'quoteleft',
    'quoteright', 'divide', 'lozenge', 'ydieresis', 'Ydieresis', 'fraction',
    'currency', 'guilsinglleft', 'guilsinglright', 'fi', 'fl', 'daggerdbl',
    'periodcentered', 'quotesinglbase', 'quotedblbase', 'perthousand',
    'Acircumflex', 'Ecircumflex', 'Aacute', 'Edieresis', 'Egrave', 'Iacute',
    'Icircumflex', 'Idieresis', 'Igrave', 'Oacute', 'Ocircumflex', 'apple',
    'Ograve', 'Uacute', 'Ucircumflex', 'Ugrave', 'dotlessi', 'circumflex',
    'tilde', 'macron', 'breve', 'dotaccent', 'ring', 'cedilla', 'hungarumlaut',
    'ogonek', 'caron'],
  StandardEncoding: ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    'space', 'exclam', 'quotedbl', 'numbersign', 'dollar', 'percent',
    'ampersand', 'quoteright', 'parenleft', 'parenright', 'asterisk', 'plus',
    'comma', 'hyphen', 'period', 'slash', 'zero', 'one', 'two', 'three',
    'four', 'five', 'six', 'seven', 'eight', 'nine', 'colon', 'semicolon',
    'less', 'equal', 'greater', 'question', 'at', 'A', 'B', 'C', 'D', 'E', 'F',
    'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U',
    'V', 'W', 'X', 'Y', 'Z', 'bracketleft', 'backslash', 'bracketright',
    'asciicircum', 'underscore', 'quoteleft', 'a', 'b', 'c', 'd', 'e', 'f',
    'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
    'v', 'w', 'x', 'y', 'z', 'braceleft', 'bar', 'braceright', 'asciitilde',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 'exclamdown',
    'cent', 'sterling', 'fraction', 'yen', 'florin', 'section', 'currency',
    'quotesingle', 'quotedblleft', 'guillemotleft', 'guilsinglleft',
    'guilsinglright', 'fi', 'fl', '', 'endash', 'dagger', 'daggerdbl',
    'periodcentered', '', 'paragraph', 'bullet', 'quotesinglbase',
    'quotedblbase', 'quotedblright', 'guillemotright', 'ellipsis',
    'perthousand', '', 'questiondown', '', 'grave', 'acute', 'circumflex',
    'tilde', 'macron', 'breve', 'dotaccent', 'dieresis', '', 'ring', 'cedilla',
    '', 'hungarumlaut', 'ogonek', 'caron', 'emdash', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', 'AE', '', 'ordfeminine', '', '',
    '', '', 'Lslash', 'Oslash', 'OE', 'ordmasculine', '', '', '', '', '', 'ae',
    '', '', '', 'dotlessi', '', '', 'lslash', 'oslash', 'oe', 'germandbls'],
  WinAnsiEncoding: ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    'space', 'exclam', 'quotedbl', 'numbersign', 'dollar', 'percent',
    'ampersand', 'quotesingle', 'parenleft', 'parenright', 'asterisk', 'plus',
    'comma', 'hyphen', 'period', 'slash', 'zero', 'one', 'two', 'three',
    'four', 'five', 'six', 'seven', 'eight', 'nine', 'colon', 'semicolon',
    'less', 'equal', 'greater', 'question', 'at', 'A', 'B', 'C', 'D', 'E', 'F',
    'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U',
    'V', 'W', 'X', 'Y', 'Z', 'bracketleft', 'backslash', 'bracketright',
    'asciicircum', 'underscore', 'grave', 'a', 'b', 'c', 'd', 'e', 'f', 'g',
    'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v',
    'w', 'x', 'y', 'z', 'braceleft', 'bar', 'braceright', 'asciitilde',
    'bullet', 'Euro', 'bullet', 'quotesinglbase', 'florin', 'quotedblbase',
    'ellipsis', 'dagger', 'daggerdbl', 'circumflex', 'perthousand', 'Scaron',
    'guilsinglleft', 'OE', 'bullet', 'Zcaron', 'bullet', 'bullet', 'quoteleft',
    'quoteright', 'quotedblleft', 'quotedblright', 'bullet', 'endash',
    'emdash', 'tilde', 'trademark', 'scaron', 'guilsinglright', 'oe', 'bullet',
    'zcaron', 'Ydieresis', 'space', 'exclamdown', 'cent', 'sterling',
    'currency', 'yen', 'brokenbar', 'section', 'dieresis', 'copyright',
    'ordfeminine', 'guillemotleft', 'logicalnot', 'hyphen', 'registered',
    'macron', 'degree', 'plusminus', 'twosuperior', 'threesuperior', 'acute',
    'mu', 'paragraph', 'periodcentered', 'cedilla', 'onesuperior',
    'ordmasculine', 'guillemotright', 'onequarter', 'onehalf', 'threequarters',
    'questiondown', 'Agrave', 'Aacute', 'Acircumflex', 'Atilde', 'Adieresis',
    'Aring', 'AE', 'Ccedilla', 'Egrave', 'Eacute', 'Ecircumflex', 'Edieresis',
    'Igrave', 'Iacute', 'Icircumflex', 'Idieresis', 'Eth', 'Ntilde', 'Ograve',
    'Oacute', 'Ocircumflex', 'Otilde', 'Odieresis', 'multiply', 'Oslash',
    'Ugrave', 'Uacute', 'Ucircumflex', 'Udieresis', 'Yacute', 'Thorn',
    'germandbls', 'agrave', 'aacute', 'acircumflex', 'atilde', 'adieresis',
    'aring', 'ae', 'ccedilla', 'egrave', 'eacute', 'ecircumflex', 'edieresis',
    'igrave', 'iacute', 'icircumflex', 'idieresis', 'eth', 'ntilde', 'ograve',
    'oacute', 'ocircumflex', 'otilde', 'odieresis', 'divide', 'oslash',
    'ugrave', 'uacute', 'ucircumflex', 'udieresis', 'yacute', 'thorn',
    'ydieresis'],
  SymbolSetEncoding: ['', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    'space', 'exclam', 'universal', 'numbersign', 'existential', 'percent',
    'ampersand', 'suchthat', 'parenleft', 'parenright', 'asteriskmath', 'plus',
    'comma', 'minus', 'period', 'slash', 'zero', 'one', 'two', 'three', 'four',
    'five', 'six', 'seven', 'eight', 'nine', 'colon', 'semicolon', 'less',
    'equal', 'greater', 'question', 'congruent', 'Alpha', 'Beta', 'Chi',
    'Delta', 'Epsilon', 'Phi', 'Gamma', 'Eta', 'Iota', 'theta1', 'Kappa',
    'Lambda', 'Mu', 'Nu', 'Omicron', 'Pi', 'Theta', 'Rho', 'Sigma', 'Tau',
    'Upsilon', 'sigma1', 'Omega', 'Xi', 'Psi', 'Zeta', 'bracketleft',
    'therefore', 'bracketright', 'perpendicular', 'underscore', 'radicalex',
    'alpha', 'beta', 'chi', 'delta', 'epsilon', 'phi', 'gamma', 'eta', 'iota',
    'phi1', 'kappa', 'lambda', 'mu', 'nu', 'omicron', 'pi', 'theta', 'rho',
    'sigma', 'tau', 'upsilon', 'omega1', 'omega', 'xi', 'psi', 'zeta',
    'braceleft', 'bar', 'braceright', 'similar', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', 'Euro', 'Upsilon1', 'minute', 'lessequal',
    'fraction', 'infinity', 'florin', 'club', 'diamond', 'heart', 'spade',
    'arrowboth', 'arrowleft', 'arrowup', 'arrowright', 'arrowdown', 'degree',
    'plusminus', 'second', 'greaterequal', 'multiply', 'proportional',
    'partialdiff', 'bullet', 'divide', 'notequal', 'equivalence',
    'approxequal', 'ellipsis', 'arrowvertex', 'arrowhorizex', 'carriagereturn',
    'aleph', 'Ifraktur', 'Rfraktur', 'weierstrass', 'circlemultiply',
    'circleplus', 'emptyset', 'intersection', 'union', 'propersuperset',
    'reflexsuperset', 'notsubset', 'propersubset', 'reflexsubset', 'element',
    'notelement', 'angle', 'gradient', 'registerserif', 'copyrightserif',
    'trademarkserif', 'product', 'radical', 'dotmath', 'logicalnot',
    'logicaland', 'logicalor', 'arrowdblboth', 'arrowdblleft', 'arrowdblup',
    'arrowdblright', 'arrowdbldown', 'lozenge', 'angleleft', 'registersans',
    'copyrightsans', 'trademarksans', 'summation', 'parenlefttp',
    'parenleftex', 'parenleftbt', 'bracketlefttp', 'bracketleftex',
    'bracketleftbt', 'bracelefttp', 'braceleftmid', 'braceleftbt', 'braceex',
    '', 'angleright', 'integral', 'integraltp', 'integralex', 'integralbt',
    'parenrighttp', 'parenrightex', 'parenrightbt', 'bracketrighttp',
    'bracketrightex', 'bracketrightbt', 'bracerighttp', 'bracerightmid',
    'bracerightbt'],
  ZapfDingbatsEncoding: ['', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    'space', 'a1', 'a2', 'a202', 'a3', 'a4', 'a5', 'a119', 'a118', 'a117',
    'a11', 'a12', 'a13', 'a14', 'a15', 'a16', 'a105', 'a17', 'a18', 'a19',
    'a20', 'a21', 'a22', 'a23', 'a24', 'a25', 'a26', 'a27', 'a28', 'a6', 'a7',
    'a8', 'a9', 'a10', 'a29', 'a30', 'a31', 'a32', 'a33', 'a34', 'a35', 'a36',
    'a37', 'a38', 'a39', 'a40', 'a41', 'a42', 'a43', 'a44', 'a45', 'a46',
    'a47', 'a48', 'a49', 'a50', 'a51', 'a52', 'a53', 'a54', 'a55', 'a56',
    'a57', 'a58', 'a59', 'a60', 'a61', 'a62', 'a63', 'a64', 'a65', 'a66',
    'a67', 'a68', 'a69', 'a70', 'a71', 'a72', 'a73', 'a74', 'a203', 'a75',
    'a204', 'a76', 'a77', 'a78', 'a79', 'a81', 'a82', 'a83', 'a84', 'a97',
    'a98', 'a99', 'a100', '', 'a89', 'a90', 'a93', 'a94', 'a91', 'a92', 'a205',
    'a85', 'a206', 'a86', 'a87', 'a88', 'a95', 'a96', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', 'a101', 'a102', 'a103',
    'a104', 'a106', 'a107', 'a108', 'a112', 'a111', 'a110', 'a109', 'a120',
    'a121', 'a122', 'a123', 'a124', 'a125', 'a126', 'a127', 'a128', 'a129',
    'a130', 'a131', 'a132', 'a133', 'a134', 'a135', 'a136', 'a137', 'a138',
    'a139', 'a140', 'a141', 'a142', 'a143', 'a144', 'a145', 'a146', 'a147',
    'a148', 'a149', 'a150', 'a151', 'a152', 'a153', 'a154', 'a155', 'a156',
    'a157', 'a158', 'a159', 'a160', 'a161', 'a163', 'a164', 'a196', 'a165',
    'a192', 'a166', 'a167', 'a168', 'a169', 'a170', 'a171', 'a172', 'a173',
    'a162', 'a174', 'a175', 'a176', 'a177', 'a178', 'a179', 'a193', 'a180',
    'a199', 'a181', 'a200', 'a182', '', 'a201', 'a183', 'a184', 'a197', 'a185',
    'a194', 'a198', 'a186', 'a195', 'a187', 'a188', 'a189', 'a190', 'a191']
};

/**
 * Hold a map of decoded fonts and of the standard fourteen Type1
 * fonts and their acronyms.
 */
var stdFontMap = {
  'ArialNarrow': 'Helvetica',
  'ArialNarrow-Bold': 'Helvetica-Bold',
  'ArialNarrow-BoldItalic': 'Helvetica-BoldOblique',
  'ArialNarrow-Italic': 'Helvetica-Oblique',
  'ArialBlack': 'Helvetica',
  'ArialBlack-Bold': 'Helvetica-Bold',
  'ArialBlack-BoldItalic': 'Helvetica-BoldOblique',
  'ArialBlack-Italic': 'Helvetica-Oblique',
  'Arial': 'Helvetica',
  'Arial-Bold': 'Helvetica-Bold',
  'Arial-BoldItalic': 'Helvetica-BoldOblique',
  'Arial-Italic': 'Helvetica-Oblique',
  'Arial-BoldItalicMT': 'Helvetica-BoldOblique',
  'Arial-BoldMT': 'Helvetica-Bold',
  'Arial-ItalicMT': 'Helvetica-Oblique',
  'ArialMT': 'Helvetica',
  'Courier-Bold': 'Courier-Bold',
  'Courier-BoldItalic': 'Courier-BoldOblique',
  'Courier-Italic': 'Courier-Oblique',
  'CourierNew': 'Courier',
  'CourierNew-Bold': 'Courier-Bold',
  'CourierNew-BoldItalic': 'Courier-BoldOblique',
  'CourierNew-Italic': 'Courier-Oblique',
  'CourierNewPS-BoldItalicMT': 'Courier-BoldOblique',
  'CourierNewPS-BoldMT': 'Courier-Bold',
  'CourierNewPS-ItalicMT': 'Courier-Oblique',
  'CourierNewPSMT': 'Courier',
  'Helvetica': 'Helvetica',
  'Helvetica-Bold': 'Helvetica-Bold',
  'Helvetica-BoldItalic': 'Helvetica-BoldOblique',
  'Helvetica-BoldOblique': 'Helvetica-BoldOblique',
  'Helvetica-Italic': 'Helvetica-Oblique',
  'Helvetica-Oblique':'Helvetica-Oblique',
  'Symbol-Bold': 'Symbol',
  'Symbol-BoldItalic': 'Symbol',
  'Symbol-Italic': 'Symbol',
  'TimesNewRoman': 'Times-Roman',
  'TimesNewRoman-Bold': 'Times-Bold',
  'TimesNewRoman-BoldItalic': 'Times-BoldItalic',
  'TimesNewRoman-Italic': 'Times-Italic',
  'TimesNewRomanPS': 'Times-Roman',
  'TimesNewRomanPS-Bold': 'Times-Bold',
  'TimesNewRomanPS-BoldItalic': 'Times-BoldItalic',
  'TimesNewRomanPS-BoldItalicMT': 'Times-BoldItalic',
  'TimesNewRomanPS-BoldMT': 'Times-Bold',
  'TimesNewRomanPS-Italic': 'Times-Italic',
  'TimesNewRomanPS-ItalicMT': 'Times-Italic',
  'TimesNewRomanPSMT': 'Times-Roman',
  'TimesNewRomanPSMT-Bold': 'Times-Bold',
  'TimesNewRomanPSMT-BoldItalic': 'Times-BoldItalic',
  'TimesNewRomanPSMT-Italic': 'Times-Italic'
};

/**
 * Holds the map of the non-standard fonts that might be included as a standard
 * fonts without glyph data.
 */
var nonStdFontMap = {
  'CenturyGothic': 'Helvetica',
  'CenturyGothic-Bold': 'Helvetica-Bold',
  'CenturyGothic-BoldItalic': 'Helvetica-BoldOblique',
  'CenturyGothic-Italic': 'Helvetica-Oblique',
  'ComicSansMS': 'Comic Sans MS',
  'ComicSansMS-Bold': 'Comic Sans MS-Bold',
  'ComicSansMS-BoldItalic': 'Comic Sans MS-BoldItalic',
  'ComicSansMS-Italic': 'Comic Sans MS-Italic',
  'LucidaConsole': 'Courier',
  'LucidaConsole-Bold': 'Courier-Bold',
  'LucidaConsole-BoldItalic': 'Courier-BoldOblique',
  'LucidaConsole-Italic': 'Courier-Oblique',
  'MS-Gothic': 'MS Gothic',
  'MS-Gothic-Bold': 'MS Gothic-Bold',
  'MS-Gothic-BoldItalic': 'MS Gothic-BoldItalic',
  'MS-Gothic-Italic': 'MS Gothic-Italic',
  'MS-Mincho': 'MS Mincho',
  'MS-Mincho-Bold': 'MS Mincho-Bold',
  'MS-Mincho-BoldItalic': 'MS Mincho-BoldItalic',
  'MS-Mincho-Italic': 'MS Mincho-Italic',
  'MS-PGothic': 'MS PGothic',
  'MS-PGothic-Bold': 'MS PGothic-Bold',
  'MS-PGothic-BoldItalic': 'MS PGothic-BoldItalic',
  'MS-PGothic-Italic': 'MS PGothic-Italic',
  'MS-PMincho': 'MS PMincho',
  'MS-PMincho-Bold': 'MS PMincho-Bold',
  'MS-PMincho-BoldItalic': 'MS PMincho-BoldItalic',
  'MS-PMincho-Italic': 'MS PMincho-Italic',
  'Wingdings': 'ZapfDingbats'
};

var serifFonts = {
  'Adobe Jenson': true, 'Adobe Text': true, 'Albertus': true,
  'Aldus': true, 'Alexandria': true, 'Algerian': true,
  'American Typewriter': true, 'Antiqua': true, 'Apex': true,
  'Arno': true, 'Aster': true, 'Aurora': true,
  'Baskerville': true, 'Bell': true, 'Bembo': true,
  'Bembo Schoolbook': true, 'Benguiat': true, 'Berkeley Old Style': true,
  'Bernhard Modern': true, 'Berthold City': true, 'Bodoni': true,
  'Bauer Bodoni': true, 'Book Antiqua': true, 'Bookman': true,
  'Bordeaux Roman': true, 'Californian FB': true, 'Calisto': true,
  'Calvert': true, 'Capitals': true, 'Cambria': true,
  'Cartier': true, 'Caslon': true, 'Catull': true,
  'Centaur': true, 'Century Old Style': true, 'Century Schoolbook': true,
  'Chaparral': true, 'Charis SIL': true, 'Cheltenham': true,
  'Cholla Slab': true, 'Clarendon': true, 'Clearface': true,
  'Cochin': true, 'Colonna': true, 'Computer Modern': true,
  'Concrete Roman': true, 'Constantia': true, 'Cooper Black': true,
  'Corona': true, 'Ecotype': true, 'Egyptienne': true,
  'Elephant': true, 'Excelsior': true, 'Fairfield': true,
  'FF Scala': true, 'Folkard': true, 'Footlight': true,
  'FreeSerif': true, 'Friz Quadrata': true, 'Garamond': true,
  'Gentium': true, 'Georgia': true, 'Gloucester': true,
  'Goudy Old Style': true, 'Goudy Schoolbook': true, 'Goudy Pro Font': true,
  'Granjon': true, 'Guardian Egyptian': true, 'Heather': true,
  'Hercules': true, 'High Tower Text': true, 'Hiroshige': true,
  'Hoefler Text': true, 'Humana Serif': true, 'Imprint': true,
  'Ionic No. 5': true, 'Janson': true, 'Joanna': true,
  'Korinna': true, 'Lexicon': true, 'Liberation Serif': true,
  'Linux Libertine': true, 'Literaturnaya': true, 'Lucida': true,
  'Lucida Bright': true, 'Melior': true, 'Memphis': true,
  'Miller': true, 'Minion': true, 'Modern': true,
  'Mona Lisa': true, 'Mrs Eaves': true, 'MS Serif': true,
  'Museo Slab': true, 'New York': true, 'Nimbus Roman': true,
  'NPS Rawlinson Roadway': true, 'Palatino': true, 'Perpetua': true,
  'Plantin': true, 'Plantin Schoolbook': true, 'Playbill': true,
  'Poor Richard': true, 'Rawlinson Roadway': true, 'Renault': true,
  'Requiem': true, 'Rockwell': true, 'Roman': true,
  'Rotis Serif': true, 'Sabon': true, 'Scala': true,
  'Seagull': true, 'Sistina': true, 'Souvenir': true,
  'STIX': true, 'Stone Informal': true, 'Stone Serif': true,
  'Sylfaen': true, 'Times': true, 'Trajan': true,
  'Trinité': true, 'Trump Mediaeval': true, 'Utopia': true,
  'Vale Type': true, 'Bitstream Vera': true, 'Vera Serif': true,
  'Versailles': true, 'Wanted': true, 'Weiss': true,
  'Wide Latin': true, 'Windsor': true, 'XITS': true
};

var symbolsFonts = {
  'Dingbats': true, 'Symbol': true, 'ZapfDingbats': true
};

// Glyph map for well-known standard fonts. Sometimes Ghostscript uses CID fonts
// but does not embed the CID to GID mapping. The mapping is incomplete for all
// glyphs, but common for some set of the standard fonts.
var GlyphMapForStandardFonts = {
  '2': 10, '3': 32, '4': 33, '5': 34, '6': 35, '7': 36, '8': 37, '9': 38,
  '10': 39, '11': 40, '12': 41, '13': 42, '14': 43, '15': 44, '16': 45,
  '17': 46, '18': 47, '19': 48, '20': 49, '21': 50, '22': 51, '23': 52,
  '24': 53, '25': 54, '26': 55, '27': 56, '28': 57, '29': 58, '30': 894,
  '31': 60, '32': 61, '33': 62, '34': 63, '35': 64, '36': 65, '37': 66,
  '38': 67, '39': 68, '40': 69, '41': 70, '42': 71, '43': 72, '44': 73,
  '45': 74, '46': 75, '47': 76, '48': 77, '49': 78, '50': 79, '51': 80,
  '52': 81, '53': 82, '54': 83, '55': 84, '56': 85, '57': 86, '58': 87,
  '59': 88, '60': 89, '61': 90, '62': 91, '63': 92, '64': 93, '65': 94,
  '66': 95, '67': 96, '68': 97, '69': 98, '70': 99, '71': 100, '72': 101,
  '73': 102, '74': 103, '75': 104, '76': 105, '77': 106, '78': 107, '79': 108,
  '80': 109, '81': 110, '82': 111, '83': 112, '84': 113, '85': 114, '86': 115,
  '87': 116, '88': 117, '89': 118, '90': 119, '91': 120, '92': 121, '93': 122,
  '94': 123, '95': 124, '96': 125, '97': 126, '98': 196, '99': 197, '100': 199,
  '101': 201, '102': 209, '103': 214, '104': 220, '105': 225, '106': 224,
  '107': 226, '108': 228, '109': 227, '110': 229, '111': 231, '112': 233,
  '113': 232, '114': 234, '115': 235, '116': 237, '117': 236, '118': 238,
  '119': 239, '120': 241, '121': 243, '122': 242, '123': 244, '124': 246,
  '125': 245, '126': 250, '127': 249, '128': 251, '129': 252, '130': 8224,
  '131': 176, '132': 162, '133': 163, '134': 167, '135': 8226, '136': 182,
  '137': 223, '138': 174, '139': 169, '140': 8482, '141': 180, '142': 168,
  '143': 8800, '144': 198, '145': 216, '146': 8734, '147': 177, '148': 8804,
  '149': 8805, '150': 165, '151': 181, '152': 8706, '153': 8721, '154': 8719,
  '156': 8747, '157': 170, '158': 186, '159': 8486, '160': 230, '161': 248,
  '162': 191, '163': 161, '164': 172, '165': 8730, '166': 402, '167': 8776,
  '168': 8710, '169': 171, '170': 187, '171': 8230, '210': 218, '223': 711,
  '224': 321, '225': 322, '227': 353, '229': 382, '234': 253, '252': 263,
  '253': 268, '254': 269, '258': 258, '260': 260, '261': 261, '265': 280,
  '266': 281, '268': 283, '269': 313, '275': 323, '276': 324, '278': 328,
  '284': 345, '285': 346, '286': 347, '292': 367, '295': 377, '296': 378,
  '298': 380, '305': 963,
  '306': 964, '307': 966, '308': 8215, '309': 8252, '310': 8319, '311': 8359,
  '312': 8592, '313': 8593, '337': 9552, '493': 1039, '494': 1040, '705': 1524,
  '706': 8362, '710': 64288, '711': 64298, '759': 1617, '761': 1776,
  '763': 1778, '775': 1652, '777': 1764, '778': 1780, '779': 1781, '780': 1782,
  '782': 771, '783': 64726, '786': 8363, '788': 8532, '790': 768, '791': 769,
  '792': 768, '795': 803, '797': 64336, '798': 64337, '799': 64342,
  '800': 64343, '801': 64344, '802': 64345, '803': 64362, '804': 64363,
  '805': 64364, '2424': 7821, '2425': 7822, '2426': 7823, '2427': 7824,
  '2428': 7825, '2429': 7826, '2430': 7827, '2433': 7682, '2678': 8045,
  '2679': 8046, '2830': 1552, '2838': 686, '2840': 751, '2842': 753,
  '2843': 754, '2844': 755, '2846': 757, '2856': 767, '2857': 848, '2858': 849,
  '2862': 853, '2863': 854, '2864': 855, '2865': 861, '2866': 862, '2906': 7460,
  '2908': 7462, '2909': 7463, '2910': 7464, '2912': 7466, '2913': 7467,
  '2914': 7468, '2916': 7470, '2917': 7471, '2918': 7472, '2920': 7474,
  '2921': 7475, '2922': 7476, '2924': 7478, '2925': 7479, '2926': 7480,
  '2928': 7482, '2929': 7483, '2930': 7484, '2932': 7486, '2933': 7487,
  '2934': 7488, '2936': 7490, '2937': 7491, '2938': 7492, '2940': 7494,
  '2941': 7495, '2942': 7496, '2944': 7498, '2946': 7500, '2948': 7502,
  '2950': 7504, '2951': 7505, '2952': 7506, '2954': 7508, '2955': 7509,
  '2956': 7510, '2958': 7512, '2959': 7513, '2960': 7514, '2962': 7516,
  '2963': 7517, '2964': 7518, '2966': 7520, '2967': 7521, '2968': 7522,
  '2970': 7524, '2971': 7525, '2972': 7526, '2974': 7528, '2975': 7529,
  '2976': 7530, '2978': 1537, '2979': 1538, '2980': 1539, '2982': 1549,
  '2983': 1551, '2984': 1552, '2986': 1554, '2987': 1555, '2988': 1556,
  '2990': 1623, '2991': 1624, '2995': 1775, '2999': 1791, '3002': 64290,
  '3003': 64291, '3004': 64292, '3006': 64294, '3007': 64295, '3008': 64296,
  '3011': 1900, '3014': 8223, '3015': 8244, '3017': 7532, '3018': 7533,
  '3019': 7534, '3075': 7590, '3076': 7591, '3079': 7594, '3080': 7595,
  '3083': 7598, '3084': 7599, '3087': 7602, '3088': 7603, '3091': 7606,
  '3092': 7607, '3095': 7610, '3096': 7611, '3099': 7614, '3100': 7615,
  '3103': 7618, '3104': 7619, '3107': 8337, '3108': 8338, '3116': 1884,
  '3119': 1885, '3120': 1885, '3123': 1886, '3124': 1886, '3127': 1887,
  '3128': 1887, '3131': 1888, '3132': 1888, '3135': 1889, '3136': 1889,
  '3139': 1890, '3140': 1890, '3143': 1891, '3144': 1891, '3147': 1892,
  '3148': 1892, '3153': 580, '3154': 581, '3157': 584, '3158': 585, '3161': 588,
  '3162': 589, '3165': 891, '3166': 892, '3169': 1274, '3170': 1275,
  '3173': 1278, '3174': 1279, '3181': 7622, '3182': 7623, '3282': 11799,
  '3316': 578, '3379': 42785, '3393': 1159, '3416': 8377
};

// Some characters, e.g. copyrightserif, are mapped to the private use area and
// might not be displayed using standard fonts. Mapping/hacking well-known chars
// to the similar equivalents in the normal characters range.
var SpecialPUASymbols = {
  '63721': 0x00A9, // copyrightsans (0xF8E9) => copyright
  '63193': 0x00A9, // copyrightserif (0xF6D9) => copyright
  '63720': 0x00AE, // registersans (0xF8E8) => registered
  '63194': 0x00AE, // registerserif (0xF6DA) => registered
  '63722': 0x2122, // trademarksans (0xF8EA) => trademark
  '63195': 0x2122, // trademarkserif (0xF6DB) => trademark
  '63729': 0x23A7, // bracelefttp (0xF8F1)
  '63730': 0x23A8, // braceleftmid (0xF8F2)
  '63731': 0x23A9, // braceleftbt (0xF8F3)
  '63740': 0x23AB, // bracerighttp (0xF8FC)
  '63741': 0x23AC, // bracerightmid (0xF8FD)
  '63742': 0x23AD, // bracerightbt (0xF8FE)
  '63726': 0x23A1, // bracketlefttp (0xF8EE)
  '63727': 0x23A2, // bracketleftex (0xF8EF)
  '63728': 0x23A3, // bracketleftbt (0xF8F0)
  '63737': 0x23A4, // bracketrighttp (0xF8F9)
  '63738': 0x23A5, // bracketrightex (0xF8FA)
  '63739': 0x23A6, // bracketrightbt (0xF8FB)
  '63723': 0x239B, // parenlefttp (0xF8EB)
  '63724': 0x239C, // parenleftex (0xF8EC)
  '63725': 0x239D, // parenleftbt (0xF8ED)
  '63734': 0x239E, // parenrighttp (0xF8F6)
  '63735': 0x239F, // parenrightex (0xF8F7)
  '63736': 0x23A0, // parenrightbt (0xF8F8)
};
function mapSpecialUnicodeValues(code) {
  if (code >= 0xFFF0 && code <= 0xFFFF) { // Specials unicode block.
    return 0;
  } else if (code >= 0xF600 && code <= 0xF8FF) {
    return (SpecialPUASymbols[code] || code);
  }
  return code;
}

var UnicodeRanges = [
  { 'begin': 0x0000, 'end': 0x007F }, // Basic Latin
  { 'begin': 0x0080, 'end': 0x00FF }, // Latin-1 Supplement
  { 'begin': 0x0100, 'end': 0x017F }, // Latin Extended-A
  { 'begin': 0x0180, 'end': 0x024F }, // Latin Extended-B
  { 'begin': 0x0250, 'end': 0x02AF }, // IPA Extensions
  { 'begin': 0x02B0, 'end': 0x02FF }, // Spacing Modifier Letters
  { 'begin': 0x0300, 'end': 0x036F }, // Combining Diacritical Marks
  { 'begin': 0x0370, 'end': 0x03FF }, // Greek and Coptic
  { 'begin': 0x2C80, 'end': 0x2CFF }, // Coptic
  { 'begin': 0x0400, 'end': 0x04FF }, // Cyrillic
  { 'begin': 0x0530, 'end': 0x058F }, // Armenian
  { 'begin': 0x0590, 'end': 0x05FF }, // Hebrew
  { 'begin': 0xA500, 'end': 0xA63F }, // Vai
  { 'begin': 0x0600, 'end': 0x06FF }, // Arabic
  { 'begin': 0x07C0, 'end': 0x07FF }, // NKo
  { 'begin': 0x0900, 'end': 0x097F }, // Devanagari
  { 'begin': 0x0980, 'end': 0x09FF }, // Bengali
  { 'begin': 0x0A00, 'end': 0x0A7F }, // Gurmukhi
  { 'begin': 0x0A80, 'end': 0x0AFF }, // Gujarati
  { 'begin': 0x0B00, 'end': 0x0B7F }, // Oriya
  { 'begin': 0x0B80, 'end': 0x0BFF }, // Tamil
  { 'begin': 0x0C00, 'end': 0x0C7F }, // Telugu
  { 'begin': 0x0C80, 'end': 0x0CFF }, // Kannada
  { 'begin': 0x0D00, 'end': 0x0D7F }, // Malayalam
  { 'begin': 0x0E00, 'end': 0x0E7F }, // Thai
  { 'begin': 0x0E80, 'end': 0x0EFF }, // Lao
  { 'begin': 0x10A0, 'end': 0x10FF }, // Georgian
  { 'begin': 0x1B00, 'end': 0x1B7F }, // Balinese
  { 'begin': 0x1100, 'end': 0x11FF }, // Hangul Jamo
  { 'begin': 0x1E00, 'end': 0x1EFF }, // Latin Extended Additional
  { 'begin': 0x1F00, 'end': 0x1FFF }, // Greek Extended
  { 'begin': 0x2000, 'end': 0x206F }, // General Punctuation
  { 'begin': 0x2070, 'end': 0x209F }, // Superscripts And Subscripts
  { 'begin': 0x20A0, 'end': 0x20CF }, // Currency Symbol
  { 'begin': 0x20D0, 'end': 0x20FF }, // Combining Diacritical Marks For Symbols
  { 'begin': 0x2100, 'end': 0x214F }, // Letterlike Symbols
  { 'begin': 0x2150, 'end': 0x218F }, // Number Forms
  { 'begin': 0x2190, 'end': 0x21FF }, // Arrows
  { 'begin': 0x2200, 'end': 0x22FF }, // Mathematical Operators
  { 'begin': 0x2300, 'end': 0x23FF }, // Miscellaneous Technical
  { 'begin': 0x2400, 'end': 0x243F }, // Control Pictures
  { 'begin': 0x2440, 'end': 0x245F }, // Optical Character Recognition
  { 'begin': 0x2460, 'end': 0x24FF }, // Enclosed Alphanumerics
  { 'begin': 0x2500, 'end': 0x257F }, // Box Drawing
  { 'begin': 0x2580, 'end': 0x259F }, // Block Elements
  { 'begin': 0x25A0, 'end': 0x25FF }, // Geometric Shapes
  { 'begin': 0x2600, 'end': 0x26FF }, // Miscellaneous Symbols
  { 'begin': 0x2700, 'end': 0x27BF }, // Dingbats
  { 'begin': 0x3000, 'end': 0x303F }, // CJK Symbols And Punctuation
  { 'begin': 0x3040, 'end': 0x309F }, // Hiragana
  { 'begin': 0x30A0, 'end': 0x30FF }, // Katakana
  { 'begin': 0x3100, 'end': 0x312F }, // Bopomofo
  { 'begin': 0x3130, 'end': 0x318F }, // Hangul Compatibility Jamo
  { 'begin': 0xA840, 'end': 0xA87F }, // Phags-pa
  { 'begin': 0x3200, 'end': 0x32FF }, // Enclosed CJK Letters And Months
  { 'begin': 0x3300, 'end': 0x33FF }, // CJK Compatibility
  { 'begin': 0xAC00, 'end': 0xD7AF }, // Hangul Syllables
  { 'begin': 0xD800, 'end': 0xDFFF }, // Non-Plane 0 *
  { 'begin': 0x10900, 'end': 0x1091F }, // Phoenicia
  { 'begin': 0x4E00, 'end': 0x9FFF }, // CJK Unified Ideographs
  { 'begin': 0xE000, 'end': 0xF8FF }, // Private Use Area (plane 0)
  { 'begin': 0x31C0, 'end': 0x31EF }, // CJK Strokes
  { 'begin': 0xFB00, 'end': 0xFB4F }, // Alphabetic Presentation Forms
  { 'begin': 0xFB50, 'end': 0xFDFF }, // Arabic Presentation Forms-A
  { 'begin': 0xFE20, 'end': 0xFE2F }, // Combining Half Marks
  { 'begin': 0xFE10, 'end': 0xFE1F }, // Vertical Forms
  { 'begin': 0xFE50, 'end': 0xFE6F }, // Small Form Variants
  { 'begin': 0xFE70, 'end': 0xFEFF }, // Arabic Presentation Forms-B
  { 'begin': 0xFF00, 'end': 0xFFEF }, // Halfwidth And Fullwidth Forms
  { 'begin': 0xFFF0, 'end': 0xFFFF }, // Specials
  { 'begin': 0x0F00, 'end': 0x0FFF }, // Tibetan
  { 'begin': 0x0700, 'end': 0x074F }, // Syriac
  { 'begin': 0x0780, 'end': 0x07BF }, // Thaana
  { 'begin': 0x0D80, 'end': 0x0DFF }, // Sinhala
  { 'begin': 0x1000, 'end': 0x109F }, // Myanmar
  { 'begin': 0x1200, 'end': 0x137F }, // Ethiopic
  { 'begin': 0x13A0, 'end': 0x13FF }, // Cherokee
  { 'begin': 0x1400, 'end': 0x167F }, // Unified Canadian Aboriginal Syllabics
  { 'begin': 0x1680, 'end': 0x169F }, // Ogham
  { 'begin': 0x16A0, 'end': 0x16FF }, // Runic
  { 'begin': 0x1780, 'end': 0x17FF }, // Khmer
  { 'begin': 0x1800, 'end': 0x18AF }, // Mongolian
  { 'begin': 0x2800, 'end': 0x28FF }, // Braille Patterns
  { 'begin': 0xA000, 'end': 0xA48F }, // Yi Syllables
  { 'begin': 0x1700, 'end': 0x171F }, // Tagalog
  { 'begin': 0x10300, 'end': 0x1032F }, // Old Italic
  { 'begin': 0x10330, 'end': 0x1034F }, // Gothic
  { 'begin': 0x10400, 'end': 0x1044F }, // Deseret
  { 'begin': 0x1D000, 'end': 0x1D0FF }, // Byzantine Musical Symbols
  { 'begin': 0x1D400, 'end': 0x1D7FF }, // Mathematical Alphanumeric Symbols
  { 'begin': 0xFF000, 'end': 0xFFFFD }, // Private Use (plane 15)
  { 'begin': 0xFE00, 'end': 0xFE0F }, // Variation Selectors
  { 'begin': 0xE0000, 'end': 0xE007F }, // Tags
  { 'begin': 0x1900, 'end': 0x194F }, // Limbu
  { 'begin': 0x1950, 'end': 0x197F }, // Tai Le
  { 'begin': 0x1980, 'end': 0x19DF }, // New Tai Lue
  { 'begin': 0x1A00, 'end': 0x1A1F }, // Buginese
  { 'begin': 0x2C00, 'end': 0x2C5F }, // Glagolitic
  { 'begin': 0x2D30, 'end': 0x2D7F }, // Tifinagh
  { 'begin': 0x4DC0, 'end': 0x4DFF }, // Yijing Hexagram Symbols
  { 'begin': 0xA800, 'end': 0xA82F }, // Syloti Nagri
  { 'begin': 0x10000, 'end': 0x1007F }, // Linear B Syllabary
  { 'begin': 0x10140, 'end': 0x1018F }, // Ancient Greek Numbers
  { 'begin': 0x10380, 'end': 0x1039F }, // Ugaritic
  { 'begin': 0x103A0, 'end': 0x103DF }, // Old Persian
  { 'begin': 0x10450, 'end': 0x1047F }, // Shavian
  { 'begin': 0x10480, 'end': 0x104AF }, // Osmanya
  { 'begin': 0x10800, 'end': 0x1083F }, // Cypriot Syllabary
  { 'begin': 0x10A00, 'end': 0x10A5F }, // Kharoshthi
  { 'begin': 0x1D300, 'end': 0x1D35F }, // Tai Xuan Jing Symbols
  { 'begin': 0x12000, 'end': 0x123FF }, // Cuneiform
  { 'begin': 0x1D360, 'end': 0x1D37F }, // Counting Rod Numerals
  { 'begin': 0x1B80, 'end': 0x1BBF }, // Sundanese
  { 'begin': 0x1C00, 'end': 0x1C4F }, // Lepcha
  { 'begin': 0x1C50, 'end': 0x1C7F }, // Ol Chiki
  { 'begin': 0xA880, 'end': 0xA8DF }, // Saurashtra
  { 'begin': 0xA900, 'end': 0xA92F }, // Kayah Li
  { 'begin': 0xA930, 'end': 0xA95F }, // Rejang
  { 'begin': 0xAA00, 'end': 0xAA5F }, // Cham
  { 'begin': 0x10190, 'end': 0x101CF }, // Ancient Symbols
  { 'begin': 0x101D0, 'end': 0x101FF }, // Phaistos Disc
  { 'begin': 0x102A0, 'end': 0x102DF }, // Carian
  { 'begin': 0x1F030, 'end': 0x1F09F }  // Domino Tiles
];

var MacStandardGlyphOrdering = [
  '.notdef', '.null', 'nonmarkingreturn', 'space', 'exclam', 'quotedbl',
  'numbersign', 'dollar', 'percent', 'ampersand', 'quotesingle', 'parenleft',
  'parenright', 'asterisk', 'plus', 'comma', 'hyphen', 'period', 'slash',
  'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
  'nine', 'colon', 'semicolon', 'less', 'equal', 'greater', 'question', 'at',
  'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
  'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'bracketleft',
  'backslash', 'bracketright', 'asciicircum', 'underscore', 'grave', 'a', 'b',
  'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q',
  'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'braceleft', 'bar', 'braceright',
  'asciitilde', 'Adieresis', 'Aring', 'Ccedilla', 'Eacute', 'Ntilde',
  'Odieresis', 'Udieresis', 'aacute', 'agrave', 'acircumflex', 'adieresis',
  'atilde', 'aring', 'ccedilla', 'eacute', 'egrave', 'ecircumflex', 'edieresis',
  'iacute', 'igrave', 'icircumflex', 'idieresis', 'ntilde', 'oacute', 'ograve',
  'ocircumflex', 'odieresis', 'otilde', 'uacute', 'ugrave', 'ucircumflex',
  'udieresis', 'dagger', 'degree', 'cent', 'sterling', 'section', 'bullet',
  'paragraph', 'germandbls', 'registered', 'copyright', 'trademark', 'acute',
  'dieresis', 'notequal', 'AE', 'Oslash', 'infinity', 'plusminus', 'lessequal',
  'greaterequal', 'yen', 'mu', 'partialdiff', 'summation', 'product', 'pi',
  'integral', 'ordfeminine', 'ordmasculine', 'Omega', 'ae', 'oslash',
  'questiondown', 'exclamdown', 'logicalnot', 'radical', 'florin',
  'approxequal', 'Delta', 'guillemotleft', 'guillemotright', 'ellipsis',
  'nonbreakingspace', 'Agrave', 'Atilde', 'Otilde', 'OE', 'oe', 'endash',
  'emdash', 'quotedblleft', 'quotedblright', 'quoteleft', 'quoteright',
  'divide', 'lozenge', 'ydieresis', 'Ydieresis', 'fraction', 'currency',
  'guilsinglleft', 'guilsinglright', 'fi', 'fl', 'daggerdbl', 'periodcentered',
  'quotesinglbase', 'quotedblbase', 'perthousand', 'Acircumflex',
  'Ecircumflex', 'Aacute', 'Edieresis', 'Egrave', 'Iacute', 'Icircumflex',
  'Idieresis', 'Igrave', 'Oacute', 'Ocircumflex', 'apple', 'Ograve', 'Uacute',
  'Ucircumflex', 'Ugrave', 'dotlessi', 'circumflex', 'tilde', 'macron',
  'breve', 'dotaccent', 'ring', 'cedilla', 'hungarumlaut', 'ogonek', 'caron',
  'Lslash', 'lslash', 'Scaron', 'scaron', 'Zcaron', 'zcaron', 'brokenbar',
  'Eth', 'eth', 'Yacute', 'yacute', 'Thorn', 'thorn', 'minus', 'multiply',
  'onesuperior', 'twosuperior', 'threesuperior', 'onehalf', 'onequarter',
  'threequarters', 'franc', 'Gbreve', 'gbreve', 'Idotaccent', 'Scedilla',
  'scedilla', 'Cacute', 'cacute', 'Ccaron', 'ccaron', 'dcroat'];

function getUnicodeRangeFor(value) {
  for (var i = 0, ii = UnicodeRanges.length; i < ii; i++) {
    var range = UnicodeRanges[i];
    if (value >= range.begin && value < range.end) {
      return i;
    }
  }
  return -1;
}

function isRTLRangeFor(value) {
  var range = UnicodeRanges[13];
  if (value >= range.begin && value < range.end) {
    return true;
  }
  range = UnicodeRanges[11];
  if (value >= range.begin && value < range.end) {
    return true;
  }
  return false;
}

// The normalization table is obtained by filtering the Unicode characters
// database with <compat> entries.
var NormalizedUnicodes = {
  '\u00A8': '\u0020\u0308',
  '\u00AF': '\u0020\u0304',
  '\u00B4': '\u0020\u0301',
  '\u00B5': '\u03BC',
  '\u00B8': '\u0020\u0327',
  '\u0132': '\u0049\u004A',
  '\u0133': '\u0069\u006A',
  '\u013F': '\u004C\u00B7',
  '\u0140': '\u006C\u00B7',
  '\u0149': '\u02BC\u006E',
  '\u017F': '\u0073',
  '\u01C4': '\u0044\u017D',
  '\u01C5': '\u0044\u017E',
  '\u01C6': '\u0064\u017E',
  '\u01C7': '\u004C\u004A',
  '\u01C8': '\u004C\u006A',
  '\u01C9': '\u006C\u006A',
  '\u01CA': '\u004E\u004A',
  '\u01CB': '\u004E\u006A',
  '\u01CC': '\u006E\u006A',
  '\u01F1': '\u0044\u005A',
  '\u01F2': '\u0044\u007A',
  '\u01F3': '\u0064\u007A',
  '\u02D8': '\u0020\u0306',
  '\u02D9': '\u0020\u0307',
  '\u02DA': '\u0020\u030A',
  '\u02DB': '\u0020\u0328',
  '\u02DC': '\u0020\u0303',
  '\u02DD': '\u0020\u030B',
  '\u037A': '\u0020\u0345',
  '\u0384': '\u0020\u0301',
  '\u03D0': '\u03B2',
  '\u03D1': '\u03B8',
  '\u03D2': '\u03A5',
  '\u03D5': '\u03C6',
  '\u03D6': '\u03C0',
  '\u03F0': '\u03BA',
  '\u03F1': '\u03C1',
  '\u03F2': '\u03C2',
  '\u03F4': '\u0398',
  '\u03F5': '\u03B5',
  '\u03F9': '\u03A3',
  '\u0587': '\u0565\u0582',
  '\u0675': '\u0627\u0674',
  '\u0676': '\u0648\u0674',
  '\u0677': '\u06C7\u0674',
  '\u0678': '\u064A\u0674',
  '\u0E33': '\u0E4D\u0E32',
  '\u0EB3': '\u0ECD\u0EB2',
  '\u0EDC': '\u0EAB\u0E99',
  '\u0EDD': '\u0EAB\u0EA1',
  '\u0F77': '\u0FB2\u0F81',
  '\u0F79': '\u0FB3\u0F81',
  '\u1E9A': '\u0061\u02BE',
  '\u1FBD': '\u0020\u0313',
  '\u1FBF': '\u0020\u0313',
  '\u1FC0': '\u0020\u0342',
  '\u1FFE': '\u0020\u0314',
  '\u2002': '\u0020',
  '\u2003': '\u0020',
  '\u2004': '\u0020',
  '\u2005': '\u0020',
  '\u2006': '\u0020',
  '\u2008': '\u0020',
  '\u2009': '\u0020',
  '\u200A': '\u0020',
  '\u2017': '\u0020\u0333',
  '\u2024': '\u002E',
  '\u2025': '\u002E\u002E',
  '\u2026': '\u002E\u002E\u002E',
  '\u2033': '\u2032\u2032',
  '\u2034': '\u2032\u2032\u2032',
  '\u2036': '\u2035\u2035',
  '\u2037': '\u2035\u2035\u2035',
  '\u203C': '\u0021\u0021',
  '\u203E': '\u0020\u0305',
  '\u2047': '\u003F\u003F',
  '\u2048': '\u003F\u0021',
  '\u2049': '\u0021\u003F',
  '\u2057': '\u2032\u2032\u2032\u2032',
  '\u205F': '\u0020',
  '\u20A8': '\u0052\u0073',
  '\u2100': '\u0061\u002F\u0063',
  '\u2101': '\u0061\u002F\u0073',
  '\u2103': '\u00B0\u0043',
  '\u2105': '\u0063\u002F\u006F',
  '\u2106': '\u0063\u002F\u0075',
  '\u2107': '\u0190',
  '\u2109': '\u00B0\u0046',
  '\u2116': '\u004E\u006F',
  '\u2121': '\u0054\u0045\u004C',
  '\u2135': '\u05D0',
  '\u2136': '\u05D1',
  '\u2137': '\u05D2',
  '\u2138': '\u05D3',
  '\u213B': '\u0046\u0041\u0058',
  '\u2160': '\u0049',
  '\u2161': '\u0049\u0049',
  '\u2162': '\u0049\u0049\u0049',
  '\u2163': '\u0049\u0056',
  '\u2164': '\u0056',
  '\u2165': '\u0056\u0049',
  '\u2166': '\u0056\u0049\u0049',
  '\u2167': '\u0056\u0049\u0049\u0049',
  '\u2168': '\u0049\u0058',
  '\u2169': '\u0058',
  '\u216A': '\u0058\u0049',
  '\u216B': '\u0058\u0049\u0049',
  '\u216C': '\u004C',
  '\u216D': '\u0043',
  '\u216E': '\u0044',
  '\u216F': '\u004D',
  '\u2170': '\u0069',
  '\u2171': '\u0069\u0069',
  '\u2172': '\u0069\u0069\u0069',
  '\u2173': '\u0069\u0076',
  '\u2174': '\u0076',
  '\u2175': '\u0076\u0069',
  '\u2176': '\u0076\u0069\u0069',
  '\u2177': '\u0076\u0069\u0069\u0069',
  '\u2178': '\u0069\u0078',
  '\u2179': '\u0078',
  '\u217A': '\u0078\u0069',
  '\u217B': '\u0078\u0069\u0069',
  '\u217C': '\u006C',
  '\u217D': '\u0063',
  '\u217E': '\u0064',
  '\u217F': '\u006D',
  '\u222C': '\u222B\u222B',
  '\u222D': '\u222B\u222B\u222B',
  '\u222F': '\u222E\u222E',
  '\u2230': '\u222E\u222E\u222E',
  '\u2474': '\u0028\u0031\u0029',
  '\u2475': '\u0028\u0032\u0029',
  '\u2476': '\u0028\u0033\u0029',
  '\u2477': '\u0028\u0034\u0029',
  '\u2478': '\u0028\u0035\u0029',
  '\u2479': '\u0028\u0036\u0029',
  '\u247A': '\u0028\u0037\u0029',
  '\u247B': '\u0028\u0038\u0029',
  '\u247C': '\u0028\u0039\u0029',
  '\u247D': '\u0028\u0031\u0030\u0029',
  '\u247E': '\u0028\u0031\u0031\u0029',
  '\u247F': '\u0028\u0031\u0032\u0029',
  '\u2480': '\u0028\u0031\u0033\u0029',
  '\u2481': '\u0028\u0031\u0034\u0029',
  '\u2482': '\u0028\u0031\u0035\u0029',
  '\u2483': '\u0028\u0031\u0036\u0029',
  '\u2484': '\u0028\u0031\u0037\u0029',
  '\u2485': '\u0028\u0031\u0038\u0029',
  '\u2486': '\u0028\u0031\u0039\u0029',
  '\u2487': '\u0028\u0032\u0030\u0029',
  '\u2488': '\u0031\u002E',
  '\u2489': '\u0032\u002E',
  '\u248A': '\u0033\u002E',
  '\u248B': '\u0034\u002E',
  '\u248C': '\u0035\u002E',
  '\u248D': '\u0036\u002E',
  '\u248E': '\u0037\u002E',
  '\u248F': '\u0038\u002E',
  '\u2490': '\u0039\u002E',
  '\u2491': '\u0031\u0030\u002E',
  '\u2492': '\u0031\u0031\u002E',
  '\u2493': '\u0031\u0032\u002E',
  '\u2494': '\u0031\u0033\u002E',
  '\u2495': '\u0031\u0034\u002E',
  '\u2496': '\u0031\u0035\u002E',
  '\u2497': '\u0031\u0036\u002E',
  '\u2498': '\u0031\u0037\u002E',
  '\u2499': '\u0031\u0038\u002E',
  '\u249A': '\u0031\u0039\u002E',
  '\u249B': '\u0032\u0030\u002E',
  '\u249C': '\u0028\u0061\u0029',
  '\u249D': '\u0028\u0062\u0029',
  '\u249E': '\u0028\u0063\u0029',
  '\u249F': '\u0028\u0064\u0029',
  '\u24A0': '\u0028\u0065\u0029',
  '\u24A1': '\u0028\u0066\u0029',
  '\u24A2': '\u0028\u0067\u0029',
  '\u24A3': '\u0028\u0068\u0029',
  '\u24A4': '\u0028\u0069\u0029',
  '\u24A5': '\u0028\u006A\u0029',
  '\u24A6': '\u0028\u006B\u0029',
  '\u24A7': '\u0028\u006C\u0029',
  '\u24A8': '\u0028\u006D\u0029',
  '\u24A9': '\u0028\u006E\u0029',
  '\u24AA': '\u0028\u006F\u0029',
  '\u24AB': '\u0028\u0070\u0029',
  '\u24AC': '\u0028\u0071\u0029',
  '\u24AD': '\u0028\u0072\u0029',
  '\u24AE': '\u0028\u0073\u0029',
  '\u24AF': '\u0028\u0074\u0029',
  '\u24B0': '\u0028\u0075\u0029',
  '\u24B1': '\u0028\u0076\u0029',
  '\u24B2': '\u0028\u0077\u0029',
  '\u24B3': '\u0028\u0078\u0029',
  '\u24B4': '\u0028\u0079\u0029',
  '\u24B5': '\u0028\u007A\u0029',
  '\u2A0C': '\u222B\u222B\u222B\u222B',
  '\u2A74': '\u003A\u003A\u003D',
  '\u2A75': '\u003D\u003D',
  '\u2A76': '\u003D\u003D\u003D',
  '\u2E9F': '\u6BCD',
  '\u2EF3': '\u9F9F',
  '\u2F00': '\u4E00',
  '\u2F01': '\u4E28',
  '\u2F02': '\u4E36',
  '\u2F03': '\u4E3F',
  '\u2F04': '\u4E59',
  '\u2F05': '\u4E85',
  '\u2F06': '\u4E8C',
  '\u2F07': '\u4EA0',
  '\u2F08': '\u4EBA',
  '\u2F09': '\u513F',
  '\u2F0A': '\u5165',
  '\u2F0B': '\u516B',
  '\u2F0C': '\u5182',
  '\u2F0D': '\u5196',
  '\u2F0E': '\u51AB',
  '\u2F0F': '\u51E0',
  '\u2F10': '\u51F5',
  '\u2F11': '\u5200',
  '\u2F12': '\u529B',
  '\u2F13': '\u52F9',
  '\u2F14': '\u5315',
  '\u2F15': '\u531A',
  '\u2F16': '\u5338',
  '\u2F17': '\u5341',
  '\u2F18': '\u535C',
  '\u2F19': '\u5369',
  '\u2F1A': '\u5382',
  '\u2F1B': '\u53B6',
  '\u2F1C': '\u53C8',
  '\u2F1D': '\u53E3',
  '\u2F1E': '\u56D7',
  '\u2F1F': '\u571F',
  '\u2F20': '\u58EB',
  '\u2F21': '\u5902',
  '\u2F22': '\u590A',
  '\u2F23': '\u5915',
  '\u2F24': '\u5927',
  '\u2F25': '\u5973',
  '\u2F26': '\u5B50',
  '\u2F27': '\u5B80',
  '\u2F28': '\u5BF8',
  '\u2F29': '\u5C0F',
  '\u2F2A': '\u5C22',
  '\u2F2B': '\u5C38',
  '\u2F2C': '\u5C6E',
  '\u2F2D': '\u5C71',
  '\u2F2E': '\u5DDB',
  '\u2F2F': '\u5DE5',
  '\u2F30': '\u5DF1',
  '\u2F31': '\u5DFE',
  '\u2F32': '\u5E72',
  '\u2F33': '\u5E7A',
  '\u2F34': '\u5E7F',
  '\u2F35': '\u5EF4',
  '\u2F36': '\u5EFE',
  '\u2F37': '\u5F0B',
  '\u2F38': '\u5F13',
  '\u2F39': '\u5F50',
  '\u2F3A': '\u5F61',
  '\u2F3B': '\u5F73',
  '\u2F3C': '\u5FC3',
  '\u2F3D': '\u6208',
  '\u2F3E': '\u6236',
  '\u2F3F': '\u624B',
  '\u2F40': '\u652F',
  '\u2F41': '\u6534',
  '\u2F42': '\u6587',
  '\u2F43': '\u6597',
  '\u2F44': '\u65A4',
  '\u2F45': '\u65B9',
  '\u2F46': '\u65E0',
  '\u2F47': '\u65E5',
  '\u2F48': '\u66F0',
  '\u2F49': '\u6708',
  '\u2F4A': '\u6728',
  '\u2F4B': '\u6B20',
  '\u2F4C': '\u6B62',
  '\u2F4D': '\u6B79',
  '\u2F4E': '\u6BB3',
  '\u2F4F': '\u6BCB',
  '\u2F50': '\u6BD4',
  '\u2F51': '\u6BDB',
  '\u2F52': '\u6C0F',
  '\u2F53': '\u6C14',
  '\u2F54': '\u6C34',
  '\u2F55': '\u706B',
  '\u2F56': '\u722A',
  '\u2F57': '\u7236',
  '\u2F58': '\u723B',
  '\u2F59': '\u723F',
  '\u2F5A': '\u7247',
  '\u2F5B': '\u7259',
  '\u2F5C': '\u725B',
  '\u2F5D': '\u72AC',
  '\u2F5E': '\u7384',
  '\u2F5F': '\u7389',
  '\u2F60': '\u74DC',
  '\u2F61': '\u74E6',
  '\u2F62': '\u7518',
  '\u2F63': '\u751F',
  '\u2F64': '\u7528',
  '\u2F65': '\u7530',
  '\u2F66': '\u758B',
  '\u2F67': '\u7592',
  '\u2F68': '\u7676',
  '\u2F69': '\u767D',
  '\u2F6A': '\u76AE',
  '\u2F6B': '\u76BF',
  '\u2F6C': '\u76EE',
  '\u2F6D': '\u77DB',
  '\u2F6E': '\u77E2',
  '\u2F6F': '\u77F3',
  '\u2F70': '\u793A',
  '\u2F71': '\u79B8',
  '\u2F72': '\u79BE',
  '\u2F73': '\u7A74',
  '\u2F74': '\u7ACB',
  '\u2F75': '\u7AF9',
  '\u2F76': '\u7C73',
  '\u2F77': '\u7CF8',
  '\u2F78': '\u7F36',
  '\u2F79': '\u7F51',
  '\u2F7A': '\u7F8A',
  '\u2F7B': '\u7FBD',
  '\u2F7C': '\u8001',
  '\u2F7D': '\u800C',
  '\u2F7E': '\u8012',
  '\u2F7F': '\u8033',
  '\u2F80': '\u807F',
  '\u2F81': '\u8089',
  '\u2F82': '\u81E3',
  '\u2F83': '\u81EA',
  '\u2F84': '\u81F3',
  '\u2F85': '\u81FC',
  '\u2F86': '\u820C',
  '\u2F87': '\u821B',
  '\u2F88': '\u821F',
  '\u2F89': '\u826E',
  '\u2F8A': '\u8272',
  '\u2F8B': '\u8278',
  '\u2F8C': '\u864D',
  '\u2F8D': '\u866B',
  '\u2F8E': '\u8840',
  '\u2F8F': '\u884C',
  '\u2F90': '\u8863',
  '\u2F91': '\u897E',
  '\u2F92': '\u898B',
  '\u2F93': '\u89D2',
  '\u2F94': '\u8A00',
  '\u2F95': '\u8C37',
  '\u2F96': '\u8C46',
  '\u2F97': '\u8C55',
  '\u2F98': '\u8C78',
  '\u2F99': '\u8C9D',
  '\u2F9A': '\u8D64',
  '\u2F9B': '\u8D70',
  '\u2F9C': '\u8DB3',
  '\u2F9D': '\u8EAB',
  '\u2F9E': '\u8ECA',
  '\u2F9F': '\u8F9B',
  '\u2FA0': '\u8FB0',
  '\u2FA1': '\u8FB5',
  '\u2FA2': '\u9091',
  '\u2FA3': '\u9149',
  '\u2FA4': '\u91C6',
  '\u2FA5': '\u91CC',
  '\u2FA6': '\u91D1',
  '\u2FA7': '\u9577',
  '\u2FA8': '\u9580',
  '\u2FA9': '\u961C',
  '\u2FAA': '\u96B6',
  '\u2FAB': '\u96B9',
  '\u2FAC': '\u96E8',
  '\u2FAD': '\u9751',
  '\u2FAE': '\u975E',
  '\u2FAF': '\u9762',
  '\u2FB0': '\u9769',
  '\u2FB1': '\u97CB',
  '\u2FB2': '\u97ED',
  '\u2FB3': '\u97F3',
  '\u2FB4': '\u9801',
  '\u2FB5': '\u98A8',
  '\u2FB6': '\u98DB',
  '\u2FB7': '\u98DF',
  '\u2FB8': '\u9996',
  '\u2FB9': '\u9999',
  '\u2FBA': '\u99AC',
  '\u2FBB': '\u9AA8',
  '\u2FBC': '\u9AD8',
  '\u2FBD': '\u9ADF',
  '\u2FBE': '\u9B25',
  '\u2FBF': '\u9B2F',
  '\u2FC0': '\u9B32',
  '\u2FC1': '\u9B3C',
  '\u2FC2': '\u9B5A',
  '\u2FC3': '\u9CE5',
  '\u2FC4': '\u9E75',
  '\u2FC5': '\u9E7F',
  '\u2FC6': '\u9EA5',
  '\u2FC7': '\u9EBB',
  '\u2FC8': '\u9EC3',
  '\u2FC9': '\u9ECD',
  '\u2FCA': '\u9ED1',
  '\u2FCB': '\u9EF9',
  '\u2FCC': '\u9EFD',
  '\u2FCD': '\u9F0E',
  '\u2FCE': '\u9F13',
  '\u2FCF': '\u9F20',
  '\u2FD0': '\u9F3B',
  '\u2FD1': '\u9F4A',
  '\u2FD2': '\u9F52',
  '\u2FD3': '\u9F8D',
  '\u2FD4': '\u9F9C',
  '\u2FD5': '\u9FA0',
  '\u3036': '\u3012',
  '\u3038': '\u5341',
  '\u3039': '\u5344',
  '\u303A': '\u5345',
  '\u309B': '\u0020\u3099',
  '\u309C': '\u0020\u309A',
  '\u3131': '\u1100',
  '\u3132': '\u1101',
  '\u3133': '\u11AA',
  '\u3134': '\u1102',
  '\u3135': '\u11AC',
  '\u3136': '\u11AD',
  '\u3137': '\u1103',
  '\u3138': '\u1104',
  '\u3139': '\u1105',
  '\u313A': '\u11B0',
  '\u313B': '\u11B1',
  '\u313C': '\u11B2',
  '\u313D': '\u11B3',
  '\u313E': '\u11B4',
  '\u313F': '\u11B5',
  '\u3140': '\u111A',
  '\u3141': '\u1106',
  '\u3142': '\u1107',
  '\u3143': '\u1108',
  '\u3144': '\u1121',
  '\u3145': '\u1109',
  '\u3146': '\u110A',
  '\u3147': '\u110B',
  '\u3148': '\u110C',
  '\u3149': '\u110D',
  '\u314A': '\u110E',
  '\u314B': '\u110F',
  '\u314C': '\u1110',
  '\u314D': '\u1111',
  '\u314E': '\u1112',
  '\u314F': '\u1161',
  '\u3150': '\u1162',
  '\u3151': '\u1163',
  '\u3152': '\u1164',
  '\u3153': '\u1165',
  '\u3154': '\u1166',
  '\u3155': '\u1167',
  '\u3156': '\u1168',
  '\u3157': '\u1169',
  '\u3158': '\u116A',
  '\u3159': '\u116B',
  '\u315A': '\u116C',
  '\u315B': '\u116D',
  '\u315C': '\u116E',
  '\u315D': '\u116F',
  '\u315E': '\u1170',
  '\u315F': '\u1171',
  '\u3160': '\u1172',
  '\u3161': '\u1173',
  '\u3162': '\u1174',
  '\u3163': '\u1175',
  '\u3164': '\u1160',
  '\u3165': '\u1114',
  '\u3166': '\u1115',
  '\u3167': '\u11C7',
  '\u3168': '\u11C8',
  '\u3169': '\u11CC',
  '\u316A': '\u11CE',
  '\u316B': '\u11D3',
  '\u316C': '\u11D7',
  '\u316D': '\u11D9',
  '\u316E': '\u111C',
  '\u316F': '\u11DD',
  '\u3170': '\u11DF',
  '\u3171': '\u111D',
  '\u3172': '\u111E',
  '\u3173': '\u1120',
  '\u3174': '\u1122',
  '\u3175': '\u1123',
  '\u3176': '\u1127',
  '\u3177': '\u1129',
  '\u3178': '\u112B',
  '\u3179': '\u112C',
  '\u317A': '\u112D',
  '\u317B': '\u112E',
  '\u317C': '\u112F',
  '\u317D': '\u1132',
  '\u317E': '\u1136',
  '\u317F': '\u1140',
  '\u3180': '\u1147',
  '\u3181': '\u114C',
  '\u3182': '\u11F1',
  '\u3183': '\u11F2',
  '\u3184': '\u1157',
  '\u3185': '\u1158',
  '\u3186': '\u1159',
  '\u3187': '\u1184',
  '\u3188': '\u1185',
  '\u3189': '\u1188',
  '\u318A': '\u1191',
  '\u318B': '\u1192',
  '\u318C': '\u1194',
  '\u318D': '\u119E',
  '\u318E': '\u11A1',
  '\u3200': '\u0028\u1100\u0029',
  '\u3201': '\u0028\u1102\u0029',
  '\u3202': '\u0028\u1103\u0029',
  '\u3203': '\u0028\u1105\u0029',
  '\u3204': '\u0028\u1106\u0029',
  '\u3205': '\u0028\u1107\u0029',
  '\u3206': '\u0028\u1109\u0029',
  '\u3207': '\u0028\u110B\u0029',
  '\u3208': '\u0028\u110C\u0029',
  '\u3209': '\u0028\u110E\u0029',
  '\u320A': '\u0028\u110F\u0029',
  '\u320B': '\u0028\u1110\u0029',
  '\u320C': '\u0028\u1111\u0029',
  '\u320D': '\u0028\u1112\u0029',
  '\u320E': '\u0028\u1100\u1161\u0029',
  '\u320F': '\u0028\u1102\u1161\u0029',
  '\u3210': '\u0028\u1103\u1161\u0029',
  '\u3211': '\u0028\u1105\u1161\u0029',
  '\u3212': '\u0028\u1106\u1161\u0029',
  '\u3213': '\u0028\u1107\u1161\u0029',
  '\u3214': '\u0028\u1109\u1161\u0029',
  '\u3215': '\u0028\u110B\u1161\u0029',
  '\u3216': '\u0028\u110C\u1161\u0029',
  '\u3217': '\u0028\u110E\u1161\u0029',
  '\u3218': '\u0028\u110F\u1161\u0029',
  '\u3219': '\u0028\u1110\u1161\u0029',
  '\u321A': '\u0028\u1111\u1161\u0029',
  '\u321B': '\u0028\u1112\u1161\u0029',
  '\u321C': '\u0028\u110C\u116E\u0029',
  '\u321D': '\u0028\u110B\u1169\u110C\u1165\u11AB\u0029',
  '\u321E': '\u0028\u110B\u1169\u1112\u116E\u0029',
  '\u3220': '\u0028\u4E00\u0029',
  '\u3221': '\u0028\u4E8C\u0029',
  '\u3222': '\u0028\u4E09\u0029',
  '\u3223': '\u0028\u56DB\u0029',
  '\u3224': '\u0028\u4E94\u0029',
  '\u3225': '\u0028\u516D\u0029',
  '\u3226': '\u0028\u4E03\u0029',
  '\u3227': '\u0028\u516B\u0029',
  '\u3228': '\u0028\u4E5D\u0029',
  '\u3229': '\u0028\u5341\u0029',
  '\u322A': '\u0028\u6708\u0029',
  '\u322B': '\u0028\u706B\u0029',
  '\u322C': '\u0028\u6C34\u0029',
  '\u322D': '\u0028\u6728\u0029',
  '\u322E': '\u0028\u91D1\u0029',
  '\u322F': '\u0028\u571F\u0029',
  '\u3230': '\u0028\u65E5\u0029',
  '\u3231': '\u0028\u682A\u0029',
  '\u3232': '\u0028\u6709\u0029',
  '\u3233': '\u0028\u793E\u0029',
  '\u3234': '\u0028\u540D\u0029',
  '\u3235': '\u0028\u7279\u0029',
  '\u3236': '\u0028\u8CA1\u0029',
  '\u3237': '\u0028\u795D\u0029',
  '\u3238': '\u0028\u52B4\u0029',
  '\u3239': '\u0028\u4EE3\u0029',
  '\u323A': '\u0028\u547C\u0029',
  '\u323B': '\u0028\u5B66\u0029',
  '\u323C': '\u0028\u76E3\u0029',
  '\u323D': '\u0028\u4F01\u0029',
  '\u323E': '\u0028\u8CC7\u0029',
  '\u323F': '\u0028\u5354\u0029',
  '\u3240': '\u0028\u796D\u0029',
  '\u3241': '\u0028\u4F11\u0029',
  '\u3242': '\u0028\u81EA\u0029',
  '\u3243': '\u0028\u81F3\u0029',
  '\u32C0': '\u0031\u6708',
  '\u32C1': '\u0032\u6708',
  '\u32C2': '\u0033\u6708',
  '\u32C3': '\u0034\u6708',
  '\u32C4': '\u0035\u6708',
  '\u32C5': '\u0036\u6708',
  '\u32C6': '\u0037\u6708',
  '\u32C7': '\u0038\u6708',
  '\u32C8': '\u0039\u6708',
  '\u32C9': '\u0031\u0030\u6708',
  '\u32CA': '\u0031\u0031\u6708',
  '\u32CB': '\u0031\u0032\u6708',
  '\u3358': '\u0030\u70B9',
  '\u3359': '\u0031\u70B9',
  '\u335A': '\u0032\u70B9',
  '\u335B': '\u0033\u70B9',
  '\u335C': '\u0034\u70B9',
  '\u335D': '\u0035\u70B9',
  '\u335E': '\u0036\u70B9',
  '\u335F': '\u0037\u70B9',
  '\u3360': '\u0038\u70B9',
  '\u3361': '\u0039\u70B9',
  '\u3362': '\u0031\u0030\u70B9',
  '\u3363': '\u0031\u0031\u70B9',
  '\u3364': '\u0031\u0032\u70B9',
  '\u3365': '\u0031\u0033\u70B9',
  '\u3366': '\u0031\u0034\u70B9',
  '\u3367': '\u0031\u0035\u70B9',
  '\u3368': '\u0031\u0036\u70B9',
  '\u3369': '\u0031\u0037\u70B9',
  '\u336A': '\u0031\u0038\u70B9',
  '\u336B': '\u0031\u0039\u70B9',
  '\u336C': '\u0032\u0030\u70B9',
  '\u336D': '\u0032\u0031\u70B9',
  '\u336E': '\u0032\u0032\u70B9',
  '\u336F': '\u0032\u0033\u70B9',
  '\u3370': '\u0032\u0034\u70B9',
  '\u33E0': '\u0031\u65E5',
  '\u33E1': '\u0032\u65E5',
  '\u33E2': '\u0033\u65E5',
  '\u33E3': '\u0034\u65E5',
  '\u33E4': '\u0035\u65E5',
  '\u33E5': '\u0036\u65E5',
  '\u33E6': '\u0037\u65E5',
  '\u33E7': '\u0038\u65E5',
  '\u33E8': '\u0039\u65E5',
  '\u33E9': '\u0031\u0030\u65E5',
  '\u33EA': '\u0031\u0031\u65E5',
  '\u33EB': '\u0031\u0032\u65E5',
  '\u33EC': '\u0031\u0033\u65E5',
  '\u33ED': '\u0031\u0034\u65E5',
  '\u33EE': '\u0031\u0035\u65E5',
  '\u33EF': '\u0031\u0036\u65E5',
  '\u33F0': '\u0031\u0037\u65E5',
  '\u33F1': '\u0031\u0038\u65E5',
  '\u33F2': '\u0031\u0039\u65E5',
  '\u33F3': '\u0032\u0030\u65E5',
  '\u33F4': '\u0032\u0031\u65E5',
  '\u33F5': '\u0032\u0032\u65E5',
  '\u33F6': '\u0032\u0033\u65E5',
  '\u33F7': '\u0032\u0034\u65E5',
  '\u33F8': '\u0032\u0035\u65E5',
  '\u33F9': '\u0032\u0036\u65E5',
  '\u33FA': '\u0032\u0037\u65E5',
  '\u33FB': '\u0032\u0038\u65E5',
  '\u33FC': '\u0032\u0039\u65E5',
  '\u33FD': '\u0033\u0030\u65E5',
  '\u33FE': '\u0033\u0031\u65E5',
  '\uFB00': '\u0066\u0066',
  '\uFB01': '\u0066\u0069',
  '\uFB02': '\u0066\u006C',
  '\uFB03': '\u0066\u0066\u0069',
  '\uFB04': '\u0066\u0066\u006C',
  '\uFB05': '\u017F\u0074',
  '\uFB06': '\u0073\u0074',
  '\uFB13': '\u0574\u0576',
  '\uFB14': '\u0574\u0565',
  '\uFB15': '\u0574\u056B',
  '\uFB16': '\u057E\u0576',
  '\uFB17': '\u0574\u056D',
  '\uFB4F': '\u05D0\u05DC',
  '\uFB50': '\u0671',
  '\uFB51': '\u0671',
  '\uFB52': '\u067B',
  '\uFB53': '\u067B',
  '\uFB54': '\u067B',
  '\uFB55': '\u067B',
  '\uFB56': '\u067E',
  '\uFB57': '\u067E',
  '\uFB58': '\u067E',
  '\uFB59': '\u067E',
  '\uFB5A': '\u0680',
  '\uFB5B': '\u0680',
  '\uFB5C': '\u0680',
  '\uFB5D': '\u0680',
  '\uFB5E': '\u067A',
  '\uFB5F': '\u067A',
  '\uFB60': '\u067A',
  '\uFB61': '\u067A',
  '\uFB62': '\u067F',
  '\uFB63': '\u067F',
  '\uFB64': '\u067F',
  '\uFB65': '\u067F',
  '\uFB66': '\u0679',
  '\uFB67': '\u0679',
  '\uFB68': '\u0679',
  '\uFB69': '\u0679',
  '\uFB6A': '\u06A4',
  '\uFB6B': '\u06A4',
  '\uFB6C': '\u06A4',
  '\uFB6D': '\u06A4',
  '\uFB6E': '\u06A6',
  '\uFB6F': '\u06A6',
  '\uFB70': '\u06A6',
  '\uFB71': '\u06A6',
  '\uFB72': '\u0684',
  '\uFB73': '\u0684',
  '\uFB74': '\u0684',
  '\uFB75': '\u0684',
  '\uFB76': '\u0683',
  '\uFB77': '\u0683',
  '\uFB78': '\u0683',
  '\uFB79': '\u0683',
  '\uFB7A': '\u0686',
  '\uFB7B': '\u0686',
  '\uFB7C': '\u0686',
  '\uFB7D': '\u0686',
  '\uFB7E': '\u0687',
  '\uFB7F': '\u0687',
  '\uFB80': '\u0687',
  '\uFB81': '\u0687',
  '\uFB82': '\u068D',
  '\uFB83': '\u068D',
  '\uFB84': '\u068C',
  '\uFB85': '\u068C',
  '\uFB86': '\u068E',
  '\uFB87': '\u068E',
  '\uFB88': '\u0688',
  '\uFB89': '\u0688',
  '\uFB8A': '\u0698',
  '\uFB8B': '\u0698',
  '\uFB8C': '\u0691',
  '\uFB8D': '\u0691',
  '\uFB8E': '\u06A9',
  '\uFB8F': '\u06A9',
  '\uFB90': '\u06A9',
  '\uFB91': '\u06A9',
  '\uFB92': '\u06AF',
  '\uFB93': '\u06AF',
  '\uFB94': '\u06AF',
  '\uFB95': '\u06AF',
  '\uFB96': '\u06B3',
  '\uFB97': '\u06B3',
  '\uFB98': '\u06B3',
  '\uFB99': '\u06B3',
  '\uFB9A': '\u06B1',
  '\uFB9B': '\u06B1',
  '\uFB9C': '\u06B1',
  '\uFB9D': '\u06B1',
  '\uFB9E': '\u06BA',
  '\uFB9F': '\u06BA',
  '\uFBA0': '\u06BB',
  '\uFBA1': '\u06BB',
  '\uFBA2': '\u06BB',
  '\uFBA3': '\u06BB',
  '\uFBA4': '\u06C0',
  '\uFBA5': '\u06C0',
  '\uFBA6': '\u06C1',
  '\uFBA7': '\u06C1',
  '\uFBA8': '\u06C1',
  '\uFBA9': '\u06C1',
  '\uFBAA': '\u06BE',
  '\uFBAB': '\u06BE',
  '\uFBAC': '\u06BE',
  '\uFBAD': '\u06BE',
  '\uFBAE': '\u06D2',
  '\uFBAF': '\u06D2',
  '\uFBB0': '\u06D3',
  '\uFBB1': '\u06D3',
  '\uFBD3': '\u06AD',
  '\uFBD4': '\u06AD',
  '\uFBD5': '\u06AD',
  '\uFBD6': '\u06AD',
  '\uFBD7': '\u06C7',
  '\uFBD8': '\u06C7',
  '\uFBD9': '\u06C6',
  '\uFBDA': '\u06C6',
  '\uFBDB': '\u06C8',
  '\uFBDC': '\u06C8',
  '\uFBDD': '\u0677',
  '\uFBDE': '\u06CB',
  '\uFBDF': '\u06CB',
  '\uFBE0': '\u06C5',
  '\uFBE1': '\u06C5',
  '\uFBE2': '\u06C9',
  '\uFBE3': '\u06C9',
  '\uFBE4': '\u06D0',
  '\uFBE5': '\u06D0',
  '\uFBE6': '\u06D0',
  '\uFBE7': '\u06D0',
  '\uFBE8': '\u0649',
  '\uFBE9': '\u0649',
  '\uFBEA': '\u0626\u0627',
  '\uFBEB': '\u0626\u0627',
  '\uFBEC': '\u0626\u06D5',
  '\uFBED': '\u0626\u06D5',
  '\uFBEE': '\u0626\u0648',
  '\uFBEF': '\u0626\u0648',
  '\uFBF0': '\u0626\u06C7',
  '\uFBF1': '\u0626\u06C7',
  '\uFBF2': '\u0626\u06C6',
  '\uFBF3': '\u0626\u06C6',
  '\uFBF4': '\u0626\u06C8',
  '\uFBF5': '\u0626\u06C8',
  '\uFBF6': '\u0626\u06D0',
  '\uFBF7': '\u0626\u06D0',
  '\uFBF8': '\u0626\u06D0',
  '\uFBF9': '\u0626\u0649',
  '\uFBFA': '\u0626\u0649',
  '\uFBFB': '\u0626\u0649',
  '\uFBFC': '\u06CC',
  '\uFBFD': '\u06CC',
  '\uFBFE': '\u06CC',
  '\uFBFF': '\u06CC',
  '\uFC00': '\u0626\u062C',
  '\uFC01': '\u0626\u062D',
  '\uFC02': '\u0626\u0645',
  '\uFC03': '\u0626\u0649',
  '\uFC04': '\u0626\u064A',
  '\uFC05': '\u0628\u062C',
  '\uFC06': '\u0628\u062D',
  '\uFC07': '\u0628\u062E',
  '\uFC08': '\u0628\u0645',
  '\uFC09': '\u0628\u0649',
  '\uFC0A': '\u0628\u064A',
  '\uFC0B': '\u062A\u062C',
  '\uFC0C': '\u062A\u062D',
  '\uFC0D': '\u062A\u062E',
  '\uFC0E': '\u062A\u0645',
  '\uFC0F': '\u062A\u0649',
  '\uFC10': '\u062A\u064A',
  '\uFC11': '\u062B\u062C',
  '\uFC12': '\u062B\u0645',
  '\uFC13': '\u062B\u0649',
  '\uFC14': '\u062B\u064A',
  '\uFC15': '\u062C\u062D',
  '\uFC16': '\u062C\u0645',
  '\uFC17': '\u062D\u062C',
  '\uFC18': '\u062D\u0645',
  '\uFC19': '\u062E\u062C',
  '\uFC1A': '\u062E\u062D',
  '\uFC1B': '\u062E\u0645',
  '\uFC1C': '\u0633\u062C',
  '\uFC1D': '\u0633\u062D',
  '\uFC1E': '\u0633\u062E',
  '\uFC1F': '\u0633\u0645',
  '\uFC20': '\u0635\u062D',
  '\uFC21': '\u0635\u0645',
  '\uFC22': '\u0636\u062C',
  '\uFC23': '\u0636\u062D',
  '\uFC24': '\u0636\u062E',
  '\uFC25': '\u0636\u0645',
  '\uFC26': '\u0637\u062D',
  '\uFC27': '\u0637\u0645',
  '\uFC28': '\u0638\u0645',
  '\uFC29': '\u0639\u062C',
  '\uFC2A': '\u0639\u0645',
  '\uFC2B': '\u063A\u062C',
  '\uFC2C': '\u063A\u0645',
  '\uFC2D': '\u0641\u062C',
  '\uFC2E': '\u0641\u062D',
  '\uFC2F': '\u0641\u062E',
  '\uFC30': '\u0641\u0645',
  '\uFC31': '\u0641\u0649',
  '\uFC32': '\u0641\u064A',
  '\uFC33': '\u0642\u062D',
  '\uFC34': '\u0642\u0645',
  '\uFC35': '\u0642\u0649',
  '\uFC36': '\u0642\u064A',
  '\uFC37': '\u0643\u0627',
  '\uFC38': '\u0643\u062C',
  '\uFC39': '\u0643\u062D',
  '\uFC3A': '\u0643\u062E',
  '\uFC3B': '\u0643\u0644',
  '\uFC3C': '\u0643\u0645',
  '\uFC3D': '\u0643\u0649',
  '\uFC3E': '\u0643\u064A',
  '\uFC3F': '\u0644\u062C',
  '\uFC40': '\u0644\u062D',
  '\uFC41': '\u0644\u062E',
  '\uFC42': '\u0644\u0645',
  '\uFC43': '\u0644\u0649',
  '\uFC44': '\u0644\u064A',
  '\uFC45': '\u0645\u062C',
  '\uFC46': '\u0645\u062D',
  '\uFC47': '\u0645\u062E',
  '\uFC48': '\u0645\u0645',
  '\uFC49': '\u0645\u0649',
  '\uFC4A': '\u0645\u064A',
  '\uFC4B': '\u0646\u062C',
  '\uFC4C': '\u0646\u062D',
  '\uFC4D': '\u0646\u062E',
  '\uFC4E': '\u0646\u0645',
  '\uFC4F': '\u0646\u0649',
  '\uFC50': '\u0646\u064A',
  '\uFC51': '\u0647\u062C',
  '\uFC52': '\u0647\u0645',
  '\uFC53': '\u0647\u0649',
  '\uFC54': '\u0647\u064A',
  '\uFC55': '\u064A\u062C',
  '\uFC56': '\u064A\u062D',
  '\uFC57': '\u064A\u062E',
  '\uFC58': '\u064A\u0645',
  '\uFC59': '\u064A\u0649',
  '\uFC5A': '\u064A\u064A',
  '\uFC5B': '\u0630\u0670',
  '\uFC5C': '\u0631\u0670',
  '\uFC5D': '\u0649\u0670',
  '\uFC5E': '\u0020\u064C\u0651',
  '\uFC5F': '\u0020\u064D\u0651',
  '\uFC60': '\u0020\u064E\u0651',
  '\uFC61': '\u0020\u064F\u0651',
  '\uFC62': '\u0020\u0650\u0651',
  '\uFC63': '\u0020\u0651\u0670',
  '\uFC64': '\u0626\u0631',
  '\uFC65': '\u0626\u0632',
  '\uFC66': '\u0626\u0645',
  '\uFC67': '\u0626\u0646',
  '\uFC68': '\u0626\u0649',
  '\uFC69': '\u0626\u064A',
  '\uFC6A': '\u0628\u0631',
  '\uFC6B': '\u0628\u0632',
  '\uFC6C': '\u0628\u0645',
  '\uFC6D': '\u0628\u0646',
  '\uFC6E': '\u0628\u0649',
  '\uFC6F': '\u0628\u064A',
  '\uFC70': '\u062A\u0631',
  '\uFC71': '\u062A\u0632',
  '\uFC72': '\u062A\u0645',
  '\uFC73': '\u062A\u0646',
  '\uFC74': '\u062A\u0649',
  '\uFC75': '\u062A\u064A',
  '\uFC76': '\u062B\u0631',
  '\uFC77': '\u062B\u0632',
  '\uFC78': '\u062B\u0645',
  '\uFC79': '\u062B\u0646',
  '\uFC7A': '\u062B\u0649',
  '\uFC7B': '\u062B\u064A',
  '\uFC7C': '\u0641\u0649',
  '\uFC7D': '\u0641\u064A',
  '\uFC7E': '\u0642\u0649',
  '\uFC7F': '\u0642\u064A',
  '\uFC80': '\u0643\u0627',
  '\uFC81': '\u0643\u0644',
  '\uFC82': '\u0643\u0645',
  '\uFC83': '\u0643\u0649',
  '\uFC84': '\u0643\u064A',
  '\uFC85': '\u0644\u0645',
  '\uFC86': '\u0644\u0649',
  '\uFC87': '\u0644\u064A',
  '\uFC88': '\u0645\u0627',
  '\uFC89': '\u0645\u0645',
  '\uFC8A': '\u0646\u0631',
  '\uFC8B': '\u0646\u0632',
  '\uFC8C': '\u0646\u0645',
  '\uFC8D': '\u0646\u0646',
  '\uFC8E': '\u0646\u0649',
  '\uFC8F': '\u0646\u064A',
  '\uFC90': '\u0649\u0670',
  '\uFC91': '\u064A\u0631',
  '\uFC92': '\u064A\u0632',
  '\uFC93': '\u064A\u0645',
  '\uFC94': '\u064A\u0646',
  '\uFC95': '\u064A\u0649',
  '\uFC96': '\u064A\u064A',
  '\uFC97': '\u0626\u062C',
  '\uFC98': '\u0626\u062D',
  '\uFC99': '\u0626\u062E',
  '\uFC9A': '\u0626\u0645',
  '\uFC9B': '\u0626\u0647',
  '\uFC9C': '\u0628\u062C',
  '\uFC9D': '\u0628\u062D',
  '\uFC9E': '\u0628\u062E',
  '\uFC9F': '\u0628\u0645',
  '\uFCA0': '\u0628\u0647',
  '\uFCA1': '\u062A\u062C',
  '\uFCA2': '\u062A\u062D',
  '\uFCA3': '\u062A\u062E',
  '\uFCA4': '\u062A\u0645',
  '\uFCA5': '\u062A\u0647',
  '\uFCA6': '\u062B\u0645',
  '\uFCA7': '\u062C\u062D',
  '\uFCA8': '\u062C\u0645',
  '\uFCA9': '\u062D\u062C',
  '\uFCAA': '\u062D\u0645',
  '\uFCAB': '\u062E\u062C',
  '\uFCAC': '\u062E\u0645',
  '\uFCAD': '\u0633\u062C',
  '\uFCAE': '\u0633\u062D',
  '\uFCAF': '\u0633\u062E',
  '\uFCB0': '\u0633\u0645',
  '\uFCB1': '\u0635\u062D',
  '\uFCB2': '\u0635\u062E',
  '\uFCB3': '\u0635\u0645',
  '\uFCB4': '\u0636\u062C',
  '\uFCB5': '\u0636\u062D',
  '\uFCB6': '\u0636\u062E',
  '\uFCB7': '\u0636\u0645',
  '\uFCB8': '\u0637\u062D',
  '\uFCB9': '\u0638\u0645',
  '\uFCBA': '\u0639\u062C',
  '\uFCBB': '\u0639\u0645',
  '\uFCBC': '\u063A\u062C',
  '\uFCBD': '\u063A\u0645',
  '\uFCBE': '\u0641\u062C',
  '\uFCBF': '\u0641\u062D',
  '\uFCC0': '\u0641\u062E',
  '\uFCC1': '\u0641\u0645',
  '\uFCC2': '\u0642\u062D',
  '\uFCC3': '\u0642\u0645',
  '\uFCC4': '\u0643\u062C',
  '\uFCC5': '\u0643\u062D',
  '\uFCC6': '\u0643\u062E',
  '\uFCC7': '\u0643\u0644',
  '\uFCC8': '\u0643\u0645',
  '\uFCC9': '\u0644\u062C',
  '\uFCCA': '\u0644\u062D',
  '\uFCCB': '\u0644\u062E',
  '\uFCCC': '\u0644\u0645',
  '\uFCCD': '\u0644\u0647',
  '\uFCCE': '\u0645\u062C',
  '\uFCCF': '\u0645\u062D',
  '\uFCD0': '\u0645\u062E',
  '\uFCD1': '\u0645\u0645',
  '\uFCD2': '\u0646\u062C',
  '\uFCD3': '\u0646\u062D',
  '\uFCD4': '\u0646\u062E',
  '\uFCD5': '\u0646\u0645',
  '\uFCD6': '\u0646\u0647',
  '\uFCD7': '\u0647\u062C',
  '\uFCD8': '\u0647\u0645',
  '\uFCD9': '\u0647\u0670',
  '\uFCDA': '\u064A\u062C',
  '\uFCDB': '\u064A\u062D',
  '\uFCDC': '\u064A\u062E',
  '\uFCDD': '\u064A\u0645',
  '\uFCDE': '\u064A\u0647',
  '\uFCDF': '\u0626\u0645',
  '\uFCE0': '\u0626\u0647',
  '\uFCE1': '\u0628\u0645',
  '\uFCE2': '\u0628\u0647',
  '\uFCE3': '\u062A\u0645',
  '\uFCE4': '\u062A\u0647',
  '\uFCE5': '\u062B\u0645',
  '\uFCE6': '\u062B\u0647',
  '\uFCE7': '\u0633\u0645',
  '\uFCE8': '\u0633\u0647',
  '\uFCE9': '\u0634\u0645',
  '\uFCEA': '\u0634\u0647',
  '\uFCEB': '\u0643\u0644',
  '\uFCEC': '\u0643\u0645',
  '\uFCED': '\u0644\u0645',
  '\uFCEE': '\u0646\u0645',
  '\uFCEF': '\u0646\u0647',
  '\uFCF0': '\u064A\u0645',
  '\uFCF1': '\u064A\u0647',
  '\uFCF2': '\u0640\u064E\u0651',
  '\uFCF3': '\u0640\u064F\u0651',
  '\uFCF4': '\u0640\u0650\u0651',
  '\uFCF5': '\u0637\u0649',
  '\uFCF6': '\u0637\u064A',
  '\uFCF7': '\u0639\u0649',
  '\uFCF8': '\u0639\u064A',
  '\uFCF9': '\u063A\u0649',
  '\uFCFA': '\u063A\u064A',
  '\uFCFB': '\u0633\u0649',
  '\uFCFC': '\u0633\u064A',
  '\uFCFD': '\u0634\u0649',
  '\uFCFE': '\u0634\u064A',
  '\uFCFF': '\u062D\u0649',
  '\uFD00': '\u062D\u064A',
  '\uFD01': '\u062C\u0649',
  '\uFD02': '\u062C\u064A',
  '\uFD03': '\u062E\u0649',
  '\uFD04': '\u062E\u064A',
  '\uFD05': '\u0635\u0649',
  '\uFD06': '\u0635\u064A',
  '\uFD07': '\u0636\u0649',
  '\uFD08': '\u0636\u064A',
  '\uFD09': '\u0634\u062C',
  '\uFD0A': '\u0634\u062D',
  '\uFD0B': '\u0634\u062E',
  '\uFD0C': '\u0634\u0645',
  '\uFD0D': '\u0634\u0631',
  '\uFD0E': '\u0633\u0631',
  '\uFD0F': '\u0635\u0631',
  '\uFD10': '\u0636\u0631',
  '\uFD11': '\u0637\u0649',
  '\uFD12': '\u0637\u064A',
  '\uFD13': '\u0639\u0649',
  '\uFD14': '\u0639\u064A',
  '\uFD15': '\u063A\u0649',
  '\uFD16': '\u063A\u064A',
  '\uFD17': '\u0633\u0649',
  '\uFD18': '\u0633\u064A',
  '\uFD19': '\u0634\u0649',
  '\uFD1A': '\u0634\u064A',
  '\uFD1B': '\u062D\u0649',
  '\uFD1C': '\u062D\u064A',
  '\uFD1D': '\u062C\u0649',
  '\uFD1E': '\u062C\u064A',
  '\uFD1F': '\u062E\u0649',
  '\uFD20': '\u062E\u064A',
  '\uFD21': '\u0635\u0649',
  '\uFD22': '\u0635\u064A',
  '\uFD23': '\u0636\u0649',
  '\uFD24': '\u0636\u064A',
  '\uFD25': '\u0634\u062C',
  '\uFD26': '\u0634\u062D',
  '\uFD27': '\u0634\u062E',
  '\uFD28': '\u0634\u0645',
  '\uFD29': '\u0634\u0631',
  '\uFD2A': '\u0633\u0631',
  '\uFD2B': '\u0635\u0631',
  '\uFD2C': '\u0636\u0631',
  '\uFD2D': '\u0634\u062C',
  '\uFD2E': '\u0634\u062D',
  '\uFD2F': '\u0634\u062E',
  '\uFD30': '\u0634\u0645',
  '\uFD31': '\u0633\u0647',
  '\uFD32': '\u0634\u0647',
  '\uFD33': '\u0637\u0645',
  '\uFD34': '\u0633\u062C',
  '\uFD35': '\u0633\u062D',
  '\uFD36': '\u0633\u062E',
  '\uFD37': '\u0634\u062C',
  '\uFD38': '\u0634\u062D',
  '\uFD39': '\u0634\u062E',
  '\uFD3A': '\u0637\u0645',
  '\uFD3B': '\u0638\u0645',
  '\uFD3C': '\u0627\u064B',
  '\uFD3D': '\u0627\u064B',
  '\uFD50': '\u062A\u062C\u0645',
  '\uFD51': '\u062A\u062D\u062C',
  '\uFD52': '\u062A\u062D\u062C',
  '\uFD53': '\u062A\u062D\u0645',
  '\uFD54': '\u062A\u062E\u0645',
  '\uFD55': '\u062A\u0645\u062C',
  '\uFD56': '\u062A\u0645\u062D',
  '\uFD57': '\u062A\u0645\u062E',
  '\uFD58': '\u062C\u0645\u062D',
  '\uFD59': '\u062C\u0645\u062D',
  '\uFD5A': '\u062D\u0645\u064A',
  '\uFD5B': '\u062D\u0645\u0649',
  '\uFD5C': '\u0633\u062D\u062C',
  '\uFD5D': '\u0633\u062C\u062D',
  '\uFD5E': '\u0633\u062C\u0649',
  '\uFD5F': '\u0633\u0645\u062D',
  '\uFD60': '\u0633\u0645\u062D',
  '\uFD61': '\u0633\u0645\u062C',
  '\uFD62': '\u0633\u0645\u0645',
  '\uFD63': '\u0633\u0645\u0645',
  '\uFD64': '\u0635\u062D\u062D',
  '\uFD65': '\u0635\u062D\u062D',
  '\uFD66': '\u0635\u0645\u0645',
  '\uFD67': '\u0634\u062D\u0645',
  '\uFD68': '\u0634\u062D\u0645',
  '\uFD69': '\u0634\u062C\u064A',
  '\uFD6A': '\u0634\u0645\u062E',
  '\uFD6B': '\u0634\u0645\u062E',
  '\uFD6C': '\u0634\u0645\u0645',
  '\uFD6D': '\u0634\u0645\u0645',
  '\uFD6E': '\u0636\u062D\u0649',
  '\uFD6F': '\u0636\u062E\u0645',
  '\uFD70': '\u0636\u062E\u0645',
  '\uFD71': '\u0637\u0645\u062D',
  '\uFD72': '\u0637\u0645\u062D',
  '\uFD73': '\u0637\u0645\u0645',
  '\uFD74': '\u0637\u0645\u064A',
  '\uFD75': '\u0639\u062C\u0645',
  '\uFD76': '\u0639\u0645\u0645',
  '\uFD77': '\u0639\u0645\u0645',
  '\uFD78': '\u0639\u0645\u0649',
  '\uFD79': '\u063A\u0645\u0645',
  '\uFD7A': '\u063A\u0645\u064A',
  '\uFD7B': '\u063A\u0645\u0649',
  '\uFD7C': '\u0641\u062E\u0645',
  '\uFD7D': '\u0641\u062E\u0645',
  '\uFD7E': '\u0642\u0645\u062D',
  '\uFD7F': '\u0642\u0645\u0645',
  '\uFD80': '\u0644\u062D\u0645',
  '\uFD81': '\u0644\u062D\u064A',
  '\uFD82': '\u0644\u062D\u0649',
  '\uFD83': '\u0644\u062C\u062C',
  '\uFD84': '\u0644\u062C\u062C',
  '\uFD85': '\u0644\u062E\u0645',
  '\uFD86': '\u0644\u062E\u0645',
  '\uFD87': '\u0644\u0645\u062D',
  '\uFD88': '\u0644\u0645\u062D',
  '\uFD89': '\u0645\u062D\u062C',
  '\uFD8A': '\u0645\u062D\u0645',
  '\uFD8B': '\u0645\u062D\u064A',
  '\uFD8C': '\u0645\u062C\u062D',
  '\uFD8D': '\u0645\u062C\u0645',
  '\uFD8E': '\u0645\u062E\u062C',
  '\uFD8F': '\u0645\u062E\u0645',
  '\uFD92': '\u0645\u062C\u062E',
  '\uFD93': '\u0647\u0645\u062C',
  '\uFD94': '\u0647\u0645\u0645',
  '\uFD95': '\u0646\u062D\u0645',
  '\uFD96': '\u0646\u062D\u0649',
  '\uFD97': '\u0646\u062C\u0645',
  '\uFD98': '\u0646\u062C\u0645',
  '\uFD99': '\u0646\u062C\u0649',
  '\uFD9A': '\u0646\u0645\u064A',
  '\uFD9B': '\u0646\u0645\u0649',
  '\uFD9C': '\u064A\u0645\u0645',
  '\uFD9D': '\u064A\u0645\u0645',
  '\uFD9E': '\u0628\u062E\u064A',
  '\uFD9F': '\u062A\u062C\u064A',
  '\uFDA0': '\u062A\u062C\u0649',
  '\uFDA1': '\u062A\u062E\u064A',
  '\uFDA2': '\u062A\u062E\u0649',
  '\uFDA3': '\u062A\u0645\u064A',
  '\uFDA4': '\u062A\u0645\u0649',
  '\uFDA5': '\u062C\u0645\u064A',
  '\uFDA6': '\u062C\u062D\u0649',
  '\uFDA7': '\u062C\u0645\u0649',
  '\uFDA8': '\u0633\u062E\u0649',
  '\uFDA9': '\u0635\u062D\u064A',
  '\uFDAA': '\u0634\u062D\u064A',
  '\uFDAB': '\u0636\u062D\u064A',
  '\uFDAC': '\u0644\u062C\u064A',
  '\uFDAD': '\u0644\u0645\u064A',
  '\uFDAE': '\u064A\u062D\u064A',
  '\uFDAF': '\u064A\u062C\u064A',
  '\uFDB0': '\u064A\u0645\u064A',
  '\uFDB1': '\u0645\u0645\u064A',
  '\uFDB2': '\u0642\u0645\u064A',
  '\uFDB3': '\u0646\u062D\u064A',
  '\uFDB4': '\u0642\u0645\u062D',
  '\uFDB5': '\u0644\u062D\u0645',
  '\uFDB6': '\u0639\u0645\u064A',
  '\uFDB7': '\u0643\u0645\u064A',
  '\uFDB8': '\u0646\u062C\u062D',
  '\uFDB9': '\u0645\u062E\u064A',
  '\uFDBA': '\u0644\u062C\u0645',
  '\uFDBB': '\u0643\u0645\u0645',
  '\uFDBC': '\u0644\u062C\u0645',
  '\uFDBD': '\u0646\u062C\u062D',
  '\uFDBE': '\u062C\u062D\u064A',
  '\uFDBF': '\u062D\u062C\u064A',
  '\uFDC0': '\u0645\u062C\u064A',
  '\uFDC1': '\u0641\u0645\u064A',
  '\uFDC2': '\u0628\u062D\u064A',
  '\uFDC3': '\u0643\u0645\u0645',
  '\uFDC4': '\u0639\u062C\u0645',
  '\uFDC5': '\u0635\u0645\u0645',
  '\uFDC6': '\u0633\u062E\u064A',
  '\uFDC7': '\u0646\u062C\u064A',
  '\uFE49': '\u203E',
  '\uFE4A': '\u203E',
  '\uFE4B': '\u203E',
  '\uFE4C': '\u203E',
  '\uFE4D': '\u005F',
  '\uFE4E': '\u005F',
  '\uFE4F': '\u005F',
  '\uFE80': '\u0621',
  '\uFE81': '\u0622',
  '\uFE82': '\u0622',
  '\uFE83': '\u0623',
  '\uFE84': '\u0623',
  '\uFE85': '\u0624',
  '\uFE86': '\u0624',
  '\uFE87': '\u0625',
  '\uFE88': '\u0625',
  '\uFE89': '\u0626',
  '\uFE8A': '\u0626',
  '\uFE8B': '\u0626',
  '\uFE8C': '\u0626',
  '\uFE8D': '\u0627',
  '\uFE8E': '\u0627',
  '\uFE8F': '\u0628',
  '\uFE90': '\u0628',
  '\uFE91': '\u0628',
  '\uFE92': '\u0628',
  '\uFE93': '\u0629',
  '\uFE94': '\u0629',
  '\uFE95': '\u062A',
  '\uFE96': '\u062A',
  '\uFE97': '\u062A',
  '\uFE98': '\u062A',
  '\uFE99': '\u062B',
  '\uFE9A': '\u062B',
  '\uFE9B': '\u062B',
  '\uFE9C': '\u062B',
  '\uFE9D': '\u062C',
  '\uFE9E': '\u062C',
  '\uFE9F': '\u062C',
  '\uFEA0': '\u062C',
  '\uFEA1': '\u062D',
  '\uFEA2': '\u062D',
  '\uFEA3': '\u062D',
  '\uFEA4': '\u062D',
  '\uFEA5': '\u062E',
  '\uFEA6': '\u062E',
  '\uFEA7': '\u062E',
  '\uFEA8': '\u062E',
  '\uFEA9': '\u062F',
  '\uFEAA': '\u062F',
  '\uFEAB': '\u0630',
  '\uFEAC': '\u0630',
  '\uFEAD': '\u0631',
  '\uFEAE': '\u0631',
  '\uFEAF': '\u0632',
  '\uFEB0': '\u0632',
  '\uFEB1': '\u0633',
  '\uFEB2': '\u0633',
  '\uFEB3': '\u0633',
  '\uFEB4': '\u0633',
  '\uFEB5': '\u0634',
  '\uFEB6': '\u0634',
  '\uFEB7': '\u0634',
  '\uFEB8': '\u0634',
  '\uFEB9': '\u0635',
  '\uFEBA': '\u0635',
  '\uFEBB': '\u0635',
  '\uFEBC': '\u0635',
  '\uFEBD': '\u0636',
  '\uFEBE': '\u0636',
  '\uFEBF': '\u0636',
  '\uFEC0': '\u0636',
  '\uFEC1': '\u0637',
  '\uFEC2': '\u0637',
  '\uFEC3': '\u0637',
  '\uFEC4': '\u0637',
  '\uFEC5': '\u0638',
  '\uFEC6': '\u0638',
  '\uFEC7': '\u0638',
  '\uFEC8': '\u0638',
  '\uFEC9': '\u0639',
  '\uFECA': '\u0639',
  '\uFECB': '\u0639',
  '\uFECC': '\u0639',
  '\uFECD': '\u063A',
  '\uFECE': '\u063A',
  '\uFECF': '\u063A',
  '\uFED0': '\u063A',
  '\uFED1': '\u0641',
  '\uFED2': '\u0641',
  '\uFED3': '\u0641',
  '\uFED4': '\u0641',
  '\uFED5': '\u0642',
  '\uFED6': '\u0642',
  '\uFED7': '\u0642',
  '\uFED8': '\u0642',
  '\uFED9': '\u0643',
  '\uFEDA': '\u0643',
  '\uFEDB': '\u0643',
  '\uFEDC': '\u0643',
  '\uFEDD': '\u0644',
  '\uFEDE': '\u0644',
  '\uFEDF': '\u0644',
  '\uFEE0': '\u0644',
  '\uFEE1': '\u0645',
  '\uFEE2': '\u0645',
  '\uFEE3': '\u0645',
  '\uFEE4': '\u0645',
  '\uFEE5': '\u0646',
  '\uFEE6': '\u0646',
  '\uFEE7': '\u0646',
  '\uFEE8': '\u0646',
  '\uFEE9': '\u0647',
  '\uFEEA': '\u0647',
  '\uFEEB': '\u0647',
  '\uFEEC': '\u0647',
  '\uFEED': '\u0648',
  '\uFEEE': '\u0648',
  '\uFEEF': '\u0649',
  '\uFEF0': '\u0649',
  '\uFEF1': '\u064A',
  '\uFEF2': '\u064A',
  '\uFEF3': '\u064A',
  '\uFEF4': '\u064A',
  '\uFEF5': '\u0644\u0622',
  '\uFEF6': '\u0644\u0622',
  '\uFEF7': '\u0644\u0623',
  '\uFEF8': '\u0644\u0623',
  '\uFEF9': '\u0644\u0625',
  '\uFEFA': '\u0644\u0625',
  '\uFEFB': '\u0644\u0627',
  '\uFEFC': '\u0644\u0627'
};

function reverseIfRtl(chars) {
  var charsLength = chars.length;
  //reverse an arabic ligature
  if (charsLength <= 1 || !isRTLRangeFor(chars.charCodeAt(0))) {
    return chars;
  }
  var s = '';
  for (var ii = charsLength - 1; ii >= 0; ii--) {
    s += chars[ii];
  }
  return s;
}

function adjustWidths(properties) {
  if (properties.fontMatrix[0] === FONT_IDENTITY_MATRIX[0]) {
    return;
  }
  // adjusting width to fontMatrix scale
  var scale = 0.001 / properties.fontMatrix[0];
  var glyphsWidths = properties.widths;
  for (var glyph in glyphsWidths) {
    glyphsWidths[glyph] *= scale;
  }
  properties.defaultWidth *= scale;
}

function getFontType(type, subtype) {
  switch (type) {
    case 'Type1':
      return subtype === 'Type1C' ? FontType.TYPE1C : FontType.TYPE1;
    case 'CIDFontType0':
      return subtype === 'CIDFontType0C' ? FontType.CIDFONTTYPE0C :
        FontType.CIDFONTTYPE0;
    case 'OpenType':
      return FontType.OPENTYPE;
    case 'TrueType':
      return FontType.TRUETYPE;
    case 'CIDFontType2':
      return FontType.CIDFONTTYPE2;
    case 'MMType1':
      return FontType.MMTYPE1;
    case 'Type0':
      return FontType.TYPE0;
    default:
      return FontType.UNKNOWN;
  }
}

var Glyph = (function GlyphClosure() {
  function Glyph(fontChar, unicode, accent, width, vmetric, operatorListId) {
    this.fontChar = fontChar;
    this.unicode = unicode;
    this.accent = accent;
    this.width = width;
    this.vmetric = vmetric;
    this.operatorListId = operatorListId;
  }

  Glyph.prototype.matchesForCache =
      function(fontChar, unicode, accent, width, vmetric, operatorListId) {
    return this.fontChar === fontChar &&
           this.unicode === unicode &&
           this.accent === accent &&
           this.width === width &&
           this.vmetric === vmetric &&
           this.operatorListId === operatorListId;
  };

  return Glyph;
})();

var ToUnicodeMap = (function ToUnicodeMapClosure() {
  function ToUnicodeMap(cmap) {
    // The elements of this._map can be integers or strings, depending on how
    // |cmap| was created.
    this._map = cmap;
  }

  ToUnicodeMap.prototype = {
    get length() {
      return this._map.length;
    },

    forEach: function(callback) {
      for (var charCode in this._map) {
        callback(charCode, this._map[charCode].charCodeAt(0));
      }
    },

    has: function(i) {
      return this._map[i] !== undefined;
    },

    get: function(i) {
      return this._map[i];
    },

    charCodeOf: function(v) {
      return this._map.indexOf(v);
    }
  };

  return ToUnicodeMap;
})();

var IdentityToUnicodeMap = (function IdentityToUnicodeMapClosure() {
  function IdentityToUnicodeMap(firstChar, lastChar) {
    this.firstChar = firstChar;
    this.lastChar = lastChar;
  }

  IdentityToUnicodeMap.prototype = {
    get length() {
      return (this.lastChar + 1) - this.firstChar;
    },

    forEach: function (callback) {
      for (var i = this.firstChar, ii = this.lastChar; i <= ii; i++) {
        callback(i, i);
      }
    },

    has: function (i) {
      return this.firstChar <= i && i <= this.lastChar;
    },

    get: function (i) {
      if (this.firstChar <= i && i <= this.lastChar) {
        return String.fromCharCode(i);
      }
      return undefined;
    },

    charCodeOf: function (v) {
      error('should not call .charCodeOf');
    }
  };

  return IdentityToUnicodeMap;
})();

var OpenTypeFileBuilder = (function OpenTypeFileBuilderClosure() {
  function writeInt16(dest, offset, num) {
    dest[offset] = (num >> 8) & 0xFF;
    dest[offset + 1] = num & 0xFF;
  }

  function writeInt32(dest, offset, num) {
    dest[offset] = (num >> 24) & 0xFF;
    dest[offset + 1] = (num >> 16) & 0xFF;
    dest[offset + 2] = (num >> 8) & 0xFF;
    dest[offset + 3] = num & 0xFF;
  }

  function writeData(dest, offset, data) {
    var i, ii;
    if (data instanceof Uint8Array) {
      dest.set(data, offset);
    } else if (typeof data === 'string') {
      for (i = 0, ii = data.length; i < ii; i++) {
        dest[offset++] = data.charCodeAt(i) & 0xFF;
      }
    } else {
      // treating everything else as array
      for (i = 0, ii = data.length; i < ii; i++) {
        dest[offset++] = data[i] & 0xFF;
      }
    }
  }

  function OpenTypeFileBuilder(sfnt) {
    this.sfnt = sfnt;
    this.tables = Object.create(null);
  }

  OpenTypeFileBuilder.getSearchParams =
      function OpenTypeFileBuilder_getSearchParams(entriesCount, entrySize) {
    var maxPower2 = 1, log2 = 0;
    while ((maxPower2 ^ entriesCount) > maxPower2) {
      maxPower2 <<= 1;
      log2++;
    }
    var searchRange = maxPower2 * entrySize;
    return {
      range: searchRange,
      entry: log2,
      rangeShift: entrySize * entriesCount - searchRange
    };
  };

  var OTF_HEADER_SIZE = 12;
  var OTF_TABLE_ENTRY_SIZE = 16;

  OpenTypeFileBuilder.prototype = {
    toArray: function OpenTypeFileBuilder_toArray() {
      var sfnt = this.sfnt;

      // Tables needs to be written by ascendant alphabetic order
      var tables = this.tables;
      var tablesNames = Object.keys(tables);
      tablesNames.sort();
      var numTables = tablesNames.length;

      var i, j, jj, table, tableName;
      // layout the tables data
      var offset = OTF_HEADER_SIZE + numTables * OTF_TABLE_ENTRY_SIZE;
      var tableOffsets = [offset];
      for (i = 0; i < numTables; i++) {
        table = tables[tablesNames[i]];
        var paddedLength = ((table.length + 3) & ~3) >>> 0;
        offset += paddedLength;
        tableOffsets.push(offset);
      }

      var file = new Uint8Array(offset);
      // write the table data first (mostly for checksum)
      for (i = 0; i < numTables; i++) {
        table = tables[tablesNames[i]];
        writeData(file, tableOffsets[i], table);
      }

      // sfnt version (4 bytes)
      if (sfnt === 'true') {
        // Windows hates the Mac TrueType sfnt version number
        sfnt = string32(0x00010000);
      }
      file[0] = sfnt.charCodeAt(0) & 0xFF;
      file[1] = sfnt.charCodeAt(1) & 0xFF;
      file[2] = sfnt.charCodeAt(2) & 0xFF;
      file[3] = sfnt.charCodeAt(3) & 0xFF;

      // numTables (2 bytes)
      writeInt16(file, 4, numTables);

      var searchParams = OpenTypeFileBuilder.getSearchParams(numTables, 16);

      // searchRange (2 bytes)
      writeInt16(file, 6, searchParams.range);
      // entrySelector (2 bytes)
      writeInt16(file, 8, searchParams.entry);
      // rangeShift (2 bytes)
      writeInt16(file, 10, searchParams.rangeShift);

      offset = OTF_HEADER_SIZE;
      // writing table entries
      for (i = 0; i < numTables; i++) {
        tableName = tablesNames[i];
        file[offset] = tableName.charCodeAt(0) & 0xFF;
        file[offset + 1] = tableName.charCodeAt(1) & 0xFF;
        file[offset + 2] = tableName.charCodeAt(2) & 0xFF;
        file[offset + 3] = tableName.charCodeAt(3) & 0xFF;

        // checksum
        var checksum = 0;
        for (j = tableOffsets[i], jj = tableOffsets[i + 1]; j < jj; j += 4) {
          var quad = (file[j] << 24) + (file[j + 1] << 16) +
                     (file[j + 2] << 8) + file[j + 3];
          checksum = (checksum + quad) | 0;
        }
        writeInt32(file, offset + 4, checksum);

        // offset
        writeInt32(file, offset + 8, tableOffsets[i]);
        // length
        writeInt32(file, offset + 12, tables[tableName].length);

        offset += OTF_TABLE_ENTRY_SIZE;
      }
      return file;
    },

    addTable: function OpenTypeFileBuilder_addTable(tag, data) {
      if (tag in this.tables) {
        throw new Error('Table ' + tag + ' already exists');
      }
      this.tables[tag] = data;
    }
  };

  return OpenTypeFileBuilder;
})();

/**
 * 'Font' is the class the outside world should use, it encapsulate all the font
 * decoding logics whatever type it is (assuming the font type is supported).
 *
 * For example to read a Type1 font and to attach it to the document:
 *   var type1Font = new Font("MyFontName", binaryFile, propertiesObject);
 *   type1Font.bind();
 */
var Font = (function FontClosure() {
  function Font(name, file, properties) {
    var charCode, glyphName, fontChar;

    this.name = name;
    this.loadedName = properties.loadedName;
    this.isType3Font = properties.isType3Font;
    this.sizes = [];

    this.glyphCache = {};

    var names = name.split('+');
    names = names.length > 1 ? names[1] : names[0];
    names = names.split(/[-,_]/g)[0];
    this.isSerifFont = !!(properties.flags & FontFlags.Serif);
    this.isSymbolicFont = !!(properties.flags & FontFlags.Symbolic);
    this.isMonospace = !!(properties.flags & FontFlags.FixedPitch);

    var type = properties.type;
    var subtype = properties.subtype;
    this.type = type;

    this.fallbackName = (this.isMonospace ? 'monospace' :
                         (this.isSerifFont ? 'serif' : 'sans-serif'));

    this.differences = properties.differences;
    this.widths = properties.widths;
    this.defaultWidth = properties.defaultWidth;
    this.composite = properties.composite;
    this.wideChars = properties.wideChars;
    this.cMap = properties.cMap;
    this.ascent = properties.ascent / PDF_GLYPH_SPACE_UNITS;
    this.descent = properties.descent / PDF_GLYPH_SPACE_UNITS;
    this.fontMatrix = properties.fontMatrix;

    this.toUnicode = properties.toUnicode = this.buildToUnicode(properties);

    this.toFontChar = [];

    if (properties.type === 'Type3') {
      for (charCode = 0; charCode < 256; charCode++) {
        this.toFontChar[charCode] = (this.differences[charCode] ||
                                     properties.defaultEncoding[charCode]);
      }
      this.fontType = FontType.TYPE3;
      return;
    }

    this.cidEncoding = properties.cidEncoding;
    this.vertical = properties.vertical;
    if (this.vertical) {
      this.vmetrics = properties.vmetrics;
      this.defaultVMetrics = properties.defaultVMetrics;
    }

    if (!file || file.isEmpty) {
      if (file) {
        // Some bad PDF generators will include empty font files,
        // attempting to recover by assuming that no file exists.
        warn('Font file is empty in "' + name + '" (' + this.loadedName + ')');
      }

      this.missingFile = true;
      // The file data is not specified. Trying to fix the font name
      // to be used with the canvas.font.
      var fontName = name.replace(/[,_]/g, '-');
      var isStandardFont = !!stdFontMap[fontName] ||
        !!(nonStdFontMap[fontName] && stdFontMap[nonStdFontMap[fontName]]);
      fontName = stdFontMap[fontName] || nonStdFontMap[fontName] || fontName;

      this.bold = (fontName.search(/bold/gi) !== -1);
      this.italic = ((fontName.search(/oblique/gi) !== -1) ||
                     (fontName.search(/italic/gi) !== -1));

      // Use 'name' instead of 'fontName' here because the original
      // name ArialBlack for example will be replaced by Helvetica.
      this.black = (name.search(/Black/g) !== -1);

      // if at least one width is present, remeasure all chars when exists
      this.remeasure = Object.keys(this.widths).length > 0;
      if (isStandardFont && type === 'CIDFontType2' &&
          properties.cidEncoding.indexOf('Identity-') === 0) {
        // Standard fonts might be embedded as CID font without glyph mapping.
        // Building one based on GlyphMapForStandardFonts.
        var map = [];
        for (var code in GlyphMapForStandardFonts) {
          map[+code] = GlyphMapForStandardFonts[code];
        }
        var isIdentityUnicode = this.toUnicode instanceof IdentityToUnicodeMap;
        if (!isIdentityUnicode) {
          this.toUnicode.forEach(function(charCode, unicodeCharCode) {
            map[+charCode] = unicodeCharCode;
          });
        }
        this.toFontChar = map;
        this.toUnicode = new ToUnicodeMap(map);
      } else if (/Symbol/i.test(fontName)) {
        var symbols = Encodings.SymbolSetEncoding;
        for (charCode in symbols) {
          fontChar = GlyphsUnicode[symbols[charCode]];
          if (!fontChar) {
            continue;
          }
          this.toFontChar[charCode] = fontChar;
        }
        for (charCode in properties.differences) {
          fontChar = GlyphsUnicode[properties.differences[charCode]];
          if (!fontChar) {
            continue;
          }
          this.toFontChar[charCode] = fontChar;
        }
      } else if (/Dingbats/i.test(fontName)) {
        if (/Wingdings/i.test(name)) {
          warn('Wingdings font without embedded font file, ' +
               'falling back to the ZapfDingbats encoding.');
        }
        var dingbats = Encodings.ZapfDingbatsEncoding;
        for (charCode in dingbats) {
          fontChar = DingbatsGlyphsUnicode[dingbats[charCode]];
          if (!fontChar) {
            continue;
          }
          this.toFontChar[charCode] = fontChar;
        }
        for (charCode in properties.differences) {
          fontChar = DingbatsGlyphsUnicode[properties.differences[charCode]];
          if (!fontChar) {
            continue;
          }
          this.toFontChar[charCode] = fontChar;
        }
      } else if (isStandardFont) {
        this.toFontChar = [];
        for (charCode in properties.defaultEncoding) {
          glyphName = (properties.differences[charCode] ||
                       properties.defaultEncoding[charCode]);
          this.toFontChar[charCode] = GlyphsUnicode[glyphName];
        }
      } else {
        var unicodeCharCode, notCidFont = (type.indexOf('CIDFontType') === -1);
        this.toUnicode.forEach(function(charCode, unicodeCharCode) {
          if (notCidFont) {
            glyphName = (properties.differences[charCode] ||
                         properties.defaultEncoding[charCode]);
            unicodeCharCode = (GlyphsUnicode[glyphName] || unicodeCharCode);
          }
          this.toFontChar[charCode] = unicodeCharCode;
        }.bind(this));
      }
      this.loadedName = fontName.split('-')[0];
      this.loading = false;
      this.fontType = getFontType(type, subtype);
      return;
    }

    // Some fonts might use wrong font types for Type1C or CIDFontType0C
    if (subtype === 'Type1C' && (type !== 'Type1' && type !== 'MMType1')) {
      // Some TrueType fonts by mistake claim Type1C
      if (isTrueTypeFile(file)) {
        subtype = 'TrueType';
      } else {
        type = 'Type1';
      }
    }
    if (subtype === 'CIDFontType0C' && type !== 'CIDFontType0') {
      type = 'CIDFontType0';
    }
    if (subtype === 'OpenType') {
      type = 'OpenType';
    }
    // Some CIDFontType0C fonts by mistake claim CIDFontType0.
    if (type === 'CIDFontType0') {
      subtype = isType1File(file) ? 'CIDFontType0' : 'CIDFontType0C';
    }

    var data;
    switch (type) {
      case 'MMType1':
        info('MMType1 font (' + name + '), falling back to Type1.');
        /* falls through */
      case 'Type1':
      case 'CIDFontType0':
        this.mimetype = 'font/opentype';

        var cff = (subtype === 'Type1C' || subtype === 'CIDFontType0C') ?
          new CFFFont(file, properties) : new Type1Font(name, file, properties);

        adjustWidths(properties);

        // Wrap the CFF data inside an OTF font file
        data = this.convert(name, cff, properties);
        break;

      case 'OpenType':
      case 'TrueType':
      case 'CIDFontType2':
        this.mimetype = 'font/opentype';

        // Repair the TrueType file. It is can be damaged in the point of
        // view of the sanitizer
        data = this.checkAndRepair(name, file, properties);
        if (this.isOpenType) {
          type = 'OpenType';
        }
        break;

      default:
        error('Font ' + type + ' is not supported');
        break;
    }

    this.data = data;
    this.fontType = getFontType(type, subtype);

    // Transfer some properties again that could change during font conversion
    this.fontMatrix = properties.fontMatrix;
    this.widths = properties.widths;
    this.defaultWidth = properties.defaultWidth;
    this.encoding = properties.baseEncoding;
    this.seacMap = properties.seacMap;

    this.loading = true;
  }

  Font.getFontID = (function () {
    var ID = 1;
    return function Font_getFontID() {
      return String(ID++);
    };
  })();

  function int16(b0, b1) {
    return (b0 << 8) + b1;
  }

  function int32(b0, b1, b2, b3) {
    return (b0 << 24) + (b1 << 16) + (b2 << 8) + b3;
  }

  function string16(value) {
    return String.fromCharCode((value >> 8) & 0xff, value & 0xff);
  }

  function safeString16(value) {
    // clamp value to the 16-bit int range
    value = (value > 0x7FFF ? 0x7FFF : (value < -0x8000 ? -0x8000 : value));
    return String.fromCharCode((value >> 8) & 0xff, value & 0xff);
  }

  function isTrueTypeFile(file) {
    var header = file.peekBytes(4);
    return readUint32(header, 0) === 0x00010000;
  }

  function isType1File(file) {
    var header = file.peekBytes(2);
    // All Type1 font programs must begin with the comment '%!' (0x25 + 0x21).
    if (header[0] === 0x25 && header[1] === 0x21) {
      return true;
    }
    // ... obviously some fonts violate that part of the specification,
    // please refer to the comment in |Type1Font| below.
    if (header[0] === 0x80 && header[1] === 0x01) { // pfb file header.
      return true;
    }
    return false;
  }

  /**
   * Helper function for |adjustMapping|.
   * @return {boolean}
   */
  function isProblematicUnicodeLocation(code) {
    if (code <= 0x1F) { // Control chars
      return true;
    }
    if (code >= 0x80 && code <= 0x9F) { // Control chars
      return true;
    }
    if ((code >= 0x2000 && code <= 0x200F) || // General punctuation chars
        (code >= 0x2028 && code <= 0x202F) ||
        (code >= 0x2060 && code <= 0x206F)) {
      return true;
    }
    if (code >= 0xFFF0 && code <= 0xFFFF) { // Specials Unicode block
      return true;
    }
    switch (code) {
      case 0x7F: // Control char
      case 0xA0: // Non breaking space
      case 0xAD: // Soft hyphen
      case 0x0E33: // Thai character SARA AM
      case 0x2011: // Non breaking hyphen
      case 0x205F: // Medium mathematical space
      case 0x25CC: // Dotted circle (combining mark)
        return true;
    }
    return false;
  }

  /**
   * Rebuilds the char code to glyph ID map by trying to replace the char codes
   * with their unicode value. It also moves char codes that are in known
   * problematic locations.
   * @return {Object} Two properties:
   * 'toFontChar' - maps original char codes(the value that will be read
   * from commands such as show text) to the char codes that will be used in the
   * font that we build
   * 'charCodeToGlyphId' - maps the new font char codes to glyph ids
   */
  function adjustMapping(charCodeToGlyphId, properties) {
    var toUnicode = properties.toUnicode;
    var isSymbolic = !!(properties.flags & FontFlags.Symbolic);
    var isIdentityUnicode =
      properties.toUnicode instanceof IdentityToUnicodeMap;
    var newMap = Object.create(null);
    var toFontChar = [];
    var usedFontCharCodes = [];
    var nextAvailableFontCharCode = PRIVATE_USE_OFFSET_START;
    for (var originalCharCode in charCodeToGlyphId) {
      originalCharCode |= 0;
      var glyphId = charCodeToGlyphId[originalCharCode];
      var fontCharCode = originalCharCode;
      // First try to map the value to a unicode position if a non identity map
      // was created.
      if (!isIdentityUnicode && toUnicode.has(originalCharCode)) {
        var unicode = toUnicode.get(fontCharCode);
        // TODO: Try to map ligatures to the correct spot.
        if (unicode.length === 1) {
          fontCharCode = unicode.charCodeAt(0);
        }
      }
      // Try to move control characters, special characters and already mapped
      // characters to the private use area since they will not be drawn by
      // canvas if left in their current position. Also, move characters if the
      // font was symbolic and there is only an identity unicode map since the
      // characters probably aren't in the correct position (fixes an issue
      // with firefox and thuluthfont).
      if ((usedFontCharCodes[fontCharCode] !== undefined ||
           isProblematicUnicodeLocation(fontCharCode) ||
           (isSymbolic && isIdentityUnicode)) &&
          nextAvailableFontCharCode <= PRIVATE_USE_OFFSET_END) { // Room left.
        // Loop to try and find a free spot in the private use area.
        do {
          fontCharCode = nextAvailableFontCharCode++;

          if (SKIP_PRIVATE_USE_RANGE_F000_TO_F01F && fontCharCode === 0xF000) {
            fontCharCode = 0xF020;
            nextAvailableFontCharCode = fontCharCode + 1;
          }

        } while (usedFontCharCodes[fontCharCode] !== undefined &&
                 nextAvailableFontCharCode <= PRIVATE_USE_OFFSET_END);
      }

      newMap[fontCharCode] = glyphId;
      toFontChar[originalCharCode] = fontCharCode;
      usedFontCharCodes[fontCharCode] = true;
    }
    return {
      toFontChar: toFontChar,
      charCodeToGlyphId: newMap,
      nextAvailableFontCharCode: nextAvailableFontCharCode
    };
  }

  function getRanges(glyphs) {
    // Array.sort() sorts by characters, not numerically, so convert to an
    // array of characters.
    var codes = [];
    for (var charCode in glyphs) {
      codes.push({ fontCharCode: charCode | 0, glyphId: glyphs[charCode] });
    }
    codes.sort(function fontGetRangesSort(a, b) {
      return a.fontCharCode - b.fontCharCode;
    });

    // Split the sorted codes into ranges.
    var ranges = [];
    var length = codes.length;
    for (var n = 0; n < length; ) {
      var start = codes[n].fontCharCode;
      var codeIndices = [codes[n].glyphId];
      ++n;
      var end = start;
      while (n < length && end + 1 === codes[n].fontCharCode) {
        codeIndices.push(codes[n].glyphId);
        ++end;
        ++n;
        if (end === 0xFFFF) {
          break;
        }
      }
      ranges.push([start, end, codeIndices]);
    }

    return ranges;
  }

  function createCmapTable(glyphs) {
    var ranges = getRanges(glyphs);
    var numTables = ranges[ranges.length - 1][1] > 0xFFFF ? 2 : 1;
    var cmap = '\x00\x00' + // version
               string16(numTables) +  // numTables
               '\x00\x03' + // platformID
               '\x00\x01' + // encodingID
               string32(4 + numTables * 8); // start of the table record

    var i, ii, j, jj;
    for (i = ranges.length - 1; i >= 0; --i) {
      if (ranges[i][0] <= 0xFFFF) { break; }
    }
    var bmpLength = i + 1;

    if (ranges[i][0] < 0xFFFF && ranges[i][1] === 0xFFFF) {
      ranges[i][1] = 0xFFFE;
    }
    var trailingRangesCount = ranges[i][1] < 0xFFFF ? 1 : 0;
    var segCount = bmpLength + trailingRangesCount;
    var searchParams = OpenTypeFileBuilder.getSearchParams(segCount, 2);

    // Fill up the 4 parallel arrays describing the segments.
    var startCount = '';
    var endCount = '';
    var idDeltas = '';
    var idRangeOffsets = '';
    var glyphsIds = '';
    var bias = 0;

    var range, start, end, codes;
    for (i = 0, ii = bmpLength; i < ii; i++) {
      range = ranges[i];
      start = range[0];
      end = range[1];
      startCount += string16(start);
      endCount += string16(end);
      codes = range[2];
      var contiguous = true;
      for (j = 1, jj = codes.length; j < jj; ++j) {
        if (codes[j] !== codes[j - 1] + 1) {
          contiguous = false;
          break;
        }
      }
      if (!contiguous) {
        var offset = (segCount - i) * 2 + bias * 2;
        bias += (end - start + 1);

        idDeltas += string16(0);
        idRangeOffsets += string16(offset);

        for (j = 0, jj = codes.length; j < jj; ++j) {
          glyphsIds += string16(codes[j]);
        }
      } else {
        var startCode = codes[0];

        idDeltas += string16((startCode - start) & 0xFFFF);
        idRangeOffsets += string16(0);
      }
    }

    if (trailingRangesCount > 0) {
      endCount += '\xFF\xFF';
      startCount += '\xFF\xFF';
      idDeltas += '\x00\x01';
      idRangeOffsets += '\x00\x00';
    }

    var format314 = '\x00\x00' + // language
                    string16(2 * segCount) +
                    string16(searchParams.range) +
                    string16(searchParams.entry) +
                    string16(searchParams.rangeShift) +
                    endCount + '\x00\x00' + startCount +
                    idDeltas + idRangeOffsets + glyphsIds;

    var format31012 = '';
    var header31012 = '';
    if (numTables > 1) {
      cmap += '\x00\x03' + // platformID
              '\x00\x0A' + // encodingID
              string32(4 + numTables * 8 +
                       4 + format314.length); // start of the table record
      format31012 = '';
      for (i = 0, ii = ranges.length; i < ii; i++) {
        range = ranges[i];
        start = range[0];
        codes = range[2];
        var code = codes[0];
        for (j = 1, jj = codes.length; j < jj; ++j) {
          if (codes[j] !== codes[j - 1] + 1) {
            end = range[0] + j - 1;
            format31012 += string32(start) + // startCharCode
                           string32(end) + // endCharCode
                           string32(code); // startGlyphID
            start = end + 1;
            code = codes[j];
          }
        }
        format31012 += string32(start) + // startCharCode
                       string32(range[1]) + // endCharCode
                       string32(code); // startGlyphID
      }
      header31012 = '\x00\x0C' + // format
                    '\x00\x00' + // reserved
                    string32(format31012.length + 16) + // length
                    '\x00\x00\x00\x00' + // language
                    string32(format31012.length / 12); // nGroups
    }

    return cmap + '\x00\x04' + // format
                  string16(format314.length + 4) + // length
                  format314 + header31012 + format31012;
  }

  function validateOS2Table(os2) {
    var stream = new Stream(os2.data);
    var version = stream.getUint16();
    // TODO verify all OS/2 tables fields, but currently we validate only those
    // that give us issues
    stream.getBytes(60); // skipping type, misc sizes, panose, unicode ranges
    var selection = stream.getUint16();
    if (version < 4 && (selection & 0x0300)) {
      return false;
    }
    var firstChar = stream.getUint16();
    var lastChar = stream.getUint16();
    if (firstChar > lastChar) {
      return false;
    }
    stream.getBytes(6); // skipping sTypoAscender/Descender/LineGap
    var usWinAscent = stream.getUint16();
    if (usWinAscent === 0) { // makes font unreadable by windows
      return false;
    }

    // OS/2 appears to be valid, resetting some fields
    os2.data[8] = os2.data[9] = 0; // IE rejects fonts if fsType != 0
    return true;
  }

  function createOS2Table(properties, charstrings, override) {
    override = override || {
      unitsPerEm: 0,
      yMax: 0,
      yMin: 0,
      ascent: 0,
      descent: 0
    };

    var ulUnicodeRange1 = 0;
    var ulUnicodeRange2 = 0;
    var ulUnicodeRange3 = 0;
    var ulUnicodeRange4 = 0;

    var firstCharIndex = null;
    var lastCharIndex = 0;

    if (charstrings) {
      for (var code in charstrings) {
        code |= 0;
        if (firstCharIndex > code || !firstCharIndex) {
          firstCharIndex = code;
        }
        if (lastCharIndex < code) {
          lastCharIndex = code;
        }

        var position = getUnicodeRangeFor(code);
        if (position < 32) {
          ulUnicodeRange1 |= 1 << position;
        } else if (position < 64) {
          ulUnicodeRange2 |= 1 << position - 32;
        } else if (position < 96) {
          ulUnicodeRange3 |= 1 << position - 64;
        } else if (position < 123) {
          ulUnicodeRange4 |= 1 << position - 96;
        } else {
          error('Unicode ranges Bits > 123 are reserved for internal usage');
        }
      }
    } else {
      // TODO
      firstCharIndex = 0;
      lastCharIndex = 255;
    }

    var bbox = properties.bbox || [0, 0, 0, 0];
    var unitsPerEm = (override.unitsPerEm ||
                      1 / (properties.fontMatrix || FONT_IDENTITY_MATRIX)[0]);

    // if the font units differ to the PDF glyph space units
    // then scale up the values
    var scale = (properties.ascentScaled ? 1.0 :
                 unitsPerEm / PDF_GLYPH_SPACE_UNITS);

    var typoAscent = (override.ascent ||
                      Math.round(scale * (properties.ascent || bbox[3])));
    var typoDescent = (override.descent ||
                       Math.round(scale * (properties.descent || bbox[1])));
    if (typoDescent > 0 && properties.descent > 0 && bbox[1] < 0) {
      typoDescent = -typoDescent; // fixing incorrect descent
    }
    var winAscent = override.yMax || typoAscent;
    var winDescent = -override.yMin || -typoDescent;

    return '\x00\x03' + // version
           '\x02\x24' + // xAvgCharWidth
           '\x01\xF4' + // usWeightClass
           '\x00\x05' + // usWidthClass
           '\x00\x00' + // fstype (0 to let the font loads via font-face on IE)
           '\x02\x8A' + // ySubscriptXSize
           '\x02\xBB' + // ySubscriptYSize
           '\x00\x00' + // ySubscriptXOffset
           '\x00\x8C' + // ySubscriptYOffset
           '\x02\x8A' + // ySuperScriptXSize
           '\x02\xBB' + // ySuperScriptYSize
           '\x00\x00' + // ySuperScriptXOffset
           '\x01\xDF' + // ySuperScriptYOffset
           '\x00\x31' + // yStrikeOutSize
           '\x01\x02' + // yStrikeOutPosition
           '\x00\x00' + // sFamilyClass
           '\x00\x00\x06' +
           String.fromCharCode(properties.fixedPitch ? 0x09 : 0x00) +
           '\x00\x00\x00\x00\x00\x00' + // Panose
           string32(ulUnicodeRange1) + // ulUnicodeRange1 (Bits 0-31)
           string32(ulUnicodeRange2) + // ulUnicodeRange2 (Bits 32-63)
           string32(ulUnicodeRange3) + // ulUnicodeRange3 (Bits 64-95)
           string32(ulUnicodeRange4) + // ulUnicodeRange4 (Bits 96-127)
           '\x2A\x32\x31\x2A' + // achVendID
           string16(properties.italicAngle ? 1 : 0) + // fsSelection
           string16(firstCharIndex ||
                    properties.firstChar) + // usFirstCharIndex
           string16(lastCharIndex || properties.lastChar) +  // usLastCharIndex
           string16(typoAscent) + // sTypoAscender
           string16(typoDescent) + // sTypoDescender
           '\x00\x64' + // sTypoLineGap (7%-10% of the unitsPerEM value)
           string16(winAscent) + // usWinAscent
           string16(winDescent) + // usWinDescent
           '\x00\x00\x00\x00' + // ulCodePageRange1 (Bits 0-31)
           '\x00\x00\x00\x00' + // ulCodePageRange2 (Bits 32-63)
           string16(properties.xHeight) + // sxHeight
           string16(properties.capHeight) + // sCapHeight
           string16(0) + // usDefaultChar
           string16(firstCharIndex || properties.firstChar) + // usBreakChar
           '\x00\x03';  // usMaxContext
  }

  function createPostTable(properties) {
    var angle = Math.floor(properties.italicAngle * (Math.pow(2, 16)));
    return ('\x00\x03\x00\x00' + // Version number
            string32(angle) + // italicAngle
            '\x00\x00' + // underlinePosition
            '\x00\x00' + // underlineThickness
            string32(properties.fixedPitch) + // isFixedPitch
            '\x00\x00\x00\x00' + // minMemType42
            '\x00\x00\x00\x00' + // maxMemType42
            '\x00\x00\x00\x00' + // minMemType1
            '\x00\x00\x00\x00');  // maxMemType1
  }

  function createNameTable(name, proto) {
    if (!proto) {
      proto = [[], []]; // no strings and unicode strings
    }

    var strings = [
      proto[0][0] || 'Original licence',  // 0.Copyright
      proto[0][1] || name,                // 1.Font family
      proto[0][2] || 'Unknown',           // 2.Font subfamily (font weight)
      proto[0][3] || 'uniqueID',          // 3.Unique ID
      proto[0][4] || name,                // 4.Full font name
      proto[0][5] || 'Version 0.11',      // 5.Version
      proto[0][6] || '',                  // 6.Postscript name
      proto[0][7] || 'Unknown',           // 7.Trademark
      proto[0][8] || 'Unknown',           // 8.Manufacturer
      proto[0][9] || 'Unknown'            // 9.Designer
    ];

    // Mac want 1-byte per character strings while Windows want
    // 2-bytes per character, so duplicate the names table
    var stringsUnicode = [];
    var i, ii, j, jj, str;
    for (i = 0, ii = strings.length; i < ii; i++) {
      str = proto[1][i] || strings[i];

      var strBufUnicode = [];
      for (j = 0, jj = str.length; j < jj; j++) {
        strBufUnicode.push(string16(str.charCodeAt(j)));
      }
      stringsUnicode.push(strBufUnicode.join(''));
    }

    var names = [strings, stringsUnicode];
    var platforms = ['\x00\x01', '\x00\x03'];
    var encodings = ['\x00\x00', '\x00\x01'];
    var languages = ['\x00\x00', '\x04\x09'];

    var namesRecordCount = strings.length * platforms.length;
    var nameTable =
      '\x00\x00' +                           // format
      string16(namesRecordCount) +           // Number of names Record
      string16(namesRecordCount * 12 + 6);   // Storage

    // Build the name records field
    var strOffset = 0;
    for (i = 0, ii = platforms.length; i < ii; i++) {
      var strs = names[i];
      for (j = 0, jj = strs.length; j < jj; j++) {
        str = strs[j];
        var nameRecord =
          platforms[i] + // platform ID
          encodings[i] + // encoding ID
          languages[i] + // language ID
          string16(j) + // name ID
          string16(str.length) +
          string16(strOffset);
        nameTable += nameRecord;
        strOffset += str.length;
      }
    }

    nameTable += strings.join('') + stringsUnicode.join('');
    return nameTable;
  }

  Font.prototype = {
    name: null,
    font: null,
    mimetype: null,
    encoding: null,
    get renderer() {
      var renderer = FontRendererFactory.create(this);
      return shadow(this, 'renderer', renderer);
    },

    exportData: function Font_exportData() {
      var data = {};
      for (var i in this) {
        if (this.hasOwnProperty(i)) {
          data[i] = this[i];
        }
      }
      return data;
    },

    checkAndRepair: function Font_checkAndRepair(name, font, properties) {
      function readTableEntry(file) {
        var tag = bytesToString(file.getBytes(4));

        var checksum = file.getInt32();
        var offset = file.getInt32() >>> 0;
        var length = file.getInt32() >>> 0;

        // Read the table associated data
        var previousPosition = file.pos;
        file.pos = file.start ? file.start : 0;
        file.skip(offset);
        var data = file.getBytes(length);
        file.pos = previousPosition;

        if (tag === 'head') {
          // clearing checksum adjustment
          data[8] = data[9] = data[10] = data[11] = 0;
          data[17] |= 0x20; //Set font optimized for cleartype flag
        }

        return {
          tag: tag,
          checksum: checksum,
          length: length,
          offset: offset,
          data: data
        };
      }

      function readOpenTypeHeader(ttf) {
        return {
          version: bytesToString(ttf.getBytes(4)),
          numTables: ttf.getUint16(),
          searchRange: ttf.getUint16(),
          entrySelector: ttf.getUint16(),
          rangeShift: ttf.getUint16()
        };
      }

      /**
       * Read the appropriate subtable from the cmap according to 9.6.6.4 from
       * PDF spec
       */
      function readCmapTable(cmap, font, isSymbolicFont) {
        var segment;
        var start = (font.start ? font.start : 0) + cmap.offset;
        font.pos = start;

        var version = font.getUint16();
        var numTables = font.getUint16();

        var potentialTable;
        var canBreak = false;
        // There's an order of preference in terms of which cmap subtable to
        // use:
        // - non-symbolic fonts the preference is a 3,1 table then a 1,0 table
        // - symbolic fonts the preference is a 3,0 table then a 1,0 table
        // The following takes advantage of the fact that the tables are sorted
        // to work.
        for (var i = 0; i < numTables; i++) {
          var platformId = font.getUint16();
          var encodingId = font.getUint16();
          var offset = font.getInt32() >>> 0;
          var useTable = false;

          if (platformId === 0 && encodingId === 0) {
            useTable = true;
            // Continue the loop since there still may be a higher priority
            // table.
          } else if (platformId === 1 && encodingId === 0) {
            useTable = true;
            // Continue the loop since there still may be a higher priority
            // table.
          } else if (platformId === 3 && encodingId === 1 &&
                     (!isSymbolicFont || !potentialTable)) {
            useTable = true;
            if (!isSymbolicFont) {
              canBreak = true;
            }
          } else if (isSymbolicFont && platformId === 3 && encodingId === 0) {
            useTable = true;
            canBreak = true;
          }

          if (useTable) {
            potentialTable = {
              platformId: platformId,
              encodingId: encodingId,
              offset: offset
            };
          }
          if (canBreak) {
            break;
          }
        }

        if (!potentialTable) {
          warn('Could not find a preferred cmap table.');
          return {
            platformId: -1,
            encodingId: -1,
            mappings: [],
            hasShortCmap: false
          };
        }

        font.pos = start + potentialTable.offset;
        var format = font.getUint16();
        var length = font.getUint16();
        var language = font.getUint16();

        var hasShortCmap = false;
        var mappings = [];
        var j, glyphId;

        // TODO(mack): refactor this cmap subtable reading logic out
        if (format === 0) {
          for (j = 0; j < 256; j++) {
            var index = font.getByte();
            if (!index) {
              continue;
            }
            mappings.push({
              charCode: j,
              glyphId: index
            });
          }
          hasShortCmap = true;
        } else if (format === 4) {
          // re-creating the table in format 4 since the encoding
          // might be changed
          var segCount = (font.getUint16() >> 1);
          font.getBytes(6); // skipping range fields
          var segIndex, segments = [];
          for (segIndex = 0; segIndex < segCount; segIndex++) {
            segments.push({ end: font.getUint16() });
          }
          font.getUint16();
          for (segIndex = 0; segIndex < segCount; segIndex++) {
            segments[segIndex].start = font.getUint16();
          }

          for (segIndex = 0; segIndex < segCount; segIndex++) {
            segments[segIndex].delta = font.getUint16();
          }

          var offsetsCount = 0;
          for (segIndex = 0; segIndex < segCount; segIndex++) {
            segment = segments[segIndex];
            var rangeOffset = font.getUint16();
            if (!rangeOffset) {
              segment.offsetIndex = -1;
              continue;
            }

            var offsetIndex = (rangeOffset >> 1) - (segCount - segIndex);
            segment.offsetIndex = offsetIndex;
            offsetsCount = Math.max(offsetsCount, offsetIndex +
                                    segment.end - segment.start + 1);
          }

          var offsets = [];
          for (j = 0; j < offsetsCount; j++) {
            offsets.push(font.getUint16());
          }

          for (segIndex = 0; segIndex < segCount; segIndex++) {
            segment = segments[segIndex];
            start = segment.start;
            var end = segment.end;
            var delta = segment.delta;
            offsetIndex = segment.offsetIndex;

            for (j = start; j <= end; j++) {
              if (j === 0xFFFF) {
                continue;
              }

              glyphId = (offsetIndex < 0 ?
                         j : offsets[offsetIndex + j - start]);
              glyphId = (glyphId + delta) & 0xFFFF;
              if (glyphId === 0) {
                continue;
              }
              mappings.push({
                charCode: j,
                glyphId: glyphId
              });
            }
          }
        } else if (format === 6) {
          // Format 6 is a 2-bytes dense mapping, which means the font data
          // lives glue together even if they are pretty far in the unicode
          // table. (This looks weird, so I can have missed something), this
          // works on Linux but seems to fails on Mac so let's rewrite the
          // cmap table to a 3-1-4 style
          var firstCode = font.getUint16();
          var entryCount = font.getUint16();

          for (j = 0; j < entryCount; j++) {
            glyphId = font.getUint16();
            var charCode = firstCode + j;

            mappings.push({
              charCode: charCode,
              glyphId: glyphId
            });
          }
        } else {
          error('cmap table has unsupported format: ' + format);
        }

        // removing duplicate entries
        mappings.sort(function (a, b) {
          return a.charCode - b.charCode;
        });
        for (i = 1; i < mappings.length; i++) {
          if (mappings[i - 1].charCode === mappings[i].charCode) {
            mappings.splice(i, 1);
            i--;
          }
        }

        return {
          platformId: potentialTable.platformId,
          encodingId: potentialTable.encodingId,
          mappings: mappings,
          hasShortCmap: hasShortCmap
        };
      }

      function sanitizeMetrics(font, header, metrics, numGlyphs) {
        if (!header) {
          if (metrics) {
            metrics.data = null;
          }
          return;
        }

        font.pos = (font.start ? font.start : 0) + header.offset;
        font.pos += header.length - 2;
        var numOfMetrics = font.getUint16();

        if (numOfMetrics > numGlyphs) {
          info('The numOfMetrics (' + numOfMetrics + ') should not be ' +
               'greater than the numGlyphs (' + numGlyphs + ')');
          // Reduce numOfMetrics if it is greater than numGlyphs
          numOfMetrics = numGlyphs;
          header.data[34] = (numOfMetrics & 0xff00) >> 8;
          header.data[35] = numOfMetrics & 0x00ff;
        }

        var numOfSidebearings = numGlyphs - numOfMetrics;
        var numMissing = numOfSidebearings -
          ((metrics.length - numOfMetrics * 4) >> 1);

        if (numMissing > 0) {
          // For each missing glyph, we set both the width and lsb to 0 (zero).
          // Since we need to add two properties for each glyph, this explains
          // the use of |numMissing * 2| when initializing the typed array.
          var entries = new Uint8Array(metrics.length + numMissing * 2);
          entries.set(metrics.data);
          metrics.data = entries;
        }
      }

      function sanitizeGlyph(source, sourceStart, sourceEnd, dest, destStart,
                             hintsValid) {
        if (sourceEnd - sourceStart <= 12) {
          // glyph with data less than 12 is invalid one
          return 0;
        }
        var glyf = source.subarray(sourceStart, sourceEnd);
        var contoursCount = (glyf[0] << 8) | glyf[1];
        if (contoursCount & 0x8000) {
          // complex glyph, writing as is
          dest.set(glyf, destStart);
          return glyf.length;
        }

        var i, j = 10, flagsCount = 0;
        for (i = 0; i < contoursCount; i++) {
          var endPoint = (glyf[j] << 8) | glyf[j + 1];
          flagsCount = endPoint + 1;
          j += 2;
        }
        // skipping instructions
        var instructionsStart = j;
        var instructionsLength = (glyf[j] << 8) | glyf[j + 1];
        j += 2 + instructionsLength;
        var instructionsEnd = j;
        // validating flags
        var coordinatesLength = 0;
        for (i = 0; i < flagsCount; i++) {
          var flag = glyf[j++];
          if (flag & 0xC0) {
            // reserved flags must be zero, cleaning up
            glyf[j - 1] = flag & 0x3F;
          }
          var xyLength = ((flag & 2) ? 1 : (flag & 16) ? 0 : 2) +
                         ((flag & 4) ? 1 : (flag & 32) ? 0 : 2);
          coordinatesLength += xyLength;
          if (flag & 8) {
            var repeat = glyf[j++];
            i += repeat;
            coordinatesLength += repeat * xyLength;
          }
        }
        // glyph without coordinates will be rejected
        if (coordinatesLength === 0) {
          return 0;
        }
        var glyphDataLength = j + coordinatesLength;
        if (glyphDataLength > glyf.length) {
          // not enough data for coordinates
          return 0;
        }
        if (!hintsValid && instructionsLength > 0) {
          dest.set(glyf.subarray(0, instructionsStart), destStart);
          dest.set([0, 0], destStart + instructionsStart);
          dest.set(glyf.subarray(instructionsEnd, glyphDataLength),
                   destStart + instructionsStart + 2);
          glyphDataLength -= instructionsLength;
          if (glyf.length - glyphDataLength > 3) {
            glyphDataLength = (glyphDataLength + 3) & ~3;
          }
          return glyphDataLength;
        }
        if (glyf.length - glyphDataLength > 3) {
          // truncating and aligning to 4 bytes the long glyph data
          glyphDataLength = (glyphDataLength + 3) & ~3;
          dest.set(glyf.subarray(0, glyphDataLength), destStart);
          return glyphDataLength;
        }
        // glyph data is fine
        dest.set(glyf, destStart);
        return glyf.length;
      }

      function sanitizeHead(head, numGlyphs, locaLength) {
        var data = head.data;

        // Validate version:
        // Should always be 0x00010000
        var version = int32(data[0], data[1], data[2], data[3]);
        if (version >> 16 !== 1) {
          info('Attempting to fix invalid version in head table: ' + version);
          data[0] = 0;
          data[1] = 1;
          data[2] = 0;
          data[3] = 0;
        }

        var indexToLocFormat = int16(data[50], data[51]);
        if (indexToLocFormat < 0 || indexToLocFormat > 1) {
          info('Attempting to fix invalid indexToLocFormat in head table: ' +
               indexToLocFormat);

          // The value of indexToLocFormat should be 0 if the loca table
          // consists of short offsets, and should be 1 if the loca table
          // consists of long offsets.
          //
          // The number of entries in the loca table should be numGlyphs + 1.
          //
          // Using this information, we can work backwards to deduce if the
          // size of each offset in the loca table, and thus figure out the
          // appropriate value for indexToLocFormat.

          var numGlyphsPlusOne = numGlyphs + 1;
          if (locaLength === numGlyphsPlusOne << 1) {
            // 0x0000 indicates the loca table consists of short offsets
            data[50] = 0;
            data[51] = 0;
          } else if (locaLength === numGlyphsPlusOne << 2) {
            // 0x0001 indicates the loca table consists of long offsets
            data[50] = 0;
            data[51] = 1;
          } else {
            warn('Could not fix indexToLocFormat: ' + indexToLocFormat);
          }
        }
      }

      function sanitizeGlyphLocations(loca, glyf, numGlyphs,
                                      isGlyphLocationsLong, hintsValid,
                                      dupFirstEntry) {
        var itemSize, itemDecode, itemEncode;
        if (isGlyphLocationsLong) {
          itemSize = 4;
          itemDecode = function fontItemDecodeLong(data, offset) {
            return (data[offset] << 24) | (data[offset + 1] << 16) |
                   (data[offset + 2] << 8) | data[offset + 3];
          };
          itemEncode = function fontItemEncodeLong(data, offset, value) {
            data[offset] = (value >>> 24) & 0xFF;
            data[offset + 1] = (value >> 16) & 0xFF;
            data[offset + 2] = (value >> 8) & 0xFF;
            data[offset + 3] = value & 0xFF;
          };
        } else {
          itemSize = 2;
          itemDecode = function fontItemDecode(data, offset) {
            return (data[offset] << 9) | (data[offset + 1] << 1);
          };
          itemEncode = function fontItemEncode(data, offset, value) {
            data[offset] = (value >> 9) & 0xFF;
            data[offset + 1] = (value >> 1) & 0xFF;
          };
        }
        var locaData = loca.data;
        var locaDataSize = itemSize * (1 + numGlyphs);
        // is loca.data too short or long?
        if (locaData.length !== locaDataSize) {
          locaData = new Uint8Array(locaDataSize);
          locaData.set(loca.data.subarray(0, locaDataSize));
          loca.data = locaData;
        }
        // removing the invalid glyphs
        var oldGlyfData = glyf.data;
        var oldGlyfDataLength = oldGlyfData.length;
        var newGlyfData = new Uint8Array(oldGlyfDataLength);
        var startOffset = itemDecode(locaData, 0);
        var writeOffset = 0;
        var missingGlyphData = {};
        itemEncode(locaData, 0, writeOffset);
        var i, j;
        for (i = 0, j = itemSize; i < numGlyphs; i++, j += itemSize) {
          var endOffset = itemDecode(locaData, j);
          if (endOffset > oldGlyfDataLength &&
              ((oldGlyfDataLength + 3) & ~3) === endOffset) {
            // Aspose breaks fonts by aligning the glyphs to the qword, but not
            // the glyf table size, which makes last glyph out of range.
            endOffset = oldGlyfDataLength;
          }
          if (endOffset > oldGlyfDataLength) {
            // glyph end offset points outside glyf data, rejecting the glyph
            itemEncode(locaData, j, writeOffset);
            startOffset = endOffset;
            continue;
          }

          if (startOffset === endOffset) {
            missingGlyphData[i] = true;
          }

          var newLength = sanitizeGlyph(oldGlyfData, startOffset, endOffset,
                                        newGlyfData, writeOffset, hintsValid);
          writeOffset += newLength;
          itemEncode(locaData, j, writeOffset);
          startOffset = endOffset;
        }

        if (writeOffset === 0) {
          // glyf table cannot be empty -- redoing the glyf and loca tables
          // to have single glyph with one point
          var simpleGlyph = new Uint8Array(
            [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 49, 0]);
          for (i = 0, j = itemSize; i < numGlyphs; i++, j += itemSize) {
            itemEncode(locaData, j, simpleGlyph.length);
          }
          glyf.data = simpleGlyph;
          return missingGlyphData;
        }

        if (dupFirstEntry) {
          var firstEntryLength = itemDecode(locaData, itemSize);
          if (newGlyfData.length > firstEntryLength + writeOffset) {
            glyf.data = newGlyfData.subarray(0, firstEntryLength + writeOffset);
          } else {
            glyf.data = new Uint8Array(firstEntryLength + writeOffset);
            glyf.data.set(newGlyfData.subarray(0, writeOffset));
          }
          glyf.data.set(newGlyfData.subarray(0, firstEntryLength), writeOffset);
          itemEncode(loca.data, locaData.length - itemSize,
                     writeOffset + firstEntryLength);
        } else {
          glyf.data = newGlyfData.subarray(0, writeOffset);
        }
        return missingGlyphData;
      }

      function readPostScriptTable(post, properties, maxpNumGlyphs) {
        var start = (font.start ? font.start : 0) + post.offset;
        font.pos = start;

        var length = post.length, end = start + length;
        var version = font.getInt32();
        // skip rest to the tables
        font.getBytes(28);

        var glyphNames;
        var valid = true;
        var i;

        switch (version) {
          case 0x00010000:
            glyphNames = MacStandardGlyphOrdering;
            break;
          case 0x00020000:
            var numGlyphs = font.getUint16();
            if (numGlyphs !== maxpNumGlyphs) {
              valid = false;
              break;
            }
            var glyphNameIndexes = [];
            for (i = 0; i < numGlyphs; ++i) {
              var index = font.getUint16();
              if (index >= 32768) {
                valid = false;
                break;
              }
              glyphNameIndexes.push(index);
            }
            if (!valid) {
              break;
            }
            var customNames = [];
            var strBuf = [];
            while (font.pos < end) {
              var stringLength = font.getByte();
              strBuf.length = stringLength;
              for (i = 0; i < stringLength; ++i) {
                strBuf[i] = String.fromCharCode(font.getByte());
              }
              customNames.push(strBuf.join(''));
            }
            glyphNames = [];
            for (i = 0; i < numGlyphs; ++i) {
              var j = glyphNameIndexes[i];
              if (j < 258) {
                glyphNames.push(MacStandardGlyphOrdering[j]);
                continue;
              }
              glyphNames.push(customNames[j - 258]);
            }
            break;
          case 0x00030000:
            break;
          default:
            warn('Unknown/unsupported post table version ' + version);
            valid = false;
            break;
        }
        properties.glyphNames = glyphNames;
        return valid;
      }

      function readNameTable(nameTable) {
        var start = (font.start ? font.start : 0) + nameTable.offset;
        font.pos = start;

        var names = [[], []];
        var length = nameTable.length, end = start + length;
        var format = font.getUint16();
        var FORMAT_0_HEADER_LENGTH = 6;
        if (format !== 0 || length < FORMAT_0_HEADER_LENGTH) {
          // unsupported name table format or table "too" small
          return names;
        }
        var numRecords = font.getUint16();
        var stringsStart = font.getUint16();
        var records = [];
        var NAME_RECORD_LENGTH = 12;
        var i, ii;

        for (i = 0; i < numRecords &&
                        font.pos + NAME_RECORD_LENGTH <= end; i++) {
          var r = {
            platform: font.getUint16(),
            encoding: font.getUint16(),
            language: font.getUint16(),
            name: font.getUint16(),
            length: font.getUint16(),
            offset: font.getUint16()
          };
          // using only Macintosh and Windows platform/encoding names
          if ((r.platform === 1 && r.encoding === 0 && r.language === 0) ||
              (r.platform === 3 && r.encoding === 1 && r.language === 0x409)) {
            records.push(r);
          }
        }
        for (i = 0, ii = records.length; i < ii; i++) {
          var record = records[i];
          var pos = start + stringsStart + record.offset;
          if (pos + record.length > end) {
            continue; // outside of name table, ignoring
          }
          font.pos = pos;
          var nameIndex = record.name;
          if (record.encoding) {
            // unicode
            var str = '';
            for (var j = 0, jj = record.length; j < jj; j += 2) {
              str += String.fromCharCode(font.getUint16());
            }
            names[1][nameIndex] = str;
          } else {
            names[0][nameIndex] = bytesToString(font.getBytes(record.length));
          }
        }
        return names;
      }

      var TTOpsStackDeltas = [
        0, 0, 0, 0, 0, 0, 0, 0, -2, -2, -2, -2, 0, 0, -2, -5,
        -1, -1, -1, -1, -1, -1, -1, -1, 0, 0, -1, 0, -1, -1, -1, -1,
        1, -1, -999, 0, 1, 0, -1, -2, 0, -1, -2, -1, -1, 0, -1, -1,
        0, 0, -999, -999, -1, -1, -1, -1, -2, -999, -2, -2, -999, 0, -2, -2,
        0, 0, -2, 0, -2, 0, 0, 0, -2, -1, -1, 1, 1, 0, 0, -1,
        -1, -1, -1, -1, -1, -1, 0, 0, -1, 0, -1, -1, 0, -999, -1, -1,
        -1, -1, -1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        -2, -999, -999, -999, -999, -999, -1, -1, -2, -2, 0, 0, 0, 0, -1, -1,
        -999, -2, -2, 0, 0, -1, -2, -2, 0, 0, 0, -1, -1, -1, -2];
        // 0xC0-DF == -1 and 0xE0-FF == -2

      function sanitizeTTProgram(table, ttContext) {
        var data = table.data;
        var i = 0, j, n, b, funcId, pc, lastEndf = 0, lastDeff = 0;
        var stack = [];
        var callstack = [];
        var functionsCalled = [];
        var tooComplexToFollowFunctions =
          ttContext.tooComplexToFollowFunctions;
        var inFDEF = false, ifLevel = 0, inELSE = 0;
        for (var ii = data.length; i < ii;) {
          var op = data[i++];
          // The TrueType instruction set docs can be found at
          // https://developer.apple.com/fonts/TTRefMan/RM05/Chap5.html
          if (op === 0x40) { // NPUSHB - pushes n bytes
            n = data[i++];
            if (inFDEF || inELSE) {
              i += n;
            } else {
              for (j = 0; j < n; j++) {
                stack.push(data[i++]);
              }
            }
          } else if (op === 0x41) { // NPUSHW - pushes n words
            n = data[i++];
            if (inFDEF || inELSE) {
              i += n * 2;
            } else {
              for (j = 0; j < n; j++) {
                b = data[i++];
                stack.push((b << 8) | data[i++]);
              }
            }
          } else if ((op & 0xF8) === 0xB0) { // PUSHB - pushes bytes
            n = op - 0xB0 + 1;
            if (inFDEF || inELSE) {
              i += n;
            } else {
              for (j = 0; j < n; j++) {
                stack.push(data[i++]);
              }
            }
          } else if ((op & 0xF8) === 0xB8) { // PUSHW - pushes words
            n = op - 0xB8 + 1;
            if (inFDEF || inELSE) {
              i += n * 2;
            } else {
              for (j = 0; j < n; j++) {
                b = data[i++];
                stack.push((b << 8) | data[i++]);
              }
            }
          } else if (op === 0x2B && !tooComplexToFollowFunctions) { // CALL
            if (!inFDEF && !inELSE) {
              // collecting inforamtion about which functions are used
              funcId = stack[stack.length - 1];
              ttContext.functionsUsed[funcId] = true;
              if (funcId in ttContext.functionsStackDeltas) {
                stack.length += ttContext.functionsStackDeltas[funcId];
              } else if (funcId in ttContext.functionsDefined &&
                         functionsCalled.indexOf(funcId) < 0) {
                callstack.push({data: data, i: i, stackTop: stack.length - 1});
                functionsCalled.push(funcId);
                pc = ttContext.functionsDefined[funcId];
                if (!pc) {
                  warn('TT: CALL non-existent function');
                  ttContext.hintsValid = false;
                  return;
                }
                data = pc.data;
                i = pc.i;
              }
            }
          } else if (op === 0x2C && !tooComplexToFollowFunctions) { // FDEF
            if (inFDEF || inELSE) {
              warn('TT: nested FDEFs not allowed');
              tooComplexToFollowFunctions = true;
            }
            inFDEF = true;
            // collecting inforamtion about which functions are defined
            lastDeff = i;
            funcId = stack.pop();
            ttContext.functionsDefined[funcId] = {data: data, i: i};
          } else if (op === 0x2D) { // ENDF - end of function
            if (inFDEF) {
              inFDEF = false;
              lastEndf = i;
            } else {
              pc = callstack.pop();
              if (!pc) {
                warn('TT: ENDF bad stack');
                ttContext.hintsValid = false;
                return;
              }
              funcId = functionsCalled.pop();
              data = pc.data;
              i = pc.i;
              ttContext.functionsStackDeltas[funcId] =
                stack.length - pc.stackTop;
            }
          } else if (op === 0x89) { // IDEF - instruction definition
            if (inFDEF || inELSE) {
              warn('TT: nested IDEFs not allowed');
              tooComplexToFollowFunctions = true;
            }
            inFDEF = true;
            // recording it as a function to track ENDF
            lastDeff = i;
          } else if (op === 0x58) { // IF
            ++ifLevel;
          } else if (op === 0x1B) { // ELSE
            inELSE = ifLevel;
          } else if (op === 0x59) { // EIF
            if (inELSE === ifLevel) {
              inELSE = 0;
            }
            --ifLevel;
          } else if (op === 0x1C) { // JMPR
            if (!inFDEF && !inELSE) {
              var offset = stack[stack.length - 1];
              // only jumping forward to prevent infinite loop
              if (offset > 0) {
                i += offset - 1;
              }
            }
          }
          // Adjusting stack not extactly, but just enough to get function id
          if (!inFDEF && !inELSE) {
            var stackDelta = op <= 0x8E ? TTOpsStackDeltas[op] :
              op >= 0xC0 && op <= 0xDF ? -1 : op >= 0xE0 ? -2 : 0;
            if (op >= 0x71 && op <= 0x75) {
              n = stack.pop();
              if (n === n) {
                stackDelta = -n * 2;
              }
            }
            while (stackDelta < 0 && stack.length > 0) {
              stack.pop();
              stackDelta++;
            }
            while (stackDelta > 0) {
              stack.push(NaN); // pushing any number into stack
              stackDelta--;
            }
          }
        }
        ttContext.tooComplexToFollowFunctions = tooComplexToFollowFunctions;
        var content = [data];
        if (i > data.length) {
          content.push(new Uint8Array(i - data.length));
        }
        if (lastDeff > lastEndf) {
          warn('TT: complementing a missing function tail');
          // new function definition started, but not finished
          // complete function by [CLEAR, ENDF]
          content.push(new Uint8Array([0x22, 0x2D]));
        }
        foldTTTable(table, content);
      }

      function checkInvalidFunctions(ttContext, maxFunctionDefs) {
        if (ttContext.tooComplexToFollowFunctions) {
          return;
        }
        if (ttContext.functionsDefined.length > maxFunctionDefs) {
          warn('TT: more functions defined than expected');
          ttContext.hintsValid = false;
          return;
        }
        for (var j = 0, jj = ttContext.functionsUsed.length; j < jj; j++) {
          if (j > maxFunctionDefs) {
            warn('TT: invalid function id: ' + j);
            ttContext.hintsValid = false;
            return;
          }
          if (ttContext.functionsUsed[j] && !ttContext.functionsDefined[j]) {
            warn('TT: undefined function: ' + j);
            ttContext.hintsValid = false;
            return;
          }
        }
      }

      function foldTTTable(table, content) {
        if (content.length > 1) {
          // concatenating the content items
          var newLength = 0;
          var j, jj;
          for (j = 0, jj = content.length; j < jj; j++) {
            newLength += content[j].length;
          }
          newLength = (newLength + 3) & ~3;
          var result = new Uint8Array(newLength);
          var pos = 0;
          for (j = 0, jj = content.length; j < jj; j++) {
            result.set(content[j], pos);
            pos += content[j].length;
          }
          table.data = result;
          table.length = newLength;
        }
      }

      function sanitizeTTPrograms(fpgm, prep, cvt) {
        var ttContext = {
          functionsDefined: [],
          functionsUsed: [],
          functionsStackDeltas: [],
          tooComplexToFollowFunctions: false,
          hintsValid: true
        };
        if (fpgm) {
          sanitizeTTProgram(fpgm, ttContext);
        }
        if (prep) {
          sanitizeTTProgram(prep, ttContext);
        }
        if (fpgm) {
          checkInvalidFunctions(ttContext, maxFunctionDefs);
        }
        if (cvt && (cvt.length & 1)) {
          var cvtData = new Uint8Array(cvt.length + 1);
          cvtData.set(cvt.data);
          cvt.data = cvtData;
        }
        return ttContext.hintsValid;
      }

      // The following steps modify the original font data, making copy
      font = new Stream(new Uint8Array(font.getBytes()));

      var VALID_TABLES = ['OS/2', 'cmap', 'head', 'hhea', 'hmtx', 'maxp',
        'name', 'post', 'loca', 'glyf', 'fpgm', 'prep', 'cvt ', 'CFF '];

      var header = readOpenTypeHeader(font);
      var numTables = header.numTables;
      var cff, cffFile;

      var tables = { 'OS/2': null, cmap: null, head: null, hhea: null,
                     hmtx: null, maxp: null, name: null, post: null };
      var table;
      for (var i = 0; i < numTables; i++) {
        table = readTableEntry(font);
        if (VALID_TABLES.indexOf(table.tag) < 0) {
          continue; // skipping table if it's not a required or optional table
        }
        if (table.length === 0) {
          continue; // skipping empty tables
        }
        tables[table.tag] = table;
      }

      var isTrueType = !tables['CFF '];
      if (!isTrueType) {
        // OpenType font
        if (header.version === 'OTTO' ||
            !tables.head || !tables.hhea || !tables.maxp || !tables.post) {
          // no major tables: throwing everything at CFFFont
          cffFile = new Stream(tables['CFF '].data);
          cff = new CFFFont(cffFile, properties);

          return this.convert(name, cff, properties);
        }

        delete tables.glyf;
        delete tables.loca;
        delete tables.fpgm;
        delete tables.prep;
        delete tables['cvt '];
        this.isOpenType = true;
      } else {
        if (!tables.glyf || !tables.loca) {
          error('Required "glyf" or "loca" tables are not found');
        }
        this.isOpenType = false;
      }

      if (!tables.maxp) {
        error('Required "maxp" table is not found');
      }

      font.pos = (font.start || 0) + tables.maxp.offset;
      var version = font.getInt32();
      var numGlyphs = font.getUint16();
      var maxFunctionDefs = 0;
      if (version >= 0x00010000 && tables.maxp.length >= 22) {
        // maxZones can be invalid
        font.pos += 8;
        var maxZones = font.getUint16();
        if (maxZones > 2) { // reset to 2 if font has invalid maxZones
          tables.maxp.data[14] = 0;
          tables.maxp.data[15] = 2;
        }
        font.pos += 4;
        maxFunctionDefs = font.getUint16();
      }

      var dupFirstEntry = false;
      if (properties.type === 'CIDFontType2' && properties.toUnicode &&
          properties.toUnicode.get(0) > '\u0000') {
        // oracle's defect (see 3427), duplicating first entry
        dupFirstEntry = true;
        numGlyphs++;
        tables.maxp.data[4] = numGlyphs >> 8;
        tables.maxp.data[5] = numGlyphs & 255;
      }

      var hintsValid = sanitizeTTPrograms(tables.fpgm, tables.prep,
                                          tables['cvt '], maxFunctionDefs);
      if (!hintsValid) {
        delete tables.fpgm;
        delete tables.prep;
        delete tables['cvt '];
      }

      // Ensure the hmtx table contains the advance width and
      // sidebearings information for numGlyphs in the maxp table
      sanitizeMetrics(font, tables.hhea, tables.hmtx, numGlyphs);

      if (!tables.head) {
        error('Required "head" table is not found');
      }

      sanitizeHead(tables.head, numGlyphs, isTrueType ? tables.loca.length : 0);

      var missingGlyphs = {};
      if (isTrueType) {
        var isGlyphLocationsLong = int16(tables.head.data[50],
                                         tables.head.data[51]);
        missingGlyphs = sanitizeGlyphLocations(tables.loca, tables.glyf,
                                               numGlyphs, isGlyphLocationsLong,
                                               hintsValid, dupFirstEntry);
      }

      if (!tables.hhea) {
        error('Required "hhea" table is not found');
      }

      // Sanitizer reduces the glyph advanceWidth to the maxAdvanceWidth
      // Sometimes it's 0. That needs to be fixed
      if (tables.hhea.data[10] === 0 && tables.hhea.data[11] === 0) {
        tables.hhea.data[10] = 0xFF;
        tables.hhea.data[11] = 0xFF;
      }

      // The 'post' table has glyphs names.
      if (tables.post) {
        var valid = readPostScriptTable(tables.post, properties, numGlyphs);
        if (!valid) {
          tables.post = null;
        }
      }

      var charCodeToGlyphId = [], charCode, toUnicode = properties.toUnicode;

      function hasGlyph(glyphId, charCode) {
        if (!missingGlyphs[glyphId]) {
          return true;
        }
        if (charCode >= 0 && toUnicode.has(charCode)) {
          return true;
        }
        return false;
      }

      if (properties.type === 'CIDFontType2') {
        var cidToGidMap = properties.cidToGidMap || [];
        var isCidToGidMapEmpty = cidToGidMap.length === 0;

        properties.cMap.forEach(function(charCode, cid) {
          assert(cid <= 0xffff, 'Max size of CID is 65,535');
          var glyphId = -1;
          if (isCidToGidMapEmpty) {
            glyphId = charCode;
          } else if (cidToGidMap[cid] !== undefined) {
            glyphId = cidToGidMap[cid];
          }

          if (glyphId >= 0 && glyphId < numGlyphs &&
              hasGlyph(glyphId, charCode)) {
            charCodeToGlyphId[charCode] = glyphId;
          }
        });
        if (dupFirstEntry) {
          charCodeToGlyphId[0] = numGlyphs - 1;
        }
      } else {
        // Most of the following logic in this code branch is based on the
        // 9.6.6.4 of the PDF spec.
        var cmapTable = readCmapTable(tables.cmap, font, this.isSymbolicFont);
        var cmapPlatformId = cmapTable.platformId;
        var cmapEncodingId = cmapTable.encodingId;
        var cmapMappings = cmapTable.mappings;
        var cmapMappingsLength = cmapMappings.length;
        var hasEncoding = properties.differences.length ||
                          !!properties.baseEncodingName;

        // The spec seems to imply that if the font is symbolic the encoding
        // should be ignored, this doesn't appear to work for 'preistabelle.pdf'
        // where the the font is symbolic and it has an encoding.
        if (hasEncoding &&
            (cmapPlatformId === 3 && cmapEncodingId === 1 ||
             cmapPlatformId === 1 && cmapEncodingId === 0) ||
            (cmapPlatformId === -1 && cmapEncodingId === -1 && // Temporary hack
             !!Encodings[properties.baseEncodingName])) {      // Temporary hack
          // When no preferred cmap table was found and |baseEncodingName| is
          // one of the predefined encodings, we seem to obtain a better
          // |charCodeToGlyphId| map from the code below (fixes bug 1057544).
          // TODO: Note that this is a hack which should be removed as soon as
          //       we have proper support for more exotic cmap tables.

          var baseEncoding = [];
          if (properties.baseEncodingName === 'MacRomanEncoding' ||
              properties.baseEncodingName === 'WinAnsiEncoding') {
            baseEncoding = Encodings[properties.baseEncodingName];
          }
          for (charCode = 0; charCode < 256; charCode++) {
            var glyphName;
            if (this.differences && charCode in this.differences) {
              glyphName = this.differences[charCode];
            } else if (charCode in baseEncoding &&
                       baseEncoding[charCode] !== '') {
              glyphName = baseEncoding[charCode];
            } else {
              glyphName = Encodings.StandardEncoding[charCode];
            }
            if (!glyphName) {
              continue;
            }
            var unicodeOrCharCode;
            if (cmapPlatformId === 3 && cmapEncodingId === 1) {
              unicodeOrCharCode = GlyphsUnicode[glyphName];
            } else if (cmapPlatformId === 1 && cmapEncodingId === 0) {
              // TODO: the encoding needs to be updated with mac os table.
              unicodeOrCharCode = Encodings.MacRomanEncoding.indexOf(glyphName);
            }

            var found = false;
            for (i = 0; i < cmapMappingsLength; ++i) {
              if (cmapMappings[i].charCode === unicodeOrCharCode &&
                  hasGlyph(cmapMappings[i].glyphId, unicodeOrCharCode)) {
                charCodeToGlyphId[charCode] = cmapMappings[i].glyphId;
                found = true;
                break;
              }
            }
            if (!found && properties.glyphNames) {
              // Try to map using the post table. There are currently no known
              // pdfs that this fixes.
              var glyphId = properties.glyphNames.indexOf(glyphName);
              if (glyphId > 0 && hasGlyph(glyphId, -1)) {
                charCodeToGlyphId[charCode] = glyphId;
              }
            }
          }
        } else if (cmapPlatformId === 0 && cmapEncodingId === 0) {
          // Default Unicode semantics, use the charcodes as is.
          for (i = 0; i < cmapMappingsLength; ++i) {
            charCodeToGlyphId[cmapMappings[i].charCode] =
              cmapMappings[i].glyphId;
          }
        } else {
          // For (3, 0) cmap tables:
          // The charcode key being stored in charCodeToGlyphId is the lower
          // byte of the two-byte charcodes of the cmap table since according to
          // the spec: 'each byte from the string shall be prepended with the
          // high byte of the range [of charcodes in the cmap table], to form
          // a two-byte character, which shall be used to select the
          // associated glyph description from the subtable'.
          //
          // For (1, 0) cmap tables:
          // 'single bytes from the string shall be used to look up the
          // associated glyph descriptions from the subtable'. This means
          // charcodes in the cmap will be single bytes, so no-op since
          // glyph.charCode & 0xFF === glyph.charCode
          for (i = 0; i < cmapMappingsLength; ++i) {
            charCode = cmapMappings[i].charCode & 0xFF;
            charCodeToGlyphId[charCode] = cmapMappings[i].glyphId;
          }
        }
      }

      if (charCodeToGlyphId.length === 0) {
        // defines at least one glyph
        charCodeToGlyphId[0] = 0;
      }

      // Converting glyphs and ids into font's cmap table
      var newMapping = adjustMapping(charCodeToGlyphId, properties);
      this.toFontChar = newMapping.toFontChar;
      tables.cmap = {
        tag: 'cmap',
        data: createCmapTable(newMapping.charCodeToGlyphId)
      };

      if (!tables['OS/2'] || !validateOS2Table(tables['OS/2'])) {
        // extract some more font properties from the OpenType head and
        // hhea tables; yMin and descent value are always negative
        var override = {
          unitsPerEm: int16(tables.head.data[18], tables.head.data[19]),
          yMax: int16(tables.head.data[42], tables.head.data[43]),
          yMin: int16(tables.head.data[38], tables.head.data[39]) - 0x10000,
          ascent: int16(tables.hhea.data[4], tables.hhea.data[5]),
          descent: int16(tables.hhea.data[6], tables.hhea.data[7]) - 0x10000
        };

        tables['OS/2'] = {
          tag: 'OS/2',
          data: createOS2Table(properties, newMapping.charCodeToGlyphId,
                               override)
        };
      }

      // Rewrite the 'post' table if needed
      if (!tables.post) {
        tables.post = {
          tag: 'post',
          data: createPostTable(properties)
        };
      }

      if (!isTrueType) {
        try {
          // Trying to repair CFF file
          cffFile = new Stream(tables['CFF '].data);
          var parser = new CFFParser(cffFile, properties);
          cff = parser.parse();
          var compiler = new CFFCompiler(cff);
          tables['CFF '].data = compiler.compile();
        } catch (e) {
          warn('Failed to compile font ' + properties.loadedName);
        }
      }

      // Re-creating 'name' table
      if (!tables.name) {
        tables.name = {
          tag: 'name',
          data: createNameTable(this.name)
        };
      } else {
        // ... using existing 'name' table as prototype
        var namePrototype = readNameTable(tables.name);
        tables.name.data = createNameTable(name, namePrototype);
      }

      var builder = new OpenTypeFileBuilder(header.version);
      for (var tableTag in tables) {
        builder.addTable(tableTag, tables[tableTag].data);
      }
      return builder.toArray();
    },

    convert: function Font_convert(fontName, font, properties) {
      // TODO: Check the charstring widths to determine this.
      properties.fixedPitch = false;

      var mapping = font.getGlyphMapping(properties);
      var newMapping = adjustMapping(mapping, properties);
      this.toFontChar = newMapping.toFontChar;
      var numGlyphs = font.numGlyphs;

      function getCharCodes(charCodeToGlyphId, glyphId) {
        var charCodes = null;
        for (var charCode in charCodeToGlyphId) {
          if (glyphId === charCodeToGlyphId[charCode]) {
            if (!charCodes) {
              charCodes = [];
            }
            charCodes.push(charCode | 0);
          }
        }
        return charCodes;
      }

      function createCharCode(charCodeToGlyphId, glyphId) {
        for (var charCode in charCodeToGlyphId) {
          if (glyphId === charCodeToGlyphId[charCode]) {
            return charCode | 0;
          }
        }
        newMapping.charCodeToGlyphId[newMapping.nextAvailableFontCharCode] =
            glyphId;
        return newMapping.nextAvailableFontCharCode++;
      }

      var seacs = font.seacs;
      if (SEAC_ANALYSIS_ENABLED && seacs && seacs.length) {
        var matrix = properties.fontMatrix || FONT_IDENTITY_MATRIX;
        var charset = font.getCharset();
        var seacMap = Object.create(null);
        for (var glyphId in seacs) {
          glyphId |= 0;
          var seac = seacs[glyphId];
          var baseGlyphName = Encodings.StandardEncoding[seac[2]];
          var accentGlyphName = Encodings.StandardEncoding[seac[3]];
          var baseGlyphId = charset.indexOf(baseGlyphName);
          var accentGlyphId = charset.indexOf(accentGlyphName);
          if (baseGlyphId < 0 || accentGlyphId < 0) {
            continue;
          }
          var accentOffset = {
            x: seac[0] * matrix[0] + seac[1] * matrix[2] + matrix[4],
            y: seac[0] * matrix[1] + seac[1] * matrix[3] + matrix[5]
          };

          var charCodes = getCharCodes(mapping, glyphId);
          if (!charCodes) {
            // There's no point in mapping it if the char code was never mapped
            // to begin with.
            continue;
          }
          for (var i = 0, ii = charCodes.length; i < ii; i++) {
            var charCode = charCodes[i];
            // Find a fontCharCode that maps to the base and accent glyphs.
            // If one doesn't exists, create it.
            var charCodeToGlyphId = newMapping.charCodeToGlyphId;
            var baseFontCharCode = createCharCode(charCodeToGlyphId,
                                                  baseGlyphId);
            var accentFontCharCode = createCharCode(charCodeToGlyphId,
                                                    accentGlyphId);
            seacMap[charCode] = {
              baseFontCharCode: baseFontCharCode,
              accentFontCharCode: accentFontCharCode,
              accentOffset: accentOffset
            };
          }
        }
        properties.seacMap = seacMap;
      }

      var unitsPerEm = 1 / (properties.fontMatrix || FONT_IDENTITY_MATRIX)[0];

      var builder = new OpenTypeFileBuilder('\x4F\x54\x54\x4F');
      // PostScript Font Program
      builder.addTable('CFF ', font.data);
      // OS/2 and Windows Specific metrics
      builder.addTable('OS/2', createOS2Table(properties,
                                              newMapping.charCodeToGlyphId));
      // Character to glyphs mapping
      builder.addTable('cmap', createCmapTable(newMapping.charCodeToGlyphId));
      // Font header
      builder.addTable('head',
            '\x00\x01\x00\x00' + // Version number
            '\x00\x00\x10\x00' + // fontRevision
            '\x00\x00\x00\x00' + // checksumAdjustement
            '\x5F\x0F\x3C\xF5' + // magicNumber
            '\x00\x00' + // Flags
            safeString16(unitsPerEm) + // unitsPerEM
            '\x00\x00\x00\x00\x9e\x0b\x7e\x27' + // creation date
            '\x00\x00\x00\x00\x9e\x0b\x7e\x27' + // modifification date
            '\x00\x00' + // xMin
            safeString16(properties.descent) + // yMin
            '\x0F\xFF' + // xMax
            safeString16(properties.ascent) + // yMax
            string16(properties.italicAngle ? 2 : 0) + // macStyle
            '\x00\x11' + // lowestRecPPEM
            '\x00\x00' + // fontDirectionHint
            '\x00\x00' + // indexToLocFormat
            '\x00\x00');  // glyphDataFormat

      // Horizontal header
      builder.addTable('hhea',
            '\x00\x01\x00\x00' + // Version number
            safeString16(properties.ascent) + // Typographic Ascent
            safeString16(properties.descent) + // Typographic Descent
            '\x00\x00' + // Line Gap
            '\xFF\xFF' + // advanceWidthMax
            '\x00\x00' + // minLeftSidebearing
            '\x00\x00' + // minRightSidebearing
            '\x00\x00' + // xMaxExtent
            safeString16(properties.capHeight) + // caretSlopeRise
            safeString16(Math.tan(properties.italicAngle) *
                         properties.xHeight) + // caretSlopeRun
            '\x00\x00' + // caretOffset
            '\x00\x00' + // -reserved-
            '\x00\x00' + // -reserved-
            '\x00\x00' + // -reserved-
            '\x00\x00' + // -reserved-
            '\x00\x00' + // metricDataFormat
            string16(numGlyphs)); // Number of HMetrics

      // Horizontal metrics
      builder.addTable('hmtx', (function fontFieldsHmtx() {
          var charstrings = font.charstrings;
          var cffWidths = font.cff ? font.cff.widths : null;
          var hmtx = '\x00\x00\x00\x00'; // Fake .notdef
          for (var i = 1, ii = numGlyphs; i < ii; i++) {
            var width = 0;
            if (charstrings) {
              var charstring = charstrings[i - 1];
              width = 'width' in charstring ? charstring.width : 0;
            } else if (cffWidths) {
              width = Math.ceil(cffWidths[i] || 0);
            }
            hmtx += string16(width) + string16(0);
          }
          return hmtx;
        })());

      // Maximum profile
      builder.addTable('maxp',
            '\x00\x00\x50\x00' + // Version number
            string16(numGlyphs)); // Num of glyphs

      // Naming tables
      builder.addTable('name', createNameTable(fontName));

      // PostScript informations
      builder.addTable('post', createPostTable(properties));

      return builder.toArray();
    },

    /**
     * Builds a char code to unicode map based on section 9.10 of the spec.
     * @param {Object} properties Font properties object.
     * @return {Object} A ToUnicodeMap object.
     */
    buildToUnicode: function Font_buildToUnicode(properties) {
      // Section 9.10.2 Mapping Character Codes to Unicode Values
      if (properties.toUnicode && properties.toUnicode.length !== 0) {
        return properties.toUnicode;
      }
      // According to the spec if the font is a simple font we should only map
      // to unicode if the base encoding is MacRoman, MacExpert, or WinAnsi or
      // the differences array only contains adobe standard or symbol set names,
      // in pratice it seems better to always try to create a toUnicode
      // map based of the default encoding.
      var toUnicode, charcode;
      if (!properties.composite /* is simple font */) {
        toUnicode = [];
        var encoding = properties.defaultEncoding.slice();
        var baseEncodingName = properties.baseEncodingName;
        // Merge in the differences array.
        var differences = properties.differences;
        for (charcode in differences) {
          encoding[charcode] = differences[charcode];
        }
        for (charcode in encoding) {
          // a) Map the character code to a character name.
          var glyphName = encoding[charcode];
          // b) Look up the character name in the Adobe Glyph List (see the
          //    Bibliography) to obtain the corresponding Unicode value.
          if (glyphName === '') {
            continue;
          } else if (GlyphsUnicode[glyphName] === undefined) {
            // (undocumented) c) Few heuristics to recognize unknown glyphs
            // NOTE: Adobe Reader does not do this step, but OSX Preview does
            var code = 0;
            switch (glyphName[0]) {
              case 'G': // Gxx glyph
                if (glyphName.length === 3) {
                  code = parseInt(glyphName.substr(1), 16);
                }
                break;
              case 'g': // g00xx glyph
                if (glyphName.length === 5) {
                  code = parseInt(glyphName.substr(1), 16);
                }
                break;
              case 'C': // Cddd glyph
              case 'c': // cddd glyph
                if (glyphName.length >= 3) {
                  code = +glyphName.substr(1);
                }
                break;
            }
            if (code) {
              // If |baseEncodingName| is one the predefined encodings,
              // and |code| equals |charcode|, using the glyph defined in the
              // baseEncoding seems to yield a better |toUnicode| mapping
              // (fixes issue 5070).
              if (baseEncodingName && code === +charcode) {
                var baseEncoding = Encodings[baseEncodingName];
                if (baseEncoding && (glyphName = baseEncoding[charcode])) {
                  toUnicode[charcode] =
                    String.fromCharCode(GlyphsUnicode[glyphName]);
                  continue;
                }
              }
              toUnicode[charcode] = String.fromCharCode(code);
            }
            continue;
          }
          toUnicode[charcode] = String.fromCharCode(GlyphsUnicode[glyphName]);
        }
        return new ToUnicodeMap(toUnicode);
      }
      // If the font is a composite font that uses one of the predefined CMaps
      // listed in Table 118 (except Identity–H and Identity–V) or whose
      // descendant CIDFont uses the Adobe-GB1, Adobe-CNS1, Adobe-Japan1, or
      // Adobe-Korea1 character collection:
      if (properties.composite && (
           (properties.cMap.builtInCMap &&
            !(properties.cMap instanceof IdentityCMap)) ||
           (properties.cidSystemInfo.registry === 'Adobe' &&
             (properties.cidSystemInfo.ordering === 'GB1' ||
              properties.cidSystemInfo.ordering === 'CNS1' ||
              properties.cidSystemInfo.ordering === 'Japan1' ||
              properties.cidSystemInfo.ordering === 'Korea1')))) {
        // Then:
        // a) Map the character code to a character identifier (CID) according
        // to the font’s CMap.
        // b) Obtain the registry and ordering of the character collection used
        // by the font’s CMap (for example, Adobe and Japan1) from its
        // CIDSystemInfo dictionary.
        var registry = properties.cidSystemInfo.registry;
        var ordering = properties.cidSystemInfo.ordering;
        // c) Construct a second CMap name by concatenating the registry and
        // ordering obtained in step (b) in the format registry–ordering–UCS2
        // (for example, Adobe–Japan1–UCS2).
        var ucs2CMapName = new Name(registry + '-' + ordering + '-UCS2');
        // d) Obtain the CMap with the name constructed in step (c) (available
        // from the ASN Web site; see the Bibliography).
        var ucs2CMap = CMapFactory.create(ucs2CMapName,
          { url: PDFJS.cMapUrl, packed: PDFJS.cMapPacked }, null);
        var cMap = properties.cMap;
        toUnicode = [];
        cMap.forEach(function(charcode, cid) {
          assert(cid <= 0xffff, 'Max size of CID is 65,535');
          // e) Map the CID obtained in step (a) according to the CMap obtained
          // in step (d), producing a Unicode value.
          var ucs2 = ucs2CMap.lookup(cid);
          if (ucs2) {
            toUnicode[charcode] =
              String.fromCharCode((ucs2.charCodeAt(0) << 8) +
                                  ucs2.charCodeAt(1));
          }
        });
        return new ToUnicodeMap(toUnicode);
      }

      // The viewer's choice, just use an identity map.
      return new IdentityToUnicodeMap(properties.firstChar,
                                      properties.lastChar);
    },

    get spaceWidth() {
      if ('_shadowWidth' in this) {
        return this._shadowWidth;
      }

      // trying to estimate space character width
      var possibleSpaceReplacements = ['space', 'minus', 'one', 'i'];
      var width;
      for (var i = 0, ii = possibleSpaceReplacements.length; i < ii; i++) {
        var glyphName = possibleSpaceReplacements[i];
        // if possible, getting width by glyph name
        if (glyphName in this.widths) {
          width = this.widths[glyphName];
          break;
        }
        var glyphUnicode = GlyphsUnicode[glyphName];
        // finding the charcode via unicodeToCID map
        var charcode = 0;
        if (this.composite) {
          if (this.cMap.contains(glyphUnicode)) {
            charcode = this.cMap.lookup(glyphUnicode);
          }
        }
        // ... via toUnicode map
        if (!charcode && 'toUnicode' in this) {
          charcode = this.toUnicode.charCodeOf(glyphUnicode);
        }
        // setting it to unicode if negative or undefined
        if (charcode <= 0) {
          charcode = glyphUnicode;
        }
        // trying to get width via charcode
        width = this.widths[charcode];
        if (width) {
          break; // the non-zero width found
        }
      }
      width = width || this.defaultWidth;
      // Do not shadow the property here. See discussion:
      // https://github.com/mozilla/pdf.js/pull/2127#discussion_r1662280
      this._shadowWidth = width;
      return width;
    },

    charToGlyph: function Font_charToGlyph(charcode) {
      var fontCharCode, width, operatorListId;

      var widthCode = charcode;
      if (this.cMap && this.cMap.contains(charcode)) {
        widthCode = this.cMap.lookup(charcode);
      }
      width = this.widths[widthCode];
      width = isNum(width) ? width : this.defaultWidth;
      var vmetric = this.vmetrics && this.vmetrics[widthCode];

      var unicode = this.toUnicode.get(charcode) || charcode;
      if (typeof unicode === 'number') {
        unicode = String.fromCharCode(unicode);
      }

      // First try the toFontChar map, if it's not there then try falling
      // back to the char code.
      fontCharCode = this.toFontChar[charcode] || charcode;
      if (this.missingFile) {
        fontCharCode = mapSpecialUnicodeValues(fontCharCode);
      }

      if (this.isType3Font) {
        // Font char code in this case is actually a glyph name.
        operatorListId = fontCharCode;
      }

      var accent = null;
      if (this.seacMap && this.seacMap[charcode]) {
        var seac = this.seacMap[charcode];
        fontCharCode = seac.baseFontCharCode;
        accent = {
          fontChar: String.fromCharCode(seac.accentFontCharCode),
          offset: seac.accentOffset
        };
      }

      var fontChar = String.fromCharCode(fontCharCode);

      var glyph = this.glyphCache[charcode];
      if (!glyph ||
          !glyph.matchesForCache(fontChar, unicode, accent, width, vmetric,
                                 operatorListId)) {
        glyph = new Glyph(fontChar, unicode, accent, width, vmetric,
                          operatorListId);
        this.glyphCache[charcode] = glyph;
      }
      return glyph;
    },

    charsToGlyphs: function Font_charsToGlyphs(chars) {
      var charsCache = this.charsCache;
      var glyphs, glyph, charcode;

      // if we translated this string before, just grab it from the cache
      if (charsCache) {
        glyphs = charsCache[chars];
        if (glyphs) {
          return glyphs;
        }
      }

      // lazily create the translation cache
      if (!charsCache) {
        charsCache = this.charsCache = Object.create(null);
      }

      glyphs = [];
      var charsCacheKey = chars;
      var i = 0, ii;

      if (this.cMap) {
        // composite fonts have multi-byte strings convert the string from
        // single-byte to multi-byte
        var c = {};
        while (i < chars.length) {
          this.cMap.readCharCode(chars, i, c);
          charcode = c.charcode;
          var length = c.length;
          i += length;
          glyph = this.charToGlyph(charcode);
          glyphs.push(glyph);
          // placing null after each word break charcode (ASCII SPACE)
          // Ignore occurences of 0x20 in multiple-byte codes.
          if (length === 1 && chars.charCodeAt(i - 1) === 0x20) {
            glyphs.push(null);
          }
        }
      } else {
        for (i = 0, ii = chars.length; i < ii; ++i) {
          charcode = chars.charCodeAt(i);
          glyph = this.charToGlyph(charcode);
          glyphs.push(glyph);
          if (charcode === 0x20) {
            glyphs.push(null);
          }
        }
      }

      // Enter the translated string into the cache
      return (charsCache[charsCacheKey] = glyphs);
    }
  };

  return Font;
})();

var ErrorFont = (function ErrorFontClosure() {
  function ErrorFont(error) {
    this.error = error;
    this.loadedName = 'g_font_error';
    this.loading = false;
  }

  ErrorFont.prototype = {
    charsToGlyphs: function ErrorFont_charsToGlyphs() {
      return [];
    },
    exportData: function ErrorFont_exportData() {
      return {error: this.error};
    }
  };

  return ErrorFont;
})();

/**
 * Shared logic for building a char code to glyph id mapping for Type1 and
 * simple CFF fonts. See section 9.6.6.2 of the spec.
 * @param {Object} properties Font properties object.
 * @param {Object} builtInEncoding The encoding contained within the actual font
 * data.
 * @param {Array} Array of glyph names where the index is the glyph ID.
 * @returns {Object} A char code to glyph ID map.
 */
function type1FontGlyphMapping(properties, builtInEncoding, glyphNames) {
  var charCodeToGlyphId = Object.create(null);
  var glyphId, charCode, baseEncoding;

  if (properties.baseEncodingName) {
    // If a valid base encoding name was used, the mapping is initialized with
    // that.
    baseEncoding = Encodings[properties.baseEncodingName];
    for (charCode = 0; charCode < baseEncoding.length; charCode++) {
      glyphId = glyphNames.indexOf(baseEncoding[charCode]);
      if (glyphId >= 0) {
        charCodeToGlyphId[charCode] = glyphId;
      } else {
        charCodeToGlyphId[charCode] = 0; // notdef
      }
    }
  } else if (!!(properties.flags & FontFlags.Symbolic)) {
    // For a symbolic font the encoding should be the fonts built-in
    // encoding.
    for (charCode in builtInEncoding) {
      charCodeToGlyphId[charCode] = builtInEncoding[charCode];
    }
  } else {
    // For non-symbolic fonts that don't have a base encoding the standard
    // encoding should be used.
    baseEncoding = Encodings.StandardEncoding;
    for (charCode = 0; charCode < baseEncoding.length; charCode++) {
      glyphId = glyphNames.indexOf(baseEncoding[charCode]);
      if (glyphId >= 0) {
        charCodeToGlyphId[charCode] = glyphId;
      } else {
        charCodeToGlyphId[charCode] = 0; // notdef
      }
    }
  }

  // Lastly, merge in the differences.
  var differences = properties.differences;
  if (differences) {
    for (charCode in differences) {
      var glyphName = differences[charCode];
      glyphId = glyphNames.indexOf(glyphName);
      if (glyphId >= 0) {
        charCodeToGlyphId[charCode] = glyphId;
      } else {
        charCodeToGlyphId[charCode] = 0; // notdef
      }
    }
  }
  return charCodeToGlyphId;
}

/*
 * CharStrings are encoded following the the CharString Encoding sequence
 * describe in Chapter 6 of the "Adobe Type1 Font Format" specification.
 * The value in a byte indicates a command, a number, or subsequent bytes
 * that are to be interpreted in a special way.
 *
 * CharString Number Encoding:
 *  A CharString byte containing the values from 32 through 255 inclusive
 *  indicate an integer. These values are decoded in four ranges.
 *
 * 1. A CharString byte containing a value, v, between 32 and 246 inclusive,
 * indicate the integer v - 139. Thus, the integer values from -107 through
 * 107 inclusive may be encoded in single byte.
 *
 * 2. A CharString byte containing a value, v, between 247 and 250 inclusive,
 * indicates an integer involving the next byte, w, according to the formula:
 * [(v - 247) x 256] + w + 108
 *
 * 3. A CharString byte containing a value, v, between 251 and 254 inclusive,
 * indicates an integer involving the next byte, w, according to the formula:
 * -[(v - 251) * 256] - w - 108
 *
 * 4. A CharString containing the value 255 indicates that the next 4 bytes
 * are a two complement signed integer. The first of these bytes contains the
 * highest order bits, the second byte contains the next higher order bits
 * and the fourth byte contain the lowest order bits.
 *
 *
 * CharString Command Encoding:
 *  CharStrings commands are encoded in 1 or 2 bytes.
 *
 *  Single byte commands are encoded in 1 byte that contains a value between
 *  0 and 31 inclusive.
 *  If a command byte contains the value 12, then the value in the next byte
 *  indicates a command. This "escape" mechanism allows many extra commands
 * to be encoded and this encoding technique helps to minimize the length of
 * the charStrings.
 */
var Type1CharString = (function Type1CharStringClosure() {
  var COMMAND_MAP = {
    'hstem': [1],
    'vstem': [3],
    'vmoveto': [4],
    'rlineto': [5],
    'hlineto': [6],
    'vlineto': [7],
    'rrcurveto': [8],
    'callsubr': [10],
    'flex': [12, 35],
    'drop' : [12, 18],
    'endchar': [14],
    'rmoveto': [21],
    'hmoveto': [22],
    'vhcurveto': [30],
    'hvcurveto': [31]
  };

  function Type1CharString() {
    this.width = 0;
    this.lsb = 0;
    this.flexing = false;
    this.output = [];
    this.stack = [];
  }

  Type1CharString.prototype = {
    convert: function Type1CharString_convert(encoded, subrs) {
      var count = encoded.length;
      var error = false;
      var wx, sbx, subrNumber;
      for (var i = 0; i < count; i++) {
        var value = encoded[i];
        if (value < 32) {
          if (value === 12) {
            value = (value << 8) + encoded[++i];
          }
          switch (value) {
            case 1: // hstem
              if (!HINTING_ENABLED) {
                this.stack = [];
                break;
              }
              error = this.executeCommand(2, COMMAND_MAP.hstem);
              break;
            case 3: // vstem
              if (!HINTING_ENABLED) {
                this.stack = [];
                break;
              }
              error = this.executeCommand(2, COMMAND_MAP.vstem);
              break;
            case 4: // vmoveto
              if (this.flexing) {
                if (this.stack.length < 1) {
                  error = true;
                  break;
                }
                // Add the dx for flex and but also swap the values so they are
                // the right order.
                var dy = this.stack.pop();
                this.stack.push(0, dy);
                break;
              }
              error = this.executeCommand(1, COMMAND_MAP.vmoveto);
              break;
            case 5: // rlineto
              error = this.executeCommand(2, COMMAND_MAP.rlineto);
              break;
            case 6: // hlineto
              error = this.executeCommand(1, COMMAND_MAP.hlineto);
              break;
            case 7: // vlineto
              error = this.executeCommand(1, COMMAND_MAP.vlineto);
              break;
            case 8: // rrcurveto
              error = this.executeCommand(6, COMMAND_MAP.rrcurveto);
              break;
            case 9: // closepath
              // closepath is a Type1 command that does not take argument and is
              // useless in Type2 and it can simply be ignored.
              this.stack = [];
              break;
            case 10: // callsubr
              if (this.stack.length < 1) {
                error = true;
                break;
              }
              subrNumber = this.stack.pop();
              error = this.convert(subrs[subrNumber], subrs);
              break;
            case 11: // return
              return error;
            case 13: // hsbw
              if (this.stack.length < 2) {
                error = true;
                break;
              }
              // To convert to type2 we have to move the width value to the
              // first part of the charstring and then use hmoveto with lsb.
              wx = this.stack.pop();
              sbx = this.stack.pop();
              this.lsb = sbx;
              this.width = wx;
              this.stack.push(wx, sbx);
              error = this.executeCommand(2, COMMAND_MAP.hmoveto);
              break;
            case 14: // endchar
              this.output.push(COMMAND_MAP.endchar[0]);
              break;
            case 21: // rmoveto
              if (this.flexing) {
                break;
              }
              error = this.executeCommand(2, COMMAND_MAP.rmoveto);
              break;
            case 22: // hmoveto
              if (this.flexing) {
                // Add the dy for flex.
                this.stack.push(0);
                break;
              }
              error = this.executeCommand(1, COMMAND_MAP.hmoveto);
              break;
            case 30: // vhcurveto
              error = this.executeCommand(4, COMMAND_MAP.vhcurveto);
              break;
            case 31: // hvcurveto
              error = this.executeCommand(4, COMMAND_MAP.hvcurveto);
              break;
            case (12 << 8) + 0: // dotsection
              // dotsection is a Type1 command to specify some hinting feature
              // for dots that do not take a parameter and it can safely be
              // ignored for Type2.
              this.stack = [];
              break;
            case (12 << 8) + 1: // vstem3
              if (!HINTING_ENABLED) {
                this.stack = [];
                break;
              }
              // [vh]stem3 are Type1 only and Type2 supports [vh]stem with
              // multiple parameters, so instead of returning [vh]stem3 take a
              // shortcut and return [vhstem] instead.
              error = this.executeCommand(2, COMMAND_MAP.vstem);
              break;
            case (12 << 8) + 2: // hstem3
              if (!HINTING_ENABLED) {
                 this.stack = [];
                break;
              }
              // See vstem3.
              error = this.executeCommand(2, COMMAND_MAP.hstem);
              break;
            case (12 << 8) + 6: // seac
              // seac is like type 2's special endchar but it doesn't use the
              // first argument asb, so remove it.
              if (SEAC_ANALYSIS_ENABLED) {
                this.seac = this.stack.splice(-4, 4);
                error = this.executeCommand(0, COMMAND_MAP.endchar);
              } else {
                error = this.executeCommand(4, COMMAND_MAP.endchar);
              }
              break;
            case (12 << 8) + 7: // sbw
              if (this.stack.length < 4) {
                error = true;
                break;
              }
              // To convert to type2 we have to move the width value to the
              // first part of the charstring and then use rmoveto with
              // (dx, dy). The height argument will not be used for vmtx and
              // vhea tables reconstruction -- ignoring it.
              var wy = this.stack.pop();
              wx = this.stack.pop();
              var sby = this.stack.pop();
              sbx = this.stack.pop();
              this.lsb = sbx;
              this.width = wx;
              this.stack.push(wx, sbx, sby);
              error = this.executeCommand(3, COMMAND_MAP.rmoveto);
              break;
            case (12 << 8) + 12: // div
              if (this.stack.length < 2) {
                error = true;
                break;
              }
              var num2 = this.stack.pop();
              var num1 = this.stack.pop();
              this.stack.push(num1 / num2);
              break;
            case (12 << 8) + 16: // callothersubr
              if (this.stack.length < 2) {
                error = true;
                break;
              }
              subrNumber = this.stack.pop();
              var numArgs = this.stack.pop();
              if (subrNumber === 0 && numArgs === 3) {
                var flexArgs = this.stack.splice(this.stack.length - 17, 17);
                this.stack.push(
                  flexArgs[2] + flexArgs[0], // bcp1x + rpx
                  flexArgs[3] + flexArgs[1], // bcp1y + rpy
                  flexArgs[4], // bcp2x
                  flexArgs[5], // bcp2y
                  flexArgs[6], // p2x
                  flexArgs[7], // p2y
                  flexArgs[8], // bcp3x
                  flexArgs[9], // bcp3y
                  flexArgs[10], // bcp4x
                  flexArgs[11], // bcp4y
                  flexArgs[12], // p3x
                  flexArgs[13], // p3y
                  flexArgs[14] // flexDepth
                  // 15 = finalx unused by flex
                  // 16 = finaly unused by flex
                );
                error = this.executeCommand(13, COMMAND_MAP.flex, true);
                this.flexing = false;
                this.stack.push(flexArgs[15], flexArgs[16]);
              } else if (subrNumber === 1 && numArgs === 0) {
                this.flexing = true;
              }
              break;
            case (12 << 8) + 17: // pop
              // Ignore this since it is only used with othersubr.
              break;
            case (12 << 8) + 33: // setcurrentpoint
              // Ignore for now.
              this.stack = [];
              break;
            default:
              warn('Unknown type 1 charstring command of "' + value + '"');
              break;
          }
          if (error) {
            break;
          }
          continue;
        } else if (value <= 246) {
          value = value - 139;
        } else if (value <= 250) {
          value = ((value - 247) * 256) + encoded[++i] + 108;
        } else if (value <= 254) {
          value = -((value - 251) * 256) - encoded[++i] - 108;
        } else {
          value = (encoded[++i] & 0xff) << 24 | (encoded[++i] & 0xff) << 16 |
                  (encoded[++i] & 0xff) << 8 | (encoded[++i] & 0xff) << 0;
        }
        this.stack.push(value);
      }
      return error;
    },

    executeCommand: function(howManyArgs, command, keepStack) {
      var stackLength = this.stack.length;
      if (howManyArgs > stackLength) {
        return true;
      }
      var start = stackLength - howManyArgs;
      for (var i = start; i < stackLength; i++) {
        var value = this.stack[i];
        if (value === (value | 0)) { // int
          this.output.push(28, (value >> 8) & 0xff, value & 0xff);
        } else { // fixed point
          value = (65536 * value) | 0;
          this.output.push(255,
                           (value >> 24) & 0xFF,
                           (value >> 16) & 0xFF,
                           (value >> 8) & 0xFF,
                           value & 0xFF);
        }
      }
      this.output.push.apply(this.output, command);
      if (keepStack) {
        this.stack.splice(start, howManyArgs);
      } else {
        this.stack.length = 0;
      }
      return false;
    }
  };

  return Type1CharString;
})();

/*
 * Type1Parser encapsulate the needed code for parsing a Type1 font
 * program. Some of its logic depends on the Type2 charstrings
 * structure.
 * Note: this doesn't really parse the font since that would require evaluation
 * of PostScript, but it is possible in most cases to extract what we need
 * without a full parse.
 */
var Type1Parser = (function Type1ParserClosure() {
  /*
   * Decrypt a Sequence of Ciphertext Bytes to Produce the Original Sequence
   * of Plaintext Bytes. The function took a key as a parameter which can be
   * for decrypting the eexec block of for decoding charStrings.
   */
  var EEXEC_ENCRYPT_KEY = 55665;
  var CHAR_STRS_ENCRYPT_KEY = 4330;

  function isHexDigit(code) {
    return code >= 48 && code <= 57 || // '0'-'9'
           code >= 65 && code <= 70 || // 'A'-'F'
           code >= 97 && code <= 102;  // 'a'-'f'
  }

  function decrypt(data, key, discardNumber) {
    var r = key | 0, c1 = 52845, c2 = 22719;
    var count = data.length;
    var decrypted = new Uint8Array(count);
    for (var i = 0; i < count; i++) {
      var value = data[i];
      decrypted[i] = value ^ (r >> 8);
      r = ((value + r) * c1 + c2) & ((1 << 16) - 1);
    }
    return Array.prototype.slice.call(decrypted, discardNumber);
  }

  function decryptAscii(data, key, discardNumber) {
    var r = key | 0, c1 = 52845, c2 = 22719;
    var count = data.length, maybeLength = count >>> 1;
    var decrypted = new Uint8Array(maybeLength);
    var i, j;
    for (i = 0, j = 0; i < count; i++) {
      var digit1 = data[i];
      if (!isHexDigit(digit1)) {
        continue;
      }
      i++;
      var digit2;
      while (i < count && !isHexDigit(digit2 = data[i])) {
        i++;
      }
      if (i < count) {
        var value = parseInt(String.fromCharCode(digit1, digit2), 16);
        decrypted[j++] = value ^ (r >> 8);
        r = ((value + r) * c1 + c2) & ((1 << 16) - 1);
      }
    }
    return Array.prototype.slice.call(decrypted, discardNumber, j);
  }

  function isSpecial(c) {
    return c === 0x2F || // '/'
           c === 0x5B || c === 0x5D || // '[', ']'
           c === 0x7B || c === 0x7D || // '{', '}'
           c === 0x28 || c === 0x29; // '(', ')'
  }

  function Type1Parser(stream, encrypted) {
    if (encrypted) {
      var data = stream.getBytes();
      var isBinary = !(isHexDigit(data[0]) && isHexDigit(data[1]) &&
                       isHexDigit(data[2]) && isHexDigit(data[3]));
      stream = new Stream(isBinary ? decrypt(data, EEXEC_ENCRYPT_KEY, 4) :
                          decryptAscii(data, EEXEC_ENCRYPT_KEY, 4));
    }
    this.stream = stream;
    this.nextChar();
  }

  Type1Parser.prototype = {
    readNumberArray: function Type1Parser_readNumberArray() {
      this.getToken(); // read '[' or '{' (arrays can start with either)
      var array = [];
      while (true) {
        var token = this.getToken();
        if (token === null || token === ']' || token === '}') {
          break;
        }
        array.push(parseFloat(token || 0));
      }
      return array;
    },

    readNumber: function Type1Parser_readNumber() {
      var token = this.getToken();
      return parseFloat(token || 0);
    },

    readInt: function Type1Parser_readInt() {
      // Use '| 0' to prevent setting a double into length such as the double
      // does not flow into the loop variable.
      var token = this.getToken();
      return parseInt(token || 0, 10) | 0;
    },

    readBoolean: function Type1Parser_readBoolean() {
      var token = this.getToken();

      // Use 1 and 0 since that's what type2 charstrings use.
      return token === 'true' ? 1 : 0;
    },

    nextChar : function Type1_nextChar() {
      return (this.currentChar = this.stream.getByte());
    },

    getToken: function Type1Parser_getToken() {
      // Eat whitespace and comments.
      var comment = false;
      var ch = this.currentChar;
      while (true) {
        if (ch === -1) {
          return null;
        }

        if (comment) {
          if (ch === 0x0A || ch === 0x0D) {
            comment = false;
          }
        } else if (ch === 0x25) { // '%'
          comment = true;
        } else if (!Lexer.isSpace(ch)) {
          break;
        }
        ch = this.nextChar();
      }
      if (isSpecial(ch)) {
        this.nextChar();
        return String.fromCharCode(ch);
      }
      var token = '';
      do {
        token += String.fromCharCode(ch);
        ch = this.nextChar();
      } while (ch >= 0 && !Lexer.isSpace(ch) && !isSpecial(ch));
      return token;
    },

    /*
     * Returns an object containing a Subrs array and a CharStrings
     * array extracted from and eexec encrypted block of data
     */
    extractFontProgram: function Type1Parser_extractFontProgram() {
      var stream = this.stream;

      var subrs = [], charstrings = [];
      var program = {
        subrs: [],
        charstrings: [],
        properties: {
          'privateData': {
            'lenIV': 4
          }
        }
      };
      var token, length, data, lenIV, encoded;
      while ((token = this.getToken()) !== null) {
        if (token !== '/') {
          continue;
        }
        token = this.getToken();
        switch (token) {
          case 'CharStrings':
            // The number immediately following CharStrings must be greater or
            // equal to the number of CharStrings.
            this.getToken();
            this.getToken(); // read in 'dict'
            this.getToken(); // read in 'dup'
            this.getToken(); // read in 'begin'
            while(true) {
              token = this.getToken();
              if (token === null || token === 'end') {
                break;
              }

              if (token !== '/') {
                continue;
              }
              var glyph = this.getToken();
              length = this.readInt();
              this.getToken(); // read in 'RD' or '-|'
              data = stream.makeSubStream(stream.pos, length);
              lenIV = program.properties.privateData['lenIV'];
              encoded = decrypt(data.getBytes(), CHAR_STRS_ENCRYPT_KEY, lenIV);
              // Skip past the required space and binary data.
              stream.skip(length);
              this.nextChar();
              token = this.getToken(); // read in 'ND' or '|-'
              if (token === 'noaccess') {
                this.getToken(); // read in 'def'
              }
              charstrings.push({
                glyph: glyph,
                encoded: encoded
              });
            }
            break;
          case 'Subrs':
            var num = this.readInt();
            this.getToken(); // read in 'array'
            while ((token = this.getToken()) === 'dup') {
              var index = this.readInt();
              length = this.readInt();
              this.getToken(); // read in 'RD' or '-|'
              data = stream.makeSubStream(stream.pos, length);
              lenIV = program.properties.privateData['lenIV'];
              encoded = decrypt(data.getBytes(), CHAR_STRS_ENCRYPT_KEY, lenIV);
              // Skip past the required space and binary data.
              stream.skip(length);
              this.nextChar();
              token = this.getToken(); // read in 'NP' or '|'
              if (token === 'noaccess') {
                this.getToken(); // read in 'put'
              }
              subrs[index] = encoded;
            }
            break;
          case 'BlueValues':
          case 'OtherBlues':
          case 'FamilyBlues':
          case 'FamilyOtherBlues':
            var blueArray = this.readNumberArray();
            // *Blue* values may contain invalid data: disables reading of
            // those values when hinting is disabled.
            if (blueArray.length > 0 && (blueArray.length % 2) === 0 &&
                HINTING_ENABLED) {
              program.properties.privateData[token] = blueArray;
            }
            break;
          case 'StemSnapH':
          case 'StemSnapV':
            program.properties.privateData[token] = this.readNumberArray();
            break;
          case 'StdHW':
          case 'StdVW':
            program.properties.privateData[token] =
              this.readNumberArray()[0];
            break;
          case 'BlueShift':
          case 'lenIV':
          case 'BlueFuzz':
          case 'BlueScale':
          case 'LanguageGroup':
          case 'ExpansionFactor':
            program.properties.privateData[token] = this.readNumber();
            break;
          case 'ForceBold':
            program.properties.privateData[token] = this.readBoolean();
            break;
        }
      }

      for (var i = 0; i < charstrings.length; i++) {
        glyph = charstrings[i].glyph;
        encoded = charstrings[i].encoded;
        var charString = new Type1CharString();
        var error = charString.convert(encoded, subrs);
        var output = charString.output;
        if (error) {
          // It seems when FreeType encounters an error while evaluating a glyph
          // that it completely ignores the glyph so we'll mimic that behaviour
          // here and put an endchar to make the validator happy.
          output = [14];
        }
        program.charstrings.push({
          glyphName: glyph,
          charstring: output,
          width: charString.width,
          lsb: charString.lsb,
          seac: charString.seac
        });
      }

      return program;
    },

    extractFontHeader: function Type1Parser_extractFontHeader(properties) {
      var token;
      while ((token = this.getToken()) !== null) {
        if (token !== '/') {
          continue;
        }
        token = this.getToken();
        switch (token) {
          case 'FontMatrix':
            var matrix = this.readNumberArray();
            properties.fontMatrix = matrix;
            break;
          case 'Encoding':
            var encodingArg = this.getToken();
            var encoding;
            if (!/^\d+$/.test(encodingArg)) {
              // encoding name is specified
              encoding = Encodings[encodingArg];
            } else {
              encoding = [];
              var size = parseInt(encodingArg, 10) | 0;
              this.getToken(); // read in 'array'

              for (var j = 0; j < size; j++) {
                token = this.getToken();
                // skipping till first dup or def (e.g. ignoring for statement)
                while (token !== 'dup' && token !== 'def') {
                  token = this.getToken();
                  if (token === null) {
                    return; // invalid header
                  }
                }
                if (token === 'def') {
                  break; // read all array data
                }
                var index = this.readInt();
                this.getToken(); // read in '/'
                var glyph = this.getToken();
                encoding[index] = glyph;
                this.getToken(); // read the in 'put'
              }
            }
            properties.builtInEncoding = encoding;
            break;
          case 'FontBBox':
            var fontBBox = this.readNumberArray();
            // adjusting ascent/descent
            properties.ascent = fontBBox[3];
            properties.descent = fontBBox[1];
            properties.ascentScaled = true;
            break;
        }
      }
    }
  };

  return Type1Parser;
})();

/**
 * The CFF class takes a Type1 file and wrap it into a
 * 'Compact Font Format' which itself embed Type2 charstrings.
 */
var CFFStandardStrings = [
  '.notdef', 'space', 'exclam', 'quotedbl', 'numbersign', 'dollar', 'percent',
  'ampersand', 'quoteright', 'parenleft', 'parenright', 'asterisk', 'plus',
  'comma', 'hyphen', 'period', 'slash', 'zero', 'one', 'two', 'three', 'four',
  'five', 'six', 'seven', 'eight', 'nine', 'colon', 'semicolon', 'less',
  'equal', 'greater', 'question', 'at', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
  'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
  'X', 'Y', 'Z', 'bracketleft', 'backslash', 'bracketright', 'asciicircum',
  'underscore', 'quoteleft', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
  'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y',
  'z', 'braceleft', 'bar', 'braceright', 'asciitilde', 'exclamdown', 'cent',
  'sterling', 'fraction', 'yen', 'florin', 'section', 'currency',
  'quotesingle', 'quotedblleft', 'guillemotleft', 'guilsinglleft',
  'guilsinglright', 'fi', 'fl', 'endash', 'dagger', 'daggerdbl',
  'periodcentered', 'paragraph', 'bullet', 'quotesinglbase', 'quotedblbase',
  'quotedblright', 'guillemotright', 'ellipsis', 'perthousand', 'questiondown',
  'grave', 'acute', 'circumflex', 'tilde', 'macron', 'breve', 'dotaccent',
  'dieresis', 'ring', 'cedilla', 'hungarumlaut', 'ogonek', 'caron', 'emdash',
  'AE', 'ordfeminine', 'Lslash', 'Oslash', 'OE', 'ordmasculine', 'ae',
  'dotlessi', 'lslash', 'oslash', 'oe', 'germandbls', 'onesuperior',
  'logicalnot', 'mu', 'trademark', 'Eth', 'onehalf', 'plusminus', 'Thorn',
  'onequarter', 'divide', 'brokenbar', 'degree', 'thorn', 'threequarters',
  'twosuperior', 'registered', 'minus', 'eth', 'multiply', 'threesuperior',
  'copyright', 'Aacute', 'Acircumflex', 'Adieresis', 'Agrave', 'Aring',
  'Atilde', 'Ccedilla', 'Eacute', 'Ecircumflex', 'Edieresis', 'Egrave',
  'Iacute', 'Icircumflex', 'Idieresis', 'Igrave', 'Ntilde', 'Oacute',
  'Ocircumflex', 'Odieresis', 'Ograve', 'Otilde', 'Scaron', 'Uacute',
  'Ucircumflex', 'Udieresis', 'Ugrave', 'Yacute', 'Ydieresis', 'Zcaron',
  'aacute', 'acircumflex', 'adieresis', 'agrave', 'aring', 'atilde',
  'ccedilla', 'eacute', 'ecircumflex', 'edieresis', 'egrave', 'iacute',
  'icircumflex', 'idieresis', 'igrave', 'ntilde', 'oacute', 'ocircumflex',
  'odieresis', 'ograve', 'otilde', 'scaron', 'uacute', 'ucircumflex',
  'udieresis', 'ugrave', 'yacute', 'ydieresis', 'zcaron', 'exclamsmall',
  'Hungarumlautsmall', 'dollaroldstyle', 'dollarsuperior', 'ampersandsmall',
  'Acutesmall', 'parenleftsuperior', 'parenrightsuperior', 'twodotenleader',
  'onedotenleader', 'zerooldstyle', 'oneoldstyle', 'twooldstyle',
  'threeoldstyle', 'fouroldstyle', 'fiveoldstyle', 'sixoldstyle',
  'sevenoldstyle', 'eightoldstyle', 'nineoldstyle', 'commasuperior',
  'threequartersemdash', 'periodsuperior', 'questionsmall', 'asuperior',
  'bsuperior', 'centsuperior', 'dsuperior', 'esuperior', 'isuperior',
  'lsuperior', 'msuperior', 'nsuperior', 'osuperior', 'rsuperior', 'ssuperior',
  'tsuperior', 'ff', 'ffi', 'ffl', 'parenleftinferior', 'parenrightinferior',
  'Circumflexsmall', 'hyphensuperior', 'Gravesmall', 'Asmall', 'Bsmall',
  'Csmall', 'Dsmall', 'Esmall', 'Fsmall', 'Gsmall', 'Hsmall', 'Ismall',
  'Jsmall', 'Ksmall', 'Lsmall', 'Msmall', 'Nsmall', 'Osmall', 'Psmall',
  'Qsmall', 'Rsmall', 'Ssmall', 'Tsmall', 'Usmall', 'Vsmall', 'Wsmall',
  'Xsmall', 'Ysmall', 'Zsmall', 'colonmonetary', 'onefitted', 'rupiah',
  'Tildesmall', 'exclamdownsmall', 'centoldstyle', 'Lslashsmall',
  'Scaronsmall', 'Zcaronsmall', 'Dieresissmall', 'Brevesmall', 'Caronsmall',
  'Dotaccentsmall', 'Macronsmall', 'figuredash', 'hypheninferior',
  'Ogoneksmall', 'Ringsmall', 'Cedillasmall', 'questiondownsmall', 'oneeighth',
  'threeeighths', 'fiveeighths', 'seveneighths', 'onethird', 'twothirds',
  'zerosuperior', 'foursuperior', 'fivesuperior', 'sixsuperior',
  'sevensuperior', 'eightsuperior', 'ninesuperior', 'zeroinferior',
  'oneinferior', 'twoinferior', 'threeinferior', 'fourinferior',
  'fiveinferior', 'sixinferior', 'seveninferior', 'eightinferior',
  'nineinferior', 'centinferior', 'dollarinferior', 'periodinferior',
  'commainferior', 'Agravesmall', 'Aacutesmall', 'Acircumflexsmall',
  'Atildesmall', 'Adieresissmall', 'Aringsmall', 'AEsmall', 'Ccedillasmall',
  'Egravesmall', 'Eacutesmall', 'Ecircumflexsmall', 'Edieresissmall',
  'Igravesmall', 'Iacutesmall', 'Icircumflexsmall', 'Idieresissmall',
  'Ethsmall', 'Ntildesmall', 'Ogravesmall', 'Oacutesmall', 'Ocircumflexsmall',
  'Otildesmall', 'Odieresissmall', 'OEsmall', 'Oslashsmall', 'Ugravesmall',
  'Uacutesmall', 'Ucircumflexsmall', 'Udieresissmall', 'Yacutesmall',
  'Thornsmall', 'Ydieresissmall', '001.000', '001.001', '001.002', '001.003',
  'Black', 'Bold', 'Book', 'Light', 'Medium', 'Regular', 'Roman', 'Semibold'
];

// Type1Font is also a CIDFontType0.
var Type1Font = function Type1Font(name, file, properties) {
  // Some bad generators embed pfb file as is, we have to strip 6-byte headers.
  // Also, length1 and length2 might be off by 6 bytes as well.
  // http://www.math.ubc.ca/~cass/piscript/type1.pdf
  var PFB_HEADER_SIZE = 6;
  var headerBlockLength = properties.length1;
  var eexecBlockLength = properties.length2;
  var pfbHeader = file.peekBytes(PFB_HEADER_SIZE);
  var pfbHeaderPresent = pfbHeader[0] === 0x80 && pfbHeader[1] === 0x01;
  if (pfbHeaderPresent) {
    file.skip(PFB_HEADER_SIZE);
    headerBlockLength = (pfbHeader[5] << 24) | (pfbHeader[4] << 16) |
                        (pfbHeader[3] << 8) | pfbHeader[2];
  }

  // Get the data block containing glyphs and subrs informations
  var headerBlock = new Stream(file.getBytes(headerBlockLength));
  var headerBlockParser = new Type1Parser(headerBlock);
  headerBlockParser.extractFontHeader(properties);

  if (pfbHeaderPresent) {
    pfbHeader = file.getBytes(PFB_HEADER_SIZE);
    eexecBlockLength = (pfbHeader[5] << 24) | (pfbHeader[4] << 16) |
                       (pfbHeader[3] << 8) | pfbHeader[2];
  }

  // Decrypt the data blocks and retrieve it's content
  var eexecBlock = new Stream(file.getBytes(eexecBlockLength));
  var eexecBlockParser = new Type1Parser(eexecBlock, true);
  var data = eexecBlockParser.extractFontProgram();
  for (var info in data.properties) {
    properties[info] = data.properties[info];
  }

  var charstrings = data.charstrings;
  var type2Charstrings = this.getType2Charstrings(charstrings);
  var subrs = this.getType2Subrs(data.subrs);

  this.charstrings = charstrings;
  this.data = this.wrap(name, type2Charstrings, this.charstrings,
                        subrs, properties);
  this.seacs = this.getSeacs(data.charstrings);
};

Type1Font.prototype = {
  get numGlyphs() {
    return this.charstrings.length + 1;
  },

  getCharset: function Type1Font_getCharset() {
    var charset = ['.notdef'];
    var charstrings = this.charstrings;
    for (var glyphId = 0; glyphId < charstrings.length; glyphId++) {
      charset.push(charstrings[glyphId].glyphName);
    }
    return charset;
  },

  getGlyphMapping: function Type1Font_getGlyphMapping(properties) {
    var charstrings = this.charstrings;
    var glyphNames = ['.notdef'], glyphId;
    for (glyphId = 0; glyphId < charstrings.length; glyphId++) {
      glyphNames.push(charstrings[glyphId].glyphName);
    }
    var encoding = properties.builtInEncoding;
    if (encoding) {
      var builtInEncoding = {};
      for (var charCode in encoding) {
        glyphId = glyphNames.indexOf(encoding[charCode]);
        if (glyphId >= 0) {
          builtInEncoding[charCode] = glyphId;
        }
      }
    }

    return type1FontGlyphMapping(properties, builtInEncoding, glyphNames);
  },

  getSeacs: function Type1Font_getSeacs(charstrings) {
    var i, ii;
    var seacMap = [];
    for (i = 0, ii = charstrings.length; i < ii; i++) {
      var charstring = charstrings[i];
      if (charstring.seac) {
        // Offset by 1 for .notdef
        seacMap[i + 1] = charstring.seac;
      }
    }
    return seacMap;
  },

  getType2Charstrings: function Type1Font_getType2Charstrings(
                                  type1Charstrings) {
    var type2Charstrings = [];
    for (var i = 0, ii = type1Charstrings.length; i < ii; i++) {
      type2Charstrings.push(type1Charstrings[i].charstring);
    }
    return type2Charstrings;
  },

  getType2Subrs: function Type1Font_getType2Subrs(type1Subrs) {
    var bias = 0;
    var count = type1Subrs.length;
    if (count < 1133) {
      bias = 107;
    } else if (count < 33769) {
      bias = 1131;
    } else {
      bias = 32768;
    }

    // Add a bunch of empty subrs to deal with the Type2 bias
    var type2Subrs = [];
    var i;
    for (i = 0; i < bias; i++) {
      type2Subrs.push([0x0B]);
    }

    for (i = 0; i < count; i++) {
      type2Subrs.push(type1Subrs[i]);
    }

    return type2Subrs;
  },

  wrap: function Type1Font_wrap(name, glyphs, charstrings, subrs, properties) {
    var cff = new CFF();
    cff.header = new CFFHeader(1, 0, 4, 4);

    cff.names = [name];

    var topDict = new CFFTopDict();
    // CFF strings IDs 0...390 are predefined names, so refering
    // to entries in our own String INDEX starts at SID 391.
    topDict.setByName('version', 391);
    topDict.setByName('Notice', 392);
    topDict.setByName('FullName', 393);
    topDict.setByName('FamilyName', 394);
    topDict.setByName('Weight', 395);
    topDict.setByName('Encoding', null); // placeholder
    topDict.setByName('FontMatrix', properties.fontMatrix);
    topDict.setByName('FontBBox', properties.bbox);
    topDict.setByName('charset', null); // placeholder
    topDict.setByName('CharStrings', null); // placeholder
    topDict.setByName('Private', null); // placeholder
    cff.topDict = topDict;

    var strings = new CFFStrings();
    strings.add('Version 0.11'); // Version
    strings.add('See original notice'); // Notice
    strings.add(name); // FullName
    strings.add(name); // FamilyName
    strings.add('Medium'); // Weight
    cff.strings = strings;

    cff.globalSubrIndex = new CFFIndex();

    var count = glyphs.length;
    var charsetArray = [0];
    var i, ii;
    for (i = 0; i < count; i++) {
      var index = CFFStandardStrings.indexOf(charstrings[i].glyphName);
      // TODO: Insert the string and correctly map it.  Previously it was
      // thought mapping names that aren't in the standard strings to .notdef
      // was fine, however in issue818 when mapping them all to .notdef the
      // adieresis glyph no longer worked.
      if (index === -1) {
        index = 0;
      }
      charsetArray.push((index >> 8) & 0xff, index & 0xff);
    }
    cff.charset = new CFFCharset(false, 0, [], charsetArray);

    var charStringsIndex = new CFFIndex();
    charStringsIndex.add([0x8B, 0x0E]); // .notdef
    for (i = 0; i < count; i++) {
      charStringsIndex.add(glyphs[i]);
    }
    cff.charStrings = charStringsIndex;

    var privateDict = new CFFPrivateDict();
    privateDict.setByName('Subrs', null); // placeholder
    var fields = [
      'BlueValues',
      'OtherBlues',
      'FamilyBlues',
      'FamilyOtherBlues',
      'StemSnapH',
      'StemSnapV',
      'BlueShift',
      'BlueFuzz',
      'BlueScale',
      'LanguageGroup',
      'ExpansionFactor',
      'ForceBold',
      'StdHW',
      'StdVW'
    ];
    for (i = 0, ii = fields.length; i < ii; i++) {
      var field = fields[i];
      if (!properties.privateData.hasOwnProperty(field)) {
        continue;
      }
      var value = properties.privateData[field];
      if (isArray(value)) {
        // All of the private dictionary array data in CFF must be stored as
        // "delta-encoded" numbers.
        for (var j = value.length - 1; j > 0; j--) {
          value[j] -= value[j - 1]; // ... difference from previous value
        }
      }
      privateDict.setByName(field, value);
    }
    cff.topDict.privateDict = privateDict;

    var subrIndex = new CFFIndex();
    for (i = 0, ii = subrs.length; i < ii; i++) {
      subrIndex.add(subrs[i]);
    }
    privateDict.subrsIndex = subrIndex;

    var compiler = new CFFCompiler(cff);
    return compiler.compile();
  }
};

var CFFFont = (function CFFFontClosure() {
  function CFFFont(file, properties) {
    this.properties = properties;

    var parser = new CFFParser(file, properties);
    this.cff = parser.parse();
    var compiler = new CFFCompiler(this.cff);
    this.seacs = this.cff.seacs;
    try {
      this.data = compiler.compile();
    } catch (e) {
      warn('Failed to compile font ' + properties.loadedName);
      // There may have just been an issue with the compiler, set the data
      // anyway and hope the font loaded.
      this.data = file;
    }
  }

  CFFFont.prototype = {
    get numGlyphs() {
      return this.cff.charStrings.count;
    },
    getCharset: function CFFFont_getCharset() {
      return this.cff.charset.charset;
    },
    getGlyphMapping: function CFFFont_getGlyphMapping() {
      var cff = this.cff;
      var properties = this.properties;
      var charsets = cff.charset.charset;
      var charCodeToGlyphId;
      var glyphId;

      if (properties.composite) {
        charCodeToGlyphId = Object.create(null);
        if (cff.isCIDFont) {
          // If the font is actually a CID font then we should use the charset
          // to map CIDs to GIDs.
          for (glyphId = 0; glyphId < charsets.length; glyphId++) {
            var cid = charsets[glyphId];
            var charCode = properties.cMap.charCodeOf(cid);
            charCodeToGlyphId[charCode] = glyphId;
          }
        } else {
          // If it is NOT actually a CID font then CIDs should be mapped
          // directly to GIDs.
          for (glyphId = 0; glyphId < cff.charStrings.count; glyphId++) {
            charCodeToGlyphId[glyphId] = glyphId;
          }
        }
        return charCodeToGlyphId;
      }

      var encoding = cff.encoding ? cff.encoding.encoding : null;
      charCodeToGlyphId = type1FontGlyphMapping(properties, encoding, charsets);
      return charCodeToGlyphId;
    }
  };

  return CFFFont;
})();

var CFFParser = (function CFFParserClosure() {
  var CharstringValidationData = [
    null,
    { id: 'hstem', min: 2, stackClearing: true, stem: true },
    null,
    { id: 'vstem', min: 2, stackClearing: true, stem: true },
    { id: 'vmoveto', min: 1, stackClearing: true },
    { id: 'rlineto', min: 2, resetStack: true },
    { id: 'hlineto', min: 1, resetStack: true },
    { id: 'vlineto', min: 1, resetStack: true },
    { id: 'rrcurveto', min: 6, resetStack: true },
    null,
    { id: 'callsubr', min: 1, undefStack: true },
    { id: 'return', min: 0, undefStack: true },
    null, // 12
    null,
    { id: 'endchar', min: 0, stackClearing: true },
    null,
    null,
    null,
    { id: 'hstemhm', min: 2, stackClearing: true, stem: true },
    { id: 'hintmask', min: 0, stackClearing: true },
    { id: 'cntrmask', min: 0, stackClearing: true },
    { id: 'rmoveto', min: 2, stackClearing: true },
    { id: 'hmoveto', min: 1, stackClearing: true },
    { id: 'vstemhm', min: 2, stackClearing: true, stem: true },
    { id: 'rcurveline', min: 8, resetStack: true },
    { id: 'rlinecurve', min: 8, resetStack: true },
    { id: 'vvcurveto', min: 4, resetStack: true },
    { id: 'hhcurveto', min: 4, resetStack: true },
    null, // shortint
    { id: 'callgsubr', min: 1, undefStack: true },
    { id: 'vhcurveto', min: 4, resetStack: true },
    { id: 'hvcurveto', min: 4, resetStack: true }
  ];
  var CharstringValidationData12 = [
    null,
    null,
    null,
    { id: 'and', min: 2, stackDelta: -1 },
    { id: 'or', min: 2, stackDelta: -1 },
    { id: 'not', min: 1, stackDelta: 0 },
    null,
    null,
    null,
    { id: 'abs', min: 1, stackDelta: 0 },
    { id: 'add', min: 2, stackDelta: -1,
      stackFn: function stack_div(stack, index) {
        stack[index - 2] = stack[index - 2] + stack[index - 1];
      }
    },
    { id: 'sub', min: 2, stackDelta: -1,
      stackFn: function stack_div(stack, index) {
        stack[index - 2] = stack[index - 2] - stack[index - 1];
      }
    },
    { id: 'div', min: 2, stackDelta: -1,
      stackFn: function stack_div(stack, index) {
        stack[index - 2] = stack[index - 2] / stack[index - 1];
      }
    },
    null,
    { id: 'neg', min: 1, stackDelta: 0,
      stackFn: function stack_div(stack, index) {
        stack[index - 1] = -stack[index - 1];
      }
    },
    { id: 'eq', min: 2, stackDelta: -1 },
    null,
    null,
    { id: 'drop', min: 1, stackDelta: -1 },
    null,
    { id: 'put', min: 2, stackDelta: -2 },
    { id: 'get', min: 1, stackDelta: 0 },
    { id: 'ifelse', min: 4, stackDelta: -3 },
    { id: 'random', min: 0, stackDelta: 1 },
    { id: 'mul', min: 2, stackDelta: -1,
      stackFn: function stack_div(stack, index) {
        stack[index - 2] = stack[index - 2] * stack[index - 1];
      }
    },
    null,
    { id: 'sqrt', min: 1, stackDelta: 0 },
    { id: 'dup', min: 1, stackDelta: 1 },
    { id: 'exch', min: 2, stackDelta: 0 },
    { id: 'index', min: 2, stackDelta: 0 },
    { id: 'roll', min: 3, stackDelta: -2 },
    null,
    null,
    null,
    { id: 'hflex', min: 7, resetStack: true },
    { id: 'flex', min: 13, resetStack: true },
    { id: 'hflex1', min: 9, resetStack: true },
    { id: 'flex1', min: 11, resetStack: true }
  ];

  function CFFParser(file, properties) {
    this.bytes = file.getBytes();
    this.properties = properties;
  }
  CFFParser.prototype = {
    parse: function CFFParser_parse() {
      var properties = this.properties;
      var cff = new CFF();
      this.cff = cff;

      // The first five sections must be in order, all the others are reached
      // via offsets contained in one of the below.
      var header = this.parseHeader();
      var nameIndex = this.parseIndex(header.endPos);
      var topDictIndex = this.parseIndex(nameIndex.endPos);
      var stringIndex = this.parseIndex(topDictIndex.endPos);
      var globalSubrIndex = this.parseIndex(stringIndex.endPos);

      var topDictParsed = this.parseDict(topDictIndex.obj.get(0));
      var topDict = this.createDict(CFFTopDict, topDictParsed, cff.strings);

      cff.header = header.obj;
      cff.names = this.parseNameIndex(nameIndex.obj);
      cff.strings = this.parseStringIndex(stringIndex.obj);
      cff.topDict = topDict;
      cff.globalSubrIndex = globalSubrIndex.obj;

      this.parsePrivateDict(cff.topDict);

      cff.isCIDFont = topDict.hasName('ROS');

      var charStringOffset = topDict.getByName('CharStrings');
      var charStringsAndSeacs = this.parseCharStrings(charStringOffset);
      cff.charStrings = charStringsAndSeacs.charStrings;
      cff.seacs = charStringsAndSeacs.seacs;
      cff.widths = charStringsAndSeacs.widths;

      var fontMatrix = topDict.getByName('FontMatrix');
      if (fontMatrix) {
        properties.fontMatrix = fontMatrix;
      }

      var fontBBox = topDict.getByName('FontBBox');
      if (fontBBox) {
        // adjusting ascent/descent
        properties.ascent = fontBBox[3];
        properties.descent = fontBBox[1];
        properties.ascentScaled = true;
      }

      var charset, encoding;
      if (cff.isCIDFont) {
        var fdArrayIndex = this.parseIndex(topDict.getByName('FDArray')).obj;
        for (var i = 0, ii = fdArrayIndex.count; i < ii; ++i) {
          var dictRaw = fdArrayIndex.get(i);
          var fontDict = this.createDict(CFFTopDict, this.parseDict(dictRaw),
                                         cff.strings);
          this.parsePrivateDict(fontDict);
          cff.fdArray.push(fontDict);
        }
        // cid fonts don't have an encoding
        encoding = null;
        charset = this.parseCharsets(topDict.getByName('charset'),
                                     cff.charStrings.count, cff.strings, true);
        cff.fdSelect = this.parseFDSelect(topDict.getByName('FDSelect'),
                                             cff.charStrings.count);
      } else {
        charset = this.parseCharsets(topDict.getByName('charset'),
                                     cff.charStrings.count, cff.strings, false);
        encoding = this.parseEncoding(topDict.getByName('Encoding'),
                                      properties,
                                      cff.strings, charset.charset);
      }
      cff.charset = charset;
      cff.encoding = encoding;

      return cff;
    },
    parseHeader: function CFFParser_parseHeader() {
      var bytes = this.bytes;
      var bytesLength = bytes.length;
      var offset = 0;

      // Prevent an infinite loop, by checking that the offset is within the
      // bounds of the bytes array. Necessary in empty, or invalid, font files.
      while (offset < bytesLength && bytes[offset] !== 1) {
        ++offset;
      }
      if (offset >= bytesLength) {
        error('Invalid CFF header');
      } else if (offset !== 0) {
        info('cff data is shifted');
        bytes = bytes.subarray(offset);
        this.bytes = bytes;
      }
      var major = bytes[0];
      var minor = bytes[1];
      var hdrSize = bytes[2];
      var offSize = bytes[3];
      var header = new CFFHeader(major, minor, hdrSize, offSize);
      return { obj: header, endPos: hdrSize };
    },
    parseDict: function CFFParser_parseDict(dict) {
      var pos = 0;

      function parseOperand() {
        var value = dict[pos++];
        if (value === 30) {
          return parseFloatOperand(pos);
        } else if (value === 28) {
          value = dict[pos++];
          value = ((value << 24) | (dict[pos++] << 16)) >> 16;
          return value;
        } else if (value === 29) {
          value = dict[pos++];
          value = (value << 8) | dict[pos++];
          value = (value << 8) | dict[pos++];
          value = (value << 8) | dict[pos++];
          return value;
        } else if (value >= 32 && value <= 246) {
          return value - 139;
        } else if (value >= 247 && value <= 250) {
          return ((value - 247) * 256) + dict[pos++] + 108;
        } else if (value >= 251 && value <= 254) {
          return -((value - 251) * 256) - dict[pos++] - 108;
        } else {
          error('255 is not a valid DICT command');
        }
        return -1;
      }

      function parseFloatOperand() {
        var str = '';
        var eof = 15;
        var lookup = ['0', '1', '2', '3', '4', '5', '6', '7', '8',
            '9', '.', 'E', 'E-', null, '-'];
        var length = dict.length;
        while (pos < length) {
          var b = dict[pos++];
          var b1 = b >> 4;
          var b2 = b & 15;

          if (b1 === eof) {
            break;
          }
          str += lookup[b1];

          if (b2 === eof) {
            break;
          }
          str += lookup[b2];
        }
        return parseFloat(str);
      }

      var operands = [];
      var entries = [];

      pos = 0;
      var end = dict.length;
      while (pos < end) {
        var b = dict[pos];
        if (b <= 21) {
          if (b === 12) {
            b = (b << 8) | dict[++pos];
          }
          entries.push([b, operands]);
          operands = [];
          ++pos;
        } else {
          operands.push(parseOperand());
        }
      }
      return entries;
    },
    parseIndex: function CFFParser_parseIndex(pos) {
      var cffIndex = new CFFIndex();
      var bytes = this.bytes;
      var count = (bytes[pos++] << 8) | bytes[pos++];
      var offsets = [];
      var end = pos;
      var i, ii;

      if (count !== 0) {
        var offsetSize = bytes[pos++];
        // add 1 for offset to determine size of last object
        var startPos = pos + ((count + 1) * offsetSize) - 1;

        for (i = 0, ii = count + 1; i < ii; ++i) {
          var offset = 0;
          for (var j = 0; j < offsetSize; ++j) {
            offset <<= 8;
            offset += bytes[pos++];
          }
          offsets.push(startPos + offset);
        }
        end = offsets[count];
      }
      for (i = 0, ii = offsets.length - 1; i < ii; ++i) {
        var offsetStart = offsets[i];
        var offsetEnd = offsets[i + 1];
        cffIndex.add(bytes.subarray(offsetStart, offsetEnd));
      }
      return {obj: cffIndex, endPos: end};
    },
    parseNameIndex: function CFFParser_parseNameIndex(index) {
      var names = [];
      for (var i = 0, ii = index.count; i < ii; ++i) {
        var name = index.get(i);
        // OTS doesn't allow names to be over 127 characters.
        var length = Math.min(name.length, 127);
        var data = [];
        // OTS also only permits certain characters in the name.
        for (var j = 0; j < length; ++j) {
          var c = name[j];
          if (j === 0 && c === 0) {
            data[j] = c;
            continue;
          }
          if ((c < 33 || c > 126) || c === 91 /* [ */ || c === 93 /* ] */ ||
              c === 40 /* ( */ || c === 41 /* ) */ || c === 123 /* { */ ||
              c === 125 /* } */ || c === 60 /* < */ || c === 62 /* > */ ||
              c === 47 /* / */ || c === 37 /* % */ || c === 35 /* # */) {
            data[j] = 95;
            continue;
          }
          data[j] = c;
        }
        names.push(bytesToString(data));
      }
      return names;
    },
    parseStringIndex: function CFFParser_parseStringIndex(index) {
      var strings = new CFFStrings();
      for (var i = 0, ii = index.count; i < ii; ++i) {
        var data = index.get(i);
        strings.add(bytesToString(data));
      }
      return strings;
    },
    createDict: function CFFParser_createDict(Type, dict, strings) {
      var cffDict = new Type(strings);
      for (var i = 0, ii = dict.length; i < ii; ++i) {
        var pair = dict[i];
        var key = pair[0];
        var value = pair[1];
        cffDict.setByKey(key, value);
      }
      return cffDict;
    },
    parseCharStrings: function CFFParser_parseCharStrings(charStringOffset) {
      var charStrings = this.parseIndex(charStringOffset).obj;
      var seacs = [];
      var widths = [];
      var count = charStrings.count;
      for (var i = 0; i < count; i++) {
        var charstring = charStrings.get(i);

        var stackSize = 0;
        var stack = [];
        var undefStack = true;
        var hints = 0;
        var valid = true;
        var data = charstring;
        var length = data.length;
        var firstStackClearing = true;
        for (var j = 0; j < length;) {
          var value = data[j++];
          var validationCommand = null;
          if (value === 12) {
            var q = data[j++];
            if (q === 0) {
              // The CFF specification state that the 'dotsection' command
              // (12, 0) is deprecated and treated as a no-op, but all Type2
              // charstrings processors should support them. Unfortunately
              // the font sanitizer don't. As a workaround the sequence (12, 0)
              // is replaced by a useless (0, hmoveto).
              data[j - 2] = 139;
              data[j - 1] = 22;
              stackSize = 0;
            } else {
              validationCommand = CharstringValidationData12[q];
            }
          } else if (value === 28) { // number (16 bit)
            stack[stackSize] = ((data[j] << 24) | (data[j + 1] << 16)) >> 16;
            j += 2;
            stackSize++;
          } else if (value === 14) {
            if (stackSize >= 4) {
              stackSize -= 4;
              if (SEAC_ANALYSIS_ENABLED) {
                seacs[i] = stack.slice(stackSize, stackSize + 4);
                valid = false;
              }
            }
            validationCommand = CharstringValidationData[value];
          } else if (value >= 32 && value <= 246) {  // number
            stack[stackSize] = value - 139;
            stackSize++;
          } else if (value >= 247 && value <= 254) {  // number (+1 bytes)
            stack[stackSize] = (value < 251 ?
                                ((value - 247) << 8) + data[j] + 108 :
                                -((value - 251) << 8) - data[j] - 108);
            j++;
            stackSize++;
          } else if (value === 255) {  // number (32 bit)
            stack[stackSize] = ((data[j] << 24) | (data[j + 1] << 16) |
                                (data[j + 2] << 8) | data[j + 3]) / 65536;
            j += 4;
            stackSize++;
          } else if (value === 19 || value === 20) {
            hints += stackSize >> 1;
            j += (hints + 7) >> 3; // skipping right amount of hints flag data
            stackSize %= 2;
            validationCommand = CharstringValidationData[value];
          } else {
            validationCommand = CharstringValidationData[value];
          }
          if (validationCommand) {
            if (validationCommand.stem) {
              hints += stackSize >> 1;
            }
            if ('min' in validationCommand) {
              if (!undefStack && stackSize < validationCommand.min) {
                warn('Not enough parameters for ' + validationCommand.id +
                     '; actual: ' + stackSize +
                     ', expected: ' + validationCommand.min);
                valid = false;
                break;
              }
            }
            if (firstStackClearing && validationCommand.stackClearing) {
              firstStackClearing = false;
              // the optional character width can be found before the first
              // stack-clearing command arguments
              stackSize -= validationCommand.min;
              if (stackSize >= 2 && validationCommand.stem) {
                // there are even amount of arguments for stem commands
                stackSize %= 2;
              } else if (stackSize > 1) {
                warn('Found too many parameters for stack-clearing command');
              }
              if (stackSize > 0 && stack[stackSize - 1] >= 0) {
                widths[i] = stack[stackSize - 1];
              }
            }
            if ('stackDelta' in validationCommand) {
              if ('stackFn' in validationCommand) {
                validationCommand.stackFn(stack, stackSize);
              }
              stackSize += validationCommand.stackDelta;
            } else if (validationCommand.stackClearing) {
              stackSize = 0;
            } else if (validationCommand.resetStack) {
              stackSize = 0;
              undefStack = false;
            } else if (validationCommand.undefStack) {
              stackSize = 0;
              undefStack = true;
              firstStackClearing = false;
            }
          }
        }
        if (!valid) {
          // resetting invalid charstring to single 'endchar'
          charStrings.set(i, new Uint8Array([14]));
        }
      }
      return { charStrings: charStrings, seacs: seacs, widths: widths };
    },
    emptyPrivateDictionary:
      function CFFParser_emptyPrivateDictionary(parentDict) {
      var privateDict = this.createDict(CFFPrivateDict, [],
                                        parentDict.strings);
      parentDict.setByKey(18, [0, 0]);
      parentDict.privateDict = privateDict;
    },
    parsePrivateDict: function CFFParser_parsePrivateDict(parentDict) {
      // no private dict, do nothing
      if (!parentDict.hasName('Private')) {
        this.emptyPrivateDictionary(parentDict);
        return;
      }
      var privateOffset = parentDict.getByName('Private');
      // make sure the params are formatted correctly
      if (!isArray(privateOffset) || privateOffset.length !== 2) {
        parentDict.removeByName('Private');
        return;
      }
      var size = privateOffset[0];
      var offset = privateOffset[1];
      // remove empty dicts or ones that refer to invalid location
      if (size === 0 || offset >= this.bytes.length) {
        this.emptyPrivateDictionary(parentDict);
        return;
      }

      var privateDictEnd = offset + size;
      var dictData = this.bytes.subarray(offset, privateDictEnd);
      var dict = this.parseDict(dictData);
      var privateDict = this.createDict(CFFPrivateDict, dict,
                                        parentDict.strings);
      parentDict.privateDict = privateDict;

      // Parse the Subrs index also since it's relative to the private dict.
      if (!privateDict.getByName('Subrs')) {
        return;
      }
      var subrsOffset = privateDict.getByName('Subrs');
      var relativeOffset = offset + subrsOffset;
      // Validate the offset.
      if (subrsOffset === 0 || relativeOffset >= this.bytes.length) {
        this.emptyPrivateDictionary(parentDict);
        return;
      }
      var subrsIndex = this.parseIndex(relativeOffset);
      privateDict.subrsIndex = subrsIndex.obj;
    },
    parseCharsets: function CFFParser_parseCharsets(pos, length, strings, cid) {
      if (pos === 0) {
        return new CFFCharset(true, CFFCharsetPredefinedTypes.ISO_ADOBE,
                              ISOAdobeCharset);
      } else if (pos === 1) {
        return new CFFCharset(true, CFFCharsetPredefinedTypes.EXPERT,
                              ExpertCharset);
      } else if (pos === 2) {
        return new CFFCharset(true, CFFCharsetPredefinedTypes.EXPERT_SUBSET,
                              ExpertSubsetCharset);
      }

      var bytes = this.bytes;
      var start = pos;
      var format = bytes[pos++];
      var charset = ['.notdef'];
      var id, count, i;

      // subtract 1 for the .notdef glyph
      length -= 1;

      switch (format) {
        case 0:
          for (i = 0; i < length; i++) {
            id = (bytes[pos++] << 8) | bytes[pos++];
            charset.push(cid ? id : strings.get(id));
          }
          break;
        case 1:
          while (charset.length <= length) {
            id = (bytes[pos++] << 8) | bytes[pos++];
            count = bytes[pos++];
            for (i = 0; i <= count; i++) {
              charset.push(cid ? id++ : strings.get(id++));
            }
          }
          break;
        case 2:
          while (charset.length <= length) {
            id = (bytes[pos++] << 8) | bytes[pos++];
            count = (bytes[pos++] << 8) | bytes[pos++];
            for (i = 0; i <= count; i++) {
              charset.push(cid ? id++ : strings.get(id++));
            }
          }
          break;
        default:
          error('Unknown charset format');
      }
      // Raw won't be needed if we actually compile the charset.
      var end = pos;
      var raw = bytes.subarray(start, end);

      return new CFFCharset(false, format, charset, raw);
    },
    parseEncoding: function CFFParser_parseEncoding(pos,
                                                    properties,
                                                    strings,
                                                    charset) {
      var encoding = {};
      var bytes = this.bytes;
      var predefined = false;
      var hasSupplement = false;
      var format, i, ii;
      var raw = null;

      function readSupplement() {
        var supplementsCount = bytes[pos++];
        for (i = 0; i < supplementsCount; i++) {
          var code = bytes[pos++];
          var sid = (bytes[pos++] << 8) + (bytes[pos++] & 0xff);
          encoding[code] = charset.indexOf(strings.get(sid));
        }
      }

      if (pos === 0 || pos === 1) {
        predefined = true;
        format = pos;
        var baseEncoding = pos ? Encodings.ExpertEncoding :
                                 Encodings.StandardEncoding;
        for (i = 0, ii = charset.length; i < ii; i++) {
          var index = baseEncoding.indexOf(charset[i]);
          if (index !== -1) {
            encoding[index] = i;
          }
        }
      } else {
        var dataStart = pos;
        format = bytes[pos++];
        switch (format & 0x7f) {
          case 0:
            var glyphsCount = bytes[pos++];
            for (i = 1; i <= glyphsCount; i++) {
              encoding[bytes[pos++]] = i;
            }
            break;

          case 1:
            var rangesCount = bytes[pos++];
            var gid = 1;
            for (i = 0; i < rangesCount; i++) {
              var start = bytes[pos++];
              var left = bytes[pos++];
              for (var j = start; j <= start + left; j++) {
                encoding[j] = gid++;
              }
            }
            break;

          default:
            error('Unknow encoding format: ' + format + ' in CFF');
            break;
        }
        var dataEnd = pos;
        if (format & 0x80) {
          // The font sanitizer does not support CFF encoding with a
          // supplement, since the encoding is not really used to map
          // between gid to glyph, let's overwrite what is declared in
          // the top dictionary to let the sanitizer think the font use
          // StandardEncoding, that's a lie but that's ok.
          bytes[dataStart] &= 0x7f;
          readSupplement();
          hasSupplement = true;
        }
        raw = bytes.subarray(dataStart, dataEnd);
      }
      format = format & 0x7f;
      return new CFFEncoding(predefined, format, encoding, raw);
    },
    parseFDSelect: function CFFParser_parseFDSelect(pos, length) {
      var start = pos;
      var bytes = this.bytes;
      var format = bytes[pos++];
      var fdSelect = [];
      var i;

      switch (format) {
        case 0:
          for (i = 0; i < length; ++i) {
            var id = bytes[pos++];
            fdSelect.push(id);
          }
          break;
        case 3:
          var rangesCount = (bytes[pos++] << 8) | bytes[pos++];
          for (i = 0; i < rangesCount; ++i) {
            var first = (bytes[pos++] << 8) | bytes[pos++];
            var fdIndex = bytes[pos++];
            var next = (bytes[pos] << 8) | bytes[pos + 1];
            for (var j = first; j < next; ++j) {
              fdSelect.push(fdIndex);
            }
          }
          // Advance past the sentinel(next).
          pos += 2;
          break;
        default:
          error('Unknown fdselect format ' + format);
          break;
      }
      var end = pos;
      return new CFFFDSelect(fdSelect, bytes.subarray(start, end));
    }
  };
  return CFFParser;
})();

// Compact Font Format
var CFF = (function CFFClosure() {
  function CFF() {
    this.header = null;
    this.names = [];
    this.topDict = null;
    this.strings = new CFFStrings();
    this.globalSubrIndex = null;

    // The following could really be per font, but since we only have one font
    // store them here.
    this.encoding = null;
    this.charset = null;
    this.charStrings = null;
    this.fdArray = [];
    this.fdSelect = null;

    this.isCIDFont = false;
  }
  return CFF;
})();

var CFFHeader = (function CFFHeaderClosure() {
  function CFFHeader(major, minor, hdrSize, offSize) {
    this.major = major;
    this.minor = minor;
    this.hdrSize = hdrSize;
    this.offSize = offSize;
  }
  return CFFHeader;
})();

var CFFStrings = (function CFFStringsClosure() {
  function CFFStrings() {
    this.strings = [];
  }
  CFFStrings.prototype = {
    get: function CFFStrings_get(index) {
      if (index >= 0 && index <= 390) {
        return CFFStandardStrings[index];
      }
      if (index - 391 <= this.strings.length) {
        return this.strings[index - 391];
      }
      return CFFStandardStrings[0];
    },
    add: function CFFStrings_add(value) {
      this.strings.push(value);
    },
    get count() {
      return this.strings.length;
    }
  };
  return CFFStrings;
})();

var CFFIndex = (function CFFIndexClosure() {
  function CFFIndex() {
    this.objects = [];
    this.length = 0;
  }
  CFFIndex.prototype = {
    add: function CFFIndex_add(data) {
      this.length += data.length;
      this.objects.push(data);
    },
    set: function CFFIndex_set(index, data) {
      this.length += data.length - this.objects[index].length;
      this.objects[index] = data;
    },
    get: function CFFIndex_get(index) {
      return this.objects[index];
    },
    get count() {
      return this.objects.length;
    }
  };
  return CFFIndex;
})();

var CFFDict = (function CFFDictClosure() {
  function CFFDict(tables, strings) {
    this.keyToNameMap = tables.keyToNameMap;
    this.nameToKeyMap = tables.nameToKeyMap;
    this.defaults = tables.defaults;
    this.types = tables.types;
    this.opcodes = tables.opcodes;
    this.order = tables.order;
    this.strings = strings;
    this.values = {};
  }
  CFFDict.prototype = {
    // value should always be an array
    setByKey: function CFFDict_setByKey(key, value) {
      if (!(key in this.keyToNameMap)) {
        return false;
      }
      // ignore empty values
      if (value.length === 0) {
        return true;
      }
      var type = this.types[key];
      // remove the array wrapping these types of values
      if (type === 'num' || type === 'sid' || type === 'offset') {
        value = value[0];
      }
      this.values[key] = value;
      return true;
    },
    setByName: function CFFDict_setByName(name, value) {
      if (!(name in this.nameToKeyMap)) {
        error('Invalid dictionary name "' + name + '"');
      }
      this.values[this.nameToKeyMap[name]] = value;
    },
    hasName: function CFFDict_hasName(name) {
      return this.nameToKeyMap[name] in this.values;
    },
    getByName: function CFFDict_getByName(name) {
      if (!(name in this.nameToKeyMap)) {
        error('Invalid dictionary name "' + name + '"');
      }
      var key = this.nameToKeyMap[name];
      if (!(key in this.values)) {
        return this.defaults[key];
      }
      return this.values[key];
    },
    removeByName: function CFFDict_removeByName(name) {
      delete this.values[this.nameToKeyMap[name]];
    }
  };
  CFFDict.createTables = function CFFDict_createTables(layout) {
    var tables = {
      keyToNameMap: {},
      nameToKeyMap: {},
      defaults: {},
      types: {},
      opcodes: {},
      order: []
    };
    for (var i = 0, ii = layout.length; i < ii; ++i) {
      var entry = layout[i];
      var key = isArray(entry[0]) ? (entry[0][0] << 8) + entry[0][1] : entry[0];
      tables.keyToNameMap[key] = entry[1];
      tables.nameToKeyMap[entry[1]] = key;
      tables.types[key] = entry[2];
      tables.defaults[key] = entry[3];
      tables.opcodes[key] = isArray(entry[0]) ? entry[0] : [entry[0]];
      tables.order.push(key);
    }
    return tables;
  };
  return CFFDict;
})();

var CFFTopDict = (function CFFTopDictClosure() {
  var layout = [
    [[12, 30], 'ROS', ['sid', 'sid', 'num'], null],
    [[12, 20], 'SyntheticBase', 'num', null],
    [0, 'version', 'sid', null],
    [1, 'Notice', 'sid', null],
    [[12, 0], 'Copyright', 'sid', null],
    [2, 'FullName', 'sid', null],
    [3, 'FamilyName', 'sid', null],
    [4, 'Weight', 'sid', null],
    [[12, 1], 'isFixedPitch', 'num', 0],
    [[12, 2], 'ItalicAngle', 'num', 0],
    [[12, 3], 'UnderlinePosition', 'num', -100],
    [[12, 4], 'UnderlineThickness', 'num', 50],
    [[12, 5], 'PaintType', 'num', 0],
    [[12, 6], 'CharstringType', 'num', 2],
    [[12, 7], 'FontMatrix', ['num', 'num', 'num', 'num', 'num', 'num'],
                            [0.001, 0, 0, 0.001, 0, 0]],
    [13, 'UniqueID', 'num', null],
    [5, 'FontBBox', ['num', 'num', 'num', 'num'], [0, 0, 0, 0]],
    [[12, 8], 'StrokeWidth', 'num', 0],
    [14, 'XUID', 'array', null],
    [15, 'charset', 'offset', 0],
    [16, 'Encoding', 'offset', 0],
    [17, 'CharStrings', 'offset', 0],
    [18, 'Private', ['offset', 'offset'], null],
    [[12, 21], 'PostScript', 'sid', null],
    [[12, 22], 'BaseFontName', 'sid', null],
    [[12, 23], 'BaseFontBlend', 'delta', null],
    [[12, 31], 'CIDFontVersion', 'num', 0],
    [[12, 32], 'CIDFontRevision', 'num', 0],
    [[12, 33], 'CIDFontType', 'num', 0],
    [[12, 34], 'CIDCount', 'num', 8720],
    [[12, 35], 'UIDBase', 'num', null],
    // XXX: CID Fonts on DirectWrite 6.1 only seem to work if FDSelect comes
    // before FDArray.
    [[12, 37], 'FDSelect', 'offset', null],
    [[12, 36], 'FDArray', 'offset', null],
    [[12, 38], 'FontName', 'sid', null]
  ];
  var tables = null;
  function CFFTopDict(strings) {
    if (tables === null) {
      tables = CFFDict.createTables(layout);
    }
    CFFDict.call(this, tables, strings);
    this.privateDict = null;
  }
  CFFTopDict.prototype = Object.create(CFFDict.prototype);
  return CFFTopDict;
})();

var CFFPrivateDict = (function CFFPrivateDictClosure() {
  var layout = [
    [6, 'BlueValues', 'delta', null],
    [7, 'OtherBlues', 'delta', null],
    [8, 'FamilyBlues', 'delta', null],
    [9, 'FamilyOtherBlues', 'delta', null],
    [[12, 9], 'BlueScale', 'num', 0.039625],
    [[12, 10], 'BlueShift', 'num', 7],
    [[12, 11], 'BlueFuzz', 'num', 1],
    [10, 'StdHW', 'num', null],
    [11, 'StdVW', 'num', null],
    [[12, 12], 'StemSnapH', 'delta', null],
    [[12, 13], 'StemSnapV', 'delta', null],
    [[12, 14], 'ForceBold', 'num', 0],
    [[12, 17], 'LanguageGroup', 'num', 0],
    [[12, 18], 'ExpansionFactor', 'num', 0.06],
    [[12, 19], 'initialRandomSeed', 'num', 0],
    [20, 'defaultWidthX', 'num', 0],
    [21, 'nominalWidthX', 'num', 0],
    [19, 'Subrs', 'offset', null]
  ];
  var tables = null;
  function CFFPrivateDict(strings) {
    if (tables === null) {
      tables = CFFDict.createTables(layout);
    }
    CFFDict.call(this, tables, strings);
    this.subrsIndex = null;
  }
  CFFPrivateDict.prototype = Object.create(CFFDict.prototype);
  return CFFPrivateDict;
})();

var CFFCharsetPredefinedTypes = {
  ISO_ADOBE: 0,
  EXPERT: 1,
  EXPERT_SUBSET: 2
};
var CFFCharset = (function CFFCharsetClosure() {
  function CFFCharset(predefined, format, charset, raw) {
    this.predefined = predefined;
    this.format = format;
    this.charset = charset;
    this.raw = raw;
  }
  return CFFCharset;
})();

var CFFEncoding = (function CFFEncodingClosure() {
  function CFFEncoding(predefined, format, encoding, raw) {
    this.predefined = predefined;
    this.format = format;
    this.encoding = encoding;
    this.raw = raw;
  }
  return CFFEncoding;
})();

var CFFFDSelect = (function CFFFDSelectClosure() {
  function CFFFDSelect(fdSelect, raw) {
    this.fdSelect = fdSelect;
    this.raw = raw;
  }
  return CFFFDSelect;
})();

// Helper class to keep track of where an offset is within the data and helps
// filling in that offset once it's known.
var CFFOffsetTracker = (function CFFOffsetTrackerClosure() {
  function CFFOffsetTracker() {
    this.offsets = {};
  }
  CFFOffsetTracker.prototype = {
    isTracking: function CFFOffsetTracker_isTracking(key) {
      return key in this.offsets;
    },
    track: function CFFOffsetTracker_track(key, location) {
      if (key in this.offsets) {
        error('Already tracking location of ' + key);
      }
      this.offsets[key] = location;
    },
    offset: function CFFOffsetTracker_offset(value) {
      for (var key in this.offsets) {
        this.offsets[key] += value;
      }
    },
    setEntryLocation: function CFFOffsetTracker_setEntryLocation(key,
                                                                 values,
                                                                 output) {
      if (!(key in this.offsets)) {
        error('Not tracking location of ' + key);
      }
      var data = output.data;
      var dataOffset = this.offsets[key];
      var size = 5;
      for (var i = 0, ii = values.length; i < ii; ++i) {
        var offset0 = i * size + dataOffset;
        var offset1 = offset0 + 1;
        var offset2 = offset0 + 2;
        var offset3 = offset0 + 3;
        var offset4 = offset0 + 4;
        // It's easy to screw up offsets so perform this sanity check.
        if (data[offset0] !== 0x1d || data[offset1] !== 0 ||
            data[offset2] !== 0 || data[offset3] !== 0 || data[offset4] !== 0) {
          error('writing to an offset that is not empty');
        }
        var value = values[i];
        data[offset0] = 0x1d;
        data[offset1] = (value >> 24) & 0xFF;
        data[offset2] = (value >> 16) & 0xFF;
        data[offset3] = (value >> 8) & 0xFF;
        data[offset4] = value & 0xFF;
      }
    }
  };
  return CFFOffsetTracker;
})();

// Takes a CFF and converts it to the binary representation.
var CFFCompiler = (function CFFCompilerClosure() {
  function CFFCompiler(cff) {
    this.cff = cff;
  }
  CFFCompiler.prototype = {
    compile: function CFFCompiler_compile() {
      var cff = this.cff;
      var output = {
        data: [],
        length: 0,
        add: function CFFCompiler_add(data) {
          this.data = this.data.concat(data);
          this.length = this.data.length;
        }
      };

      // Compile the five entries that must be in order.
      var header = this.compileHeader(cff.header);
      output.add(header);

      var nameIndex = this.compileNameIndex(cff.names);
      output.add(nameIndex);

      if (cff.isCIDFont) {
        // The spec is unclear on how font matrices should relate to each other
        // when there is one in the main top dict and the sub top dicts.
        // Windows handles this differently than linux and osx so we have to
        // normalize to work on all.
        // Rules based off of some mailing list discussions:
        // - If main font has a matrix and subfont doesn't, use the main matrix.
        // - If no main font matrix and there is a subfont matrix, use the
        //   subfont matrix.
        // - If both have matrices, concat together.
        // - If neither have matrices, use default.
        // To make this work on all platforms we move the top matrix into each
        // sub top dict and concat if necessary.
        if (cff.topDict.hasName('FontMatrix')) {
          var base = cff.topDict.getByName('FontMatrix');
          cff.topDict.removeByName('FontMatrix');
          for (var i = 0, ii = cff.fdArray.length; i < ii; i++) {
            var subDict = cff.fdArray[i];
            var matrix = base.slice(0);
            if (subDict.hasName('FontMatrix')) {
              matrix = Util.transform(matrix, subDict.getByName('FontMatrix'));
            }
            subDict.setByName('FontMatrix', matrix);
          }
        }
      }

      var compiled = this.compileTopDicts([cff.topDict],
                                          output.length,
                                          cff.isCIDFont);
      output.add(compiled.output);
      var topDictTracker = compiled.trackers[0];

      var stringIndex = this.compileStringIndex(cff.strings.strings);
      output.add(stringIndex);

      var globalSubrIndex = this.compileIndex(cff.globalSubrIndex);
      output.add(globalSubrIndex);

      // Now start on the other entries that have no specfic order.
      if (cff.encoding && cff.topDict.hasName('Encoding')) {
        if (cff.encoding.predefined) {
          topDictTracker.setEntryLocation('Encoding', [cff.encoding.format],
                                          output);
        } else {
          var encoding = this.compileEncoding(cff.encoding);
          topDictTracker.setEntryLocation('Encoding', [output.length], output);
          output.add(encoding);
        }
      }

      if (cff.charset && cff.topDict.hasName('charset')) {
        if (cff.charset.predefined) {
          topDictTracker.setEntryLocation('charset', [cff.charset.format],
                                          output);
        } else {
          var charset = this.compileCharset(cff.charset);
          topDictTracker.setEntryLocation('charset', [output.length], output);
          output.add(charset);
        }
      }

      var charStrings = this.compileCharStrings(cff.charStrings);
      topDictTracker.setEntryLocation('CharStrings', [output.length], output);
      output.add(charStrings);

      if (cff.isCIDFont) {
        // For some reason FDSelect must be in front of FDArray on windows. OSX
        // and linux don't seem to care.
        topDictTracker.setEntryLocation('FDSelect', [output.length], output);
        var fdSelect = this.compileFDSelect(cff.fdSelect.raw);
        output.add(fdSelect);
        // It is unclear if the sub font dictionary can have CID related
        // dictionary keys, but the sanitizer doesn't like them so remove them.
        compiled = this.compileTopDicts(cff.fdArray, output.length, true);
        topDictTracker.setEntryLocation('FDArray', [output.length], output);
        output.add(compiled.output);
        var fontDictTrackers = compiled.trackers;

        this.compilePrivateDicts(cff.fdArray, fontDictTrackers, output);
      }

      this.compilePrivateDicts([cff.topDict], [topDictTracker], output);

      // If the font data ends with INDEX whose object data is zero-length,
      // the sanitizer will bail out. Add a dummy byte to avoid that.
      output.add([0]);

      return output.data;
    },
    encodeNumber: function CFFCompiler_encodeNumber(value) {
      if (parseFloat(value) === parseInt(value, 10) && !isNaN(value)) { // isInt
        return this.encodeInteger(value);
      } else {
        return this.encodeFloat(value);
      }
    },
    encodeFloat: function CFFCompiler_encodeFloat(num) {
      var value = num.toString();

      // rounding inaccurate doubles
      var m = /\.(\d*?)(?:9{5,20}|0{5,20})\d{0,2}(?:e(.+)|$)/.exec(value);
      if (m) {
        var epsilon = parseFloat('1e' + ((m[2] ? +m[2] : 0) + m[1].length));
        value = (Math.round(num * epsilon) / epsilon).toString();
      }

      var nibbles = '';
      var i, ii;
      for (i = 0, ii = value.length; i < ii; ++i) {
        var a = value[i];
        if (a === 'e') {
          nibbles += value[++i] === '-' ? 'c' : 'b';
        } else if (a === '.') {
          nibbles += 'a';
        } else if (a === '-') {
          nibbles += 'e';
        } else {
          nibbles += a;
        }
      }
      nibbles += (nibbles.length & 1) ? 'f' : 'ff';
      var out = [30];
      for (i = 0, ii = nibbles.length; i < ii; i += 2) {
        out.push(parseInt(nibbles.substr(i, 2), 16));
      }
      return out;
    },
    encodeInteger: function CFFCompiler_encodeInteger(value) {
      var code;
      if (value >= -107 && value <= 107) {
        code = [value + 139];
      } else if (value >= 108 && value <= 1131) {
        value = [value - 108];
        code = [(value >> 8) + 247, value & 0xFF];
      } else if (value >= -1131 && value <= -108) {
        value = -value - 108;
        code = [(value >> 8) + 251, value & 0xFF];
      } else if (value >= -32768 && value <= 32767) {
        code = [0x1c, (value >> 8) & 0xFF, value & 0xFF];
      } else {
        code = [0x1d,
                (value >> 24) & 0xFF,
                (value >> 16) & 0xFF,
                (value >> 8) & 0xFF,
                 value & 0xFF];
      }
      return code;
    },
    compileHeader: function CFFCompiler_compileHeader(header) {
      return [
        header.major,
        header.minor,
        header.hdrSize,
        header.offSize
      ];
    },
    compileNameIndex: function CFFCompiler_compileNameIndex(names) {
      var nameIndex = new CFFIndex();
      for (var i = 0, ii = names.length; i < ii; ++i) {
        nameIndex.add(stringToBytes(names[i]));
      }
      return this.compileIndex(nameIndex);
    },
    compileTopDicts: function CFFCompiler_compileTopDicts(dicts,
                                                          length,
                                                          removeCidKeys) {
      var fontDictTrackers = [];
      var fdArrayIndex = new CFFIndex();
      for (var i = 0, ii = dicts.length; i < ii; ++i) {
        var fontDict = dicts[i];
        if (removeCidKeys) {
          fontDict.removeByName('CIDFontVersion');
          fontDict.removeByName('CIDFontRevision');
          fontDict.removeByName('CIDFontType');
          fontDict.removeByName('CIDCount');
          fontDict.removeByName('UIDBase');
        }
        var fontDictTracker = new CFFOffsetTracker();
        var fontDictData = this.compileDict(fontDict, fontDictTracker);
        fontDictTrackers.push(fontDictTracker);
        fdArrayIndex.add(fontDictData);
        fontDictTracker.offset(length);
      }
      fdArrayIndex = this.compileIndex(fdArrayIndex, fontDictTrackers);
      return {
        trackers: fontDictTrackers,
        output: fdArrayIndex
      };
    },
    compilePrivateDicts: function CFFCompiler_compilePrivateDicts(dicts,
                                                                  trackers,
                                                                  output) {
      for (var i = 0, ii = dicts.length; i < ii; ++i) {
        var fontDict = dicts[i];
        assert(fontDict.privateDict && fontDict.hasName('Private'),
               'There must be an private dictionary.');
        var privateDict = fontDict.privateDict;
        var privateDictTracker = new CFFOffsetTracker();
        var privateDictData = this.compileDict(privateDict, privateDictTracker);

        var outputLength = output.length;
        privateDictTracker.offset(outputLength);
        if (!privateDictData.length) {
          // The private dictionary was empty, set the output length to zero to
          // ensure the offset length isn't out of bounds in the eyes of the
          // sanitizer.
          outputLength = 0;
        }

        trackers[i].setEntryLocation('Private',
                                     [privateDictData.length, outputLength],
                                     output);
        output.add(privateDictData);

        if (privateDict.subrsIndex && privateDict.hasName('Subrs')) {
          var subrs = this.compileIndex(privateDict.subrsIndex);
          privateDictTracker.setEntryLocation('Subrs', [privateDictData.length],
                                              output);
          output.add(subrs);
        }
      }
    },
    compileDict: function CFFCompiler_compileDict(dict, offsetTracker) {
      var out = [];
      // The dictionary keys must be in a certain order.
      var order = dict.order;
      for (var i = 0; i < order.length; ++i) {
        var key = order[i];
        if (!(key in dict.values)) {
          continue;
        }
        var values = dict.values[key];
        var types = dict.types[key];
        if (!isArray(types)) {
          types = [types];
        }
        if (!isArray(values)) {
          values = [values];
        }

        // Remove any empty dict values.
        if (values.length === 0) {
          continue;
        }

        for (var j = 0, jj = types.length; j < jj; ++j) {
          var type = types[j];
          var value = values[j];
          switch (type) {
            case 'num':
            case 'sid':
              out = out.concat(this.encodeNumber(value));
              break;
            case 'offset':
              // For offsets we just insert a 32bit integer so we don't have to
              // deal with figuring out the length of the offset when it gets
              // replaced later on by the compiler.
              var name = dict.keyToNameMap[key];
              // Some offsets have the offset and the length, so just record the
              // position of the first one.
              if (!offsetTracker.isTracking(name)) {
                offsetTracker.track(name, out.length);
              }
              out = out.concat([0x1d, 0, 0, 0, 0]);
              break;
            case 'array':
            case 'delta':
              out = out.concat(this.encodeNumber(value));
              for (var k = 1, kk = values.length; k < kk; ++k) {
                out = out.concat(this.encodeNumber(values[k]));
              }
              break;
            default:
              error('Unknown data type of ' + type);
              break;
          }
        }
        out = out.concat(dict.opcodes[key]);
      }
      return out;
    },
    compileStringIndex: function CFFCompiler_compileStringIndex(strings) {
      var stringIndex = new CFFIndex();
      for (var i = 0, ii = strings.length; i < ii; ++i) {
        stringIndex.add(stringToBytes(strings[i]));
      }
      return this.compileIndex(stringIndex);
    },
    compileGlobalSubrIndex: function CFFCompiler_compileGlobalSubrIndex() {
      var globalSubrIndex = this.cff.globalSubrIndex;
      this.out.writeByteArray(this.compileIndex(globalSubrIndex));
    },
    compileCharStrings: function CFFCompiler_compileCharStrings(charStrings) {
      return this.compileIndex(charStrings);
    },
    compileCharset: function CFFCompiler_compileCharset(charset) {
      return this.compileTypedArray(charset.raw);
    },
    compileEncoding: function CFFCompiler_compileEncoding(encoding) {
      return this.compileTypedArray(encoding.raw);
    },
    compileFDSelect: function CFFCompiler_compileFDSelect(fdSelect) {
      return this.compileTypedArray(fdSelect);
    },
    compileTypedArray: function CFFCompiler_compileTypedArray(data) {
      var out = [];
      for (var i = 0, ii = data.length; i < ii; ++i) {
        out[i] = data[i];
      }
      return out;
    },
    compileIndex: function CFFCompiler_compileIndex(index, trackers) {
      trackers = trackers || [];
      var objects = index.objects;
      // First 2 bytes contains the number of objects contained into this index
      var count = objects.length;

      // If there is no object, just create an index. This technically
      // should just be [0, 0] but OTS has an issue with that.
      if (count === 0) {
        return [0, 0, 0];
      }

      var data = [(count >> 8) & 0xFF, count & 0xff];

      var lastOffset = 1, i;
      for (i = 0; i < count; ++i) {
        lastOffset += objects[i].length;
      }

      var offsetSize;
      if (lastOffset < 0x100) {
        offsetSize = 1;
      } else if (lastOffset < 0x10000) {
        offsetSize = 2;
      } else if (lastOffset < 0x1000000) {
        offsetSize = 3;
      } else {
        offsetSize = 4;
      }

      // Next byte contains the offset size use to reference object in the file
      data.push(offsetSize);

      // Add another offset after this one because we need a new offset
      var relativeOffset = 1;
      for (i = 0; i < count + 1; i++) {
        if (offsetSize === 1) {
          data.push(relativeOffset & 0xFF);
        } else if (offsetSize === 2) {
          data.push((relativeOffset >> 8) & 0xFF,
                     relativeOffset & 0xFF);
        } else if (offsetSize === 3) {
          data.push((relativeOffset >> 16) & 0xFF,
                    (relativeOffset >> 8) & 0xFF,
                     relativeOffset & 0xFF);
        } else {
          data.push((relativeOffset >>> 24) & 0xFF,
                    (relativeOffset >> 16) & 0xFF,
                    (relativeOffset >> 8) & 0xFF,
                     relativeOffset & 0xFF);
        }

        if (objects[i]) {
          relativeOffset += objects[i].length;
        }
      }

      for (i = 0; i < count; i++) {
        // Notify the tracker where the object will be offset in the data.
        if (trackers[i]) {
          trackers[i].offset(data.length);
        }
        for (var j = 0, jj = objects[i].length; j < jj; j++) {
          data.push(objects[i][j]);
        }
      }
      return data;
    }
  };
  return CFFCompiler;
})();

// Workaround for seac on Windows.
(function checkSeacSupport() {
  if (/Windows/.test(navigator.userAgent)) {
    SEAC_ANALYSIS_ENABLED = true;
  }
})();

// Workaround for Private Use Area characters in Chrome on Windows
// http://code.google.com/p/chromium/issues/detail?id=122465
// https://github.com/mozilla/pdf.js/issues/1689
(function checkChromeWindows() {
  if (/Windows.*Chrome/.test(navigator.userAgent)) {
    SKIP_PRIVATE_USE_RANGE_F000_TO_F01F = true;
  }
})();
