#codecs support
__all__=['RL_Codecs']
from collections import namedtuple
import codecs
StdCodecData=namedtuple('StdCodecData','exceptions rexceptions')
ExtCodecData=namedtuple('ExtCodecData','baseName exceptions rexceptions')
class RL_Codecs:
    __rl_codecs_data = {
        'winansi':StdCodecData({
            0x007f: 0x2022, # BULLET
            0x0080: 0x20ac, # EURO SIGN
            0x0081: 0x2022, # BULLET
            0x0082: 0x201a, # SINGLE LOW-9 QUOTATION MARK
            0x0083: 0x0192, # LATIN SMALL LETTER F WITH HOOK
            0x0084: 0x201e, # DOUBLE LOW-9 QUOTATION MARK
            0x0085: 0x2026, # HORIZONTAL ELLIPSIS
            0x0086: 0x2020, # DAGGER
            0x0087: 0x2021, # DOUBLE DAGGER
            0x0088: 0x02c6, # MODIFIER LETTER CIRCUMFLEX ACCENT
            0x0089: 0x2030, # PER MILLE SIGN
            0x008a: 0x0160, # LATIN CAPITAL LETTER S WITH CARON
            0x008b: 0x2039, # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
            0x008c: 0x0152, # LATIN CAPITAL LIGATURE OE
            0x008d: 0x2022, # BULLET
            0x008e: 0x017d, # LATIN CAPITAL LETTER Z WITH CARON
            0x008f: 0x2022, # BULLET
            0x0090: 0x2022, # BULLET
            0x0091: 0x2018, # LEFT SINGLE QUOTATION MARK
            0x0092: 0x2019, # RIGHT SINGLE QUOTATION MARK
            0x0093: 0x201c, # LEFT DOUBLE QUOTATION MARK
            0x0094: 0x201d, # RIGHT DOUBLE QUOTATION MARK
            0x0095: 0x2022, # BULLET
            0x0096: 0x2013, # EN DASH
            0x0097: 0x2014, # EM DASH
            0x0098: 0x02dc, # SMALL TILDE
            0x0099: 0x2122, # TRADE MARK SIGN
            0x009a: 0x0161, # LATIN SMALL LETTER S WITH CARON
            0x009b: 0x203a, # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
            0x009c: 0x0153, # LATIN SMALL LIGATURE OE
            0x009d: 0x2022, # BULLET
            0x009e: 0x017e, # LATIN SMALL LETTER Z WITH CARON
            0x009f: 0x0178, # LATIN CAPITAL LETTER Y WITH DIAERESIS
            0x00a0: 0x0020, # SPACE
            }, {0x2022:0x7f,0x20:0x20,0xa0:0x20}),
        'macroman':StdCodecData({
            0x007f: None, # UNDEFINED
            0x0080: 0x00c4, # LATIN CAPITAL LETTER A WITH DIAERESIS
            0x0081: 0x00c5, # LATIN CAPITAL LETTER A WITH RING ABOVE
            0x0082: 0x00c7, # LATIN CAPITAL LETTER C WITH CEDILLA
            0x0083: 0x00c9, # LATIN CAPITAL LETTER E WITH ACUTE
            0x0084: 0x00d1, # LATIN CAPITAL LETTER N WITH TILDE
            0x0085: 0x00d6, # LATIN CAPITAL LETTER O WITH DIAERESIS
            0x0086: 0x00dc, # LATIN CAPITAL LETTER U WITH DIAERESIS
            0x0087: 0x00e1, # LATIN SMALL LETTER A WITH ACUTE
            0x0088: 0x00e0, # LATIN SMALL LETTER A WITH GRAVE
            0x0089: 0x00e2, # LATIN SMALL LETTER A WITH CIRCUMFLEX
            0x008a: 0x00e4, # LATIN SMALL LETTER A WITH DIAERESIS
            0x008b: 0x00e3, # LATIN SMALL LETTER A WITH TILDE
            0x008c: 0x00e5, # LATIN SMALL LETTER A WITH RING ABOVE
            0x008d: 0x00e7, # LATIN SMALL LETTER C WITH CEDILLA
            0x008e: 0x00e9, # LATIN SMALL LETTER E WITH ACUTE
            0x008f: 0x00e8, # LATIN SMALL LETTER E WITH GRAVE
            0x0090: 0x00ea, # LATIN SMALL LETTER E WITH CIRCUMFLEX
            0x0091: 0x00eb, # LATIN SMALL LETTER E WITH DIAERESIS
            0x0092: 0x00ed, # LATIN SMALL LETTER I WITH ACUTE
            0x0093: 0x00ec, # LATIN SMALL LETTER I WITH GRAVE
            0x0094: 0x00ee, # LATIN SMALL LETTER I WITH CIRCUMFLEX
            0x0095: 0x00ef, # LATIN SMALL LETTER I WITH DIAERESIS
            0x0096: 0x00f1, # LATIN SMALL LETTER N WITH TILDE
            0x0097: 0x00f3, # LATIN SMALL LETTER O WITH ACUTE
            0x0098: 0x00f2, # LATIN SMALL LETTER O WITH GRAVE
            0x0099: 0x00f4, # LATIN SMALL LETTER O WITH CIRCUMFLEX
            0x009a: 0x00f6, # LATIN SMALL LETTER O WITH DIAERESIS
            0x009b: 0x00f5, # LATIN SMALL LETTER O WITH TILDE
            0x009c: 0x00fa, # LATIN SMALL LETTER U WITH ACUTE
            0x009d: 0x00f9, # LATIN SMALL LETTER U WITH GRAVE
            0x009e: 0x00fb, # LATIN SMALL LETTER U WITH CIRCUMFLEX
            0x009f: 0x00fc, # LATIN SMALL LETTER U WITH DIAERESIS
            0x00a0: 0x2020, # DAGGER
            0x00a1: 0x00b0, # DEGREE SIGN
            0x00a4: 0x00a7, # SECTION SIGN
            0x00a5: 0x2022, # BULLET
            0x00a6: 0x00b6, # PILCROW SIGN
            0x00a7: 0x00df, # LATIN SMALL LETTER SHARP S
            0x00a8: 0x00ae, # REGISTERED SIGN
            0x00aa: 0x2122, # TRADE MARK SIGN
            0x00ab: 0x00b4, # ACUTE ACCENT
            0x00ac: 0x00a8, # DIAERESIS
            0x00ad: None, # UNDEFINED
            0x00ae: 0x00c6, # LATIN CAPITAL LETTER AE
            0x00af: 0x00d8, # LATIN CAPITAL LETTER O WITH STROKE
            0x00b0: None, # UNDEFINED
            0x00b2: None, # UNDEFINED
            0x00b3: None, # UNDEFINED
            0x00b4: 0x00a5, # YEN SIGN
            0x00b6: None, # UNDEFINED
            0x00b7: None, # UNDEFINED
            0x00b8: None, # UNDEFINED
            0x00b9: None, # UNDEFINED
            0x00ba: None, # UNDEFINED
            0x00bb: 0x00aa, # FEMININE ORDINAL INDICATOR
            0x00bc: 0x00ba, # MASCULINE ORDINAL INDICATOR
            0x00bd: None, # UNDEFINED
            0x00be: 0x00e6, # LATIN SMALL LETTER AE
            0x00bf: 0x00f8, # LATIN SMALL LETTER O WITH STROKE
            0x00c0: 0x00bf, # INVERTED QUESTION MARK
            0x00c1: 0x00a1, # INVERTED EXCLAMATION MARK
            0x00c2: 0x00ac, # NOT SIGN
            0x00c3: None, # UNDEFINED
            0x00c4: 0x0192, # LATIN SMALL LETTER F WITH HOOK
            0x00c5: None, # UNDEFINED
            0x00c6: None, # UNDEFINED
            0x00c7: 0x00ab, # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
            0x00c8: 0x00bb, # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
            0x00c9: 0x2026, # HORIZONTAL ELLIPSIS
            0x00ca: 0x0020, # SPACE
            0x00cb: 0x00c0, # LATIN CAPITAL LETTER A WITH GRAVE
            0x00cc: 0x00c3, # LATIN CAPITAL LETTER A WITH TILDE
            0x00cd: 0x00d5, # LATIN CAPITAL LETTER O WITH TILDE
            0x00ce: 0x0152, # LATIN CAPITAL LIGATURE OE
            0x00cf: 0x0153, # LATIN SMALL LIGATURE OE
            0x00d0: 0x2013, # EN DASH
            0x00d1: 0x2014, # EM DASH
            0x00d2: 0x201c, # LEFT DOUBLE QUOTATION MARK
            0x00d3: 0x201d, # RIGHT DOUBLE QUOTATION MARK
            0x00d4: 0x2018, # LEFT SINGLE QUOTATION MARK
            0x00d5: 0x2019, # RIGHT SINGLE QUOTATION MARK
            0x00d6: 0x00f7, # DIVISION SIGN
            0x00d7: None, # UNDEFINED
            0x00d8: 0x00ff, # LATIN SMALL LETTER Y WITH DIAERESIS
            0x00d9: 0x0178, # LATIN CAPITAL LETTER Y WITH DIAERESIS
            0x00da: 0x2044, # FRACTION SLASH
            0x00db: 0x00a4, # CURRENCY SIGN
            0x00dc: 0x2039, # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
            0x00dd: 0x203a, # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
            0x00de: 0xfb01, # LATIN SMALL LIGATURE FI
            0x00df: 0xfb02, # LATIN SMALL LIGATURE FL
            0x00e0: 0x2021, # DOUBLE DAGGER
            0x00e1: 0x00b7, # MIDDLE DOT
            0x00e2: 0x201a, # SINGLE LOW-9 QUOTATION MARK
            0x00e3: 0x201e, # DOUBLE LOW-9 QUOTATION MARK
            0x00e4: 0x2030, # PER MILLE SIGN
            0x00e5: 0x00c2, # LATIN CAPITAL LETTER A WITH CIRCUMFLEX
            0x00e6: 0x00ca, # LATIN CAPITAL LETTER E WITH CIRCUMFLEX
            0x00e7: 0x00c1, # LATIN CAPITAL LETTER A WITH ACUTE
            0x00e8: 0x00cb, # LATIN CAPITAL LETTER E WITH DIAERESIS
            0x00e9: 0x00c8, # LATIN CAPITAL LETTER E WITH GRAVE
            0x00ea: 0x00cd, # LATIN CAPITAL LETTER I WITH ACUTE
            0x00eb: 0x00ce, # LATIN CAPITAL LETTER I WITH CIRCUMFLEX
            0x00ec: 0x00cf, # LATIN CAPITAL LETTER I WITH DIAERESIS
            0x00ed: 0x00cc, # LATIN CAPITAL LETTER I WITH GRAVE
            0x00ee: 0x00d3, # LATIN CAPITAL LETTER O WITH ACUTE
            0x00ef: 0x00d4, # LATIN CAPITAL LETTER O WITH CIRCUMFLEX
            0x00f0: None, # UNDEFINED
            0x00f1: 0x00d2, # LATIN CAPITAL LETTER O WITH GRAVE
            0x00f2: 0x00da, # LATIN CAPITAL LETTER U WITH ACUTE
            0x00f3: 0x00db, # LATIN CAPITAL LETTER U WITH CIRCUMFLEX
            0x00f4: 0x00d9, # LATIN CAPITAL LETTER U WITH GRAVE
            0x00f5: 0x0131, # LATIN SMALL LETTER DOTLESS I
            0x00f6: 0x02c6, # MODIFIER LETTER CIRCUMFLEX ACCENT
            0x00f7: 0x02dc, # SMALL TILDE
            0x00f8: 0x00af, # MACRON
            0x00f9: 0x02d8, # BREVE
            0x00fa: 0x02d9, # DOT ABOVE
            0x00fb: 0x02da, # RING ABOVE
            0x00fc: 0x00b8, # CEDILLA
            0x00fd: 0x02dd, # DOUBLE ACUTE ACCENT
            0x00fe: 0x02db, # OGONEK
            0x00ff: 0x02c7, # CARON
            },None),
    'standard':StdCodecData({
            0x0027: 0x2019, # RIGHT SINGLE QUOTATION MARK
            0x0060: 0x2018, # LEFT SINGLE QUOTATION MARK
            0x007f: None, # UNDEFINED
            0x0080: None, # UNDEFINED
            0x0081: None, # UNDEFINED
            0x0082: None, # UNDEFINED
            0x0083: None, # UNDEFINED
            0x0084: None, # UNDEFINED
            0x0085: None, # UNDEFINED
            0x0086: None, # UNDEFINED
            0x0087: None, # UNDEFINED
            0x0088: None, # UNDEFINED
            0x0089: None, # UNDEFINED
            0x008a: None, # UNDEFINED
            0x008b: None, # UNDEFINED
            0x008c: None, # UNDEFINED
            0x008d: None, # UNDEFINED
            0x008e: None, # UNDEFINED
            0x008f: None, # UNDEFINED
            0x0090: None, # UNDEFINED
            0x0091: None, # UNDEFINED
            0x0092: None, # UNDEFINED
            0x0093: None, # UNDEFINED
            0x0094: None, # UNDEFINED
            0x0095: None, # UNDEFINED
            0x0096: None, # UNDEFINED
            0x0097: None, # UNDEFINED
            0x0098: None, # UNDEFINED
            0x0099: None, # UNDEFINED
            0x009a: None, # UNDEFINED
            0x009b: None, # UNDEFINED
            0x009c: None, # UNDEFINED
            0x009d: None, # UNDEFINED
            0x009e: None, # UNDEFINED
            0x009f: None, # UNDEFINED
            0x00a0: None, # UNDEFINED
            0x00a4: 0x2044, # FRACTION SLASH
            0x00a6: 0x0192, # LATIN SMALL LETTER F WITH HOOK
            0x00a8: 0x00a4, # CURRENCY SIGN
            0x00a9: 0x0027, # APOSTROPHE
            0x00aa: 0x201c, # LEFT DOUBLE QUOTATION MARK
            0x00ac: 0x2039, # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
            0x00ad: 0x203a, # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
            0x00ae: 0xfb01, # LATIN SMALL LIGATURE FI
            0x00af: 0xfb02, # LATIN SMALL LIGATURE FL
            0x00b0: None, # UNDEFINED
            0x00b1: 0x2013, # EN DASH
            0x00b2: 0x2020, # DAGGER
            0x00b3: 0x2021, # DOUBLE DAGGER
            0x00b4: 0x00b7, # MIDDLE DOT
            0x00b5: None, # UNDEFINED
            0x00b7: 0x2022, # BULLET
            0x00b8: 0x201a, # SINGLE LOW-9 QUOTATION MARK
            0x00b9: 0x201e, # DOUBLE LOW-9 QUOTATION MARK
            0x00ba: 0x201d, # RIGHT DOUBLE QUOTATION MARK
            0x00bc: 0x2026, # HORIZONTAL ELLIPSIS
            0x00bd: 0x2030, # PER MILLE SIGN
            0x00be: None, # UNDEFINED
            0x00c0: None, # UNDEFINED
            0x00c1: 0x0060, # GRAVE ACCENT
            0x00c2: 0x00b4, # ACUTE ACCENT
            0x00c3: 0x02c6, # MODIFIER LETTER CIRCUMFLEX ACCENT
            0x00c4: 0x02dc, # SMALL TILDE
            0x00c5: 0x00af, # MACRON
            0x00c6: 0x02d8, # BREVE
            0x00c7: 0x02d9, # DOT ABOVE
            0x00c8: 0x00a8, # DIAERESIS
            0x00c9: None, # UNDEFINED
            0x00ca: 0x02da, # RING ABOVE
            0x00cb: 0x00b8, # CEDILLA
            0x00cc: None, # UNDEFINED
            0x00cd: 0x02dd, # DOUBLE ACUTE ACCENT
            0x00ce: 0x02db, # OGONEK
            0x00cf: 0x02c7, # CARON
            0x00d0: 0x2014, # EM DASH
            0x00d1: None, # UNDEFINED
            0x00d2: None, # UNDEFINED
            0x00d3: None, # UNDEFINED
            0x00d4: None, # UNDEFINED
            0x00d5: None, # UNDEFINED
            0x00d6: None, # UNDEFINED
            0x00d7: None, # UNDEFINED
            0x00d8: None, # UNDEFINED
            0x00d9: None, # UNDEFINED
            0x00da: None, # UNDEFINED
            0x00db: None, # UNDEFINED
            0x00dc: None, # UNDEFINED
            0x00dd: None, # UNDEFINED
            0x00de: None, # UNDEFINED
            0x00df: None, # UNDEFINED
            0x00e0: None, # UNDEFINED
            0x00e1: 0x00c6, # LATIN CAPITAL LETTER AE
            0x00e2: None, # UNDEFINED
            0x00e3: 0x00aa, # FEMININE ORDINAL INDICATOR
            0x00e4: None, # UNDEFINED
            0x00e5: None, # UNDEFINED
            0x00e6: None, # UNDEFINED
            0x00e7: None, # UNDEFINED
            0x00e8: 0x0141, # LATIN CAPITAL LETTER L WITH STROKE
            0x00e9: 0x00d8, # LATIN CAPITAL LETTER O WITH STROKE
            0x00ea: 0x0152, # LATIN CAPITAL LIGATURE OE
            0x00eb: 0x00ba, # MASCULINE ORDINAL INDICATOR
            0x00ec: None, # UNDEFINED
            0x00ed: None, # UNDEFINED
            0x00ee: None, # UNDEFINED
            0x00ef: None, # UNDEFINED
            0x00f0: None, # UNDEFINED
            0x00f1: 0x00e6, # LATIN SMALL LETTER AE
            0x00f2: None, # UNDEFINED
            0x00f3: None, # UNDEFINED
            0x00f4: None, # UNDEFINED
            0x00f5: 0x0131, # LATIN SMALL LETTER DOTLESS I
            0x00f6: None, # UNDEFINED
            0x00f7: None, # UNDEFINED
            0x00f8: 0x0142, # LATIN SMALL LETTER L WITH STROKE
            0x00f9: 0x00f8, # LATIN SMALL LETTER O WITH STROKE
            0x00fa: 0x0153, # LATIN SMALL LIGATURE OE
            0x00fb: 0x00df, # LATIN SMALL LETTER SHARP S
            0x00fc: None, # UNDEFINED
            0x00fd: None, # UNDEFINED
            0x00fe: None, # UNDEFINED
            0x00ff: None, # UNDEFINED
            },None),
    'symbol':StdCodecData({
            0x0022: 0x2200, # FOR ALL
            0x0024: 0x2203, # THERE EXISTS
            0x0027: 0x220b, # CONTAINS AS MEMBER
            0x002a: 0x2217, # ASTERISK OPERATOR
            0x002d: 0x2212, # MINUS SIGN
            0x0040: 0x2245, # APPROXIMATELY EQUAL TO
            0x0041: 0x0391, # GREEK CAPITAL LETTER ALPHA
            0x0042: 0x0392, # GREEK CAPITAL LETTER BETA
            0x0043: 0x03a7, # GREEK CAPITAL LETTER CHI
            0x0044: 0x2206, # INCREMENT
            0x0045: 0x0395, # GREEK CAPITAL LETTER EPSILON
            0x0046: 0x03a6, # GREEK CAPITAL LETTER PHI
            0x0047: 0x0393, # GREEK CAPITAL LETTER GAMMA
            0x0048: 0x0397, # GREEK CAPITAL LETTER ETA
            0x0049: 0x0399, # GREEK CAPITAL LETTER IOTA
            0x004a: 0x03d1, # GREEK THETA SYMBOL
            0x004b: 0x039a, # GREEK CAPITAL LETTER KAPPA
            0x004c: 0x039b, # GREEK CAPITAL LETTER LAMDA
            0x004d: 0x039c, # GREEK CAPITAL LETTER MU
            0x004e: 0x039d, # GREEK CAPITAL LETTER NU
            0x004f: 0x039f, # GREEK CAPITAL LETTER OMICRON
            0x0050: 0x03a0, # GREEK CAPITAL LETTER PI
            0x0051: 0x0398, # GREEK CAPITAL LETTER THETA
            0x0052: 0x03a1, # GREEK CAPITAL LETTER RHO
            0x0053: 0x03a3, # GREEK CAPITAL LETTER SIGMA
            0x0054: 0x03a4, # GREEK CAPITAL LETTER TAU
            0x0055: 0x03a5, # GREEK CAPITAL LETTER UPSILON
            0x0056: 0x03c2, # GREEK SMALL LETTER FINAL SIGMA
            0x0057: 0x2126, # OHM SIGN
            0x0058: 0x039e, # GREEK CAPITAL LETTER XI
            0x0059: 0x03a8, # GREEK CAPITAL LETTER PSI
            0x005a: 0x0396, # GREEK CAPITAL LETTER ZETA
            0x005c: 0x2234, # THEREFORE
            0x005e: 0x22a5, # UP TACK
            0x0060: 0xf8e5, # [unknown unicode name for radicalex]
            0x0061: 0x03b1, # GREEK SMALL LETTER ALPHA
            0x0062: 0x03b2, # GREEK SMALL LETTER BETA
            0x0063: 0x03c7, # GREEK SMALL LETTER CHI
            0x0064: 0x03b4, # GREEK SMALL LETTER DELTA
            0x0065: 0x03b5, # GREEK SMALL LETTER EPSILON
            0x0066: 0x03c6, # GREEK SMALL LETTER PHI
            0x0067: 0x03b3, # GREEK SMALL LETTER GAMMA
            0x0068: 0x03b7, # GREEK SMALL LETTER ETA
            0x0069: 0x03b9, # GREEK SMALL LETTER IOTA
            0x006a: 0x03d5, # GREEK PHI SYMBOL
            0x006b: 0x03ba, # GREEK SMALL LETTER KAPPA
            0x006c: 0x03bb, # GREEK SMALL LETTER LAMDA
            0x006d: 0x00b5, # MICRO SIGN
            0x006e: 0x03bd, # GREEK SMALL LETTER NU
            0x006f: 0x03bf, # GREEK SMALL LETTER OMICRON
            0x0070: 0x03c0, # GREEK SMALL LETTER PI
            0x0071: 0x03b8, # GREEK SMALL LETTER THETA
            0x0072: 0x03c1, # GREEK SMALL LETTER RHO
            0x0073: 0x03c3, # GREEK SMALL LETTER SIGMA
            0x0074: 0x03c4, # GREEK SMALL LETTER TAU
            0x0075: 0x03c5, # GREEK SMALL LETTER UPSILON
            0x0076: 0x03d6, # GREEK PI SYMBOL
            0x0077: 0x03c9, # GREEK SMALL LETTER OMEGA
            0x0078: 0x03be, # GREEK SMALL LETTER XI
            0x0079: 0x03c8, # GREEK SMALL LETTER PSI
            0x007a: 0x03b6, # GREEK SMALL LETTER ZETA
            0x007e: 0x223c, # TILDE OPERATOR
            0x007f: None, # UNDEFINED
            0x0080: None, # UNDEFINED
            0x0081: None, # UNDEFINED
            0x0082: None, # UNDEFINED
            0x0083: None, # UNDEFINED
            0x0084: None, # UNDEFINED
            0x0085: None, # UNDEFINED
            0x0086: None, # UNDEFINED
            0x0087: None, # UNDEFINED
            0x0088: None, # UNDEFINED
            0x0089: None, # UNDEFINED
            0x008a: None, # UNDEFINED
            0x008b: None, # UNDEFINED
            0x008c: None, # UNDEFINED
            0x008d: None, # UNDEFINED
            0x008e: None, # UNDEFINED
            0x008f: None, # UNDEFINED
            0x0090: None, # UNDEFINED
            0x0091: None, # UNDEFINED
            0x0092: None, # UNDEFINED
            0x0093: None, # UNDEFINED
            0x0094: None, # UNDEFINED
            0x0095: None, # UNDEFINED
            0x0096: None, # UNDEFINED
            0x0097: None, # UNDEFINED
            0x0098: None, # UNDEFINED
            0x0099: None, # UNDEFINED
            0x009a: None, # UNDEFINED
            0x009b: None, # UNDEFINED
            0x009c: None, # UNDEFINED
            0x009d: None, # UNDEFINED
            0x009e: None, # UNDEFINED
            0x009f: None, # UNDEFINED
            0x00a0: 0x20ac, # EURO SIGN
            0x00a1: 0x03d2, # GREEK UPSILON WITH HOOK SYMBOL
            0x00a2: 0x2032, # PRIME
            0x00a3: 0x2264, # LESS-THAN OR EQUAL TO
            0x00a4: 0x2044, # FRACTION SLASH
            0x00a5: 0x221e, # INFINITY
            0x00a6: 0x0192, # LATIN SMALL LETTER F WITH HOOK
            0x00a7: 0x2663, # BLACK CLUB SUIT
            0x00a8: 0x2666, # BLACK DIAMOND SUIT
            0x00a9: 0x2665, # BLACK HEART SUIT
            0x00aa: 0x2660, # BLACK SPADE SUIT
            0x00ab: 0x2194, # LEFT RIGHT ARROW
            0x00ac: 0x2190, # LEFTWARDS ARROW
            0x00ad: 0x2191, # UPWARDS ARROW
            0x00ae: 0x2192, # RIGHTWARDS ARROW
            0x00af: 0x2193, # DOWNWARDS ARROW
            0x00b2: 0x2033, # DOUBLE PRIME
            0x00b3: 0x2265, # GREATER-THAN OR EQUAL TO
            0x00b4: 0x00d7, # MULTIPLICATION SIGN
            0x00b5: 0x221d, # PROPORTIONAL TO
            0x00b6: 0x2202, # PARTIAL DIFFERENTIAL
            0x00b7: 0x2022, # BULLET
            0x00b8: 0x00f7, # DIVISION SIGN
            0x00b9: 0x2260, # NOT EQUAL TO
            0x00ba: 0x2261, # IDENTICAL TO
            0x00bb: 0x2248, # ALMOST EQUAL TO
            0x00bc: 0x2026, # HORIZONTAL ELLIPSIS
            0x00bd: 0xf8e6, # [unknown unicode name for arrowvertex]
            0x00be: 0xf8e7, # [unknown unicode name for arrowhorizex]
            0x00bf: 0x21b5, # DOWNWARDS ARROW WITH CORNER LEFTWARDS
            0x00c0: 0x2135, # ALEF SYMBOL
            0x00c1: 0x2111, # BLACK-LETTER CAPITAL I
            0x00c2: 0x211c, # BLACK-LETTER CAPITAL R
            0x00c3: 0x2118, # SCRIPT CAPITAL P
            0x00c4: 0x2297, # CIRCLED TIMES
            0x00c5: 0x2295, # CIRCLED PLUS
            0x00c6: 0x2205, # EMPTY SET
            0x00c7: 0x2229, # INTERSECTION
            0x00c8: 0x222a, # UNION
            0x00c9: 0x2283, # SUPERSET OF
            0x00ca: 0x2287, # SUPERSET OF OR EQUAL TO
            0x00cb: 0x2284, # NOT A SUBSET OF
            0x00cc: 0x2282, # SUBSET OF
            0x00cd: 0x2286, # SUBSET OF OR EQUAL TO
            0x00ce: 0x2208, # ELEMENT OF
            0x00cf: 0x2209, # NOT AN ELEMENT OF
            0x00d0: 0x2220, # ANGLE
            0x00d1: 0x2207, # NABLA
            0x00d2: 0xf6da, # [unknown unicode name for registerserif]
            0x00d3: 0xf6d9, # [unknown unicode name for copyrightserif]
            0x00d4: 0xf6db, # [unknown unicode name for trademarkserif]
            0x00d5: 0x220f, # N-ARY PRODUCT
            0x00d6: 0x221a, # SQUARE ROOT
            0x00d7: 0x22c5, # DOT OPERATOR
            0x00d8: 0x00ac, # NOT SIGN
            0x00d9: 0x2227, # LOGICAL AND
            0x00da: 0x2228, # LOGICAL OR
            0x00db: 0x21d4, # LEFT RIGHT DOUBLE ARROW
            0x00dc: 0x21d0, # LEFTWARDS DOUBLE ARROW
            0x00dd: 0x21d1, # UPWARDS DOUBLE ARROW
            0x00de: 0x21d2, # RIGHTWARDS DOUBLE ARROW
            0x00df: 0x21d3, # DOWNWARDS DOUBLE ARROW
            0x00e0: 0x25ca, # LOZENGE
            0x00e1: 0x2329, # LEFT-POINTING ANGLE BRACKET
            0x00e2: 0xf8e8, # [unknown unicode name for registersans]
            0x00e3: 0xf8e9, # [unknown unicode name for copyrightsans]
            0x00e4: 0xf8ea, # [unknown unicode name for trademarksans]
            0x00e5: 0x2211, # N-ARY SUMMATION
            0x00e6: 0xf8eb, # [unknown unicode name for parenlefttp]
            0x00e7: 0xf8ec, # [unknown unicode name for parenleftex]
            0x00e8: 0xf8ed, # [unknown unicode name for parenleftbt]
            0x00e9: 0xf8ee, # [unknown unicode name for bracketlefttp]
            0x00ea: 0xf8ef, # [unknown unicode name for bracketleftex]
            0x00eb: 0xf8f0, # [unknown unicode name for bracketleftbt]
            0x00ec: 0xf8f1, # [unknown unicode name for bracelefttp]
            0x00ed: 0xf8f2, # [unknown unicode name for braceleftmid]
            0x00ee: 0xf8f3, # [unknown unicode name for braceleftbt]
            0x00ef: 0xf8f4, # [unknown unicode name for braceex]
            0x00f0: None, # UNDEFINED
            0x00f1: 0x232a, # RIGHT-POINTING ANGLE BRACKET
            0x00f2: 0x222b, # INTEGRAL
            0x00f3: 0x2320, # TOP HALF INTEGRAL
            0x00f4: 0xf8f5, # [unknown unicode name for integralex]
            0x00f5: 0x2321, # BOTTOM HALF INTEGRAL
            0x00f6: 0xf8f6, # [unknown unicode name for parenrighttp]
            0x00f7: 0xf8f7, # [unknown unicode name for parenrightex]
            0x00f8: 0xf8f8, # [unknown unicode name for parenrightbt]
            0x00f9: 0xf8f9, # [unknown unicode name for bracketrighttp]
            0x00fa: 0xf8fa, # [unknown unicode name for bracketrightex]
            0x00fb: 0xf8fb, # [unknown unicode name for bracketrightbt]
            0x00fc: 0xf8fc, # [unknown unicode name for bracerighttp]
            0x00fd: 0xf8fd, # [unknown unicode name for bracerightmid]
            0x00fe: 0xf8fe, # [unknown unicode name for bracerightbt]
            0x00ff: None, # UNDEFINED
            },
            {
            0x0394:0x0044, # GREEK CAPITAL LETTER DELTA
            0x03a9:0x0057, # GREEK CAPITAL LETTER OMEGA
            0x03bc:0x006d, # GREEK SMALL LETTER MU
            }
            ),
    'zapfdingbats':StdCodecData({
            0x0021: 0x2701, # UPPER BLADE SCISSORS
            0x0022: 0x2702, # BLACK SCISSORS
            0x0023: 0x2703, # LOWER BLADE SCISSORS
            0x0024: 0x2704, # WHITE SCISSORS
            0x0025: 0x260e, # BLACK TELEPHONE
            0x0026: 0x2706, # TELEPHONE LOCATION SIGN
            0x0027: 0x2707, # TAPE DRIVE
            0x0028: 0x2708, # AIRPLANE
            0x0029: 0x2709, # ENVELOPE
            0x002a: 0x261b, # BLACK RIGHT POINTING INDEX
            0x002b: 0x261e, # WHITE RIGHT POINTING INDEX
            0x002c: 0x270c, # VICTORY HAND
            0x002d: 0x270d, # WRITING HAND
            0x002e: 0x270e, # LOWER RIGHT PENCIL
            0x002f: 0x270f, # PENCIL
            0x0030: 0x2710, # UPPER RIGHT PENCIL
            0x0031: 0x2711, # WHITE NIB
            0x0032: 0x2712, # BLACK NIB
            0x0033: 0x2713, # CHECK MARK
            0x0034: 0x2714, # HEAVY CHECK MARK
            0x0035: 0x2715, # MULTIPLICATION X
            0x0036: 0x2716, # HEAVY MULTIPLICATION X
            0x0037: 0x2717, # BALLOT X
            0x0038: 0x2718, # HEAVY BALLOT X
            0x0039: 0x2719, # OUTLINED GREEK CROSS
            0x003a: 0x271a, # HEAVY GREEK CROSS
            0x003b: 0x271b, # OPEN CENTRE CROSS
            0x003c: 0x271c, # HEAVY OPEN CENTRE CROSS
            0x003d: 0x271d, # LATIN CROSS
            0x003e: 0x271e, # SHADOWED WHITE LATIN CROSS
            0x003f: 0x271f, # OUTLINED LATIN CROSS
            0x0040: 0x2720, # MALTESE CROSS
            0x0041: 0x2721, # STAR OF DAVID
            0x0042: 0x2722, # FOUR TEARDROP-SPOKED ASTERISK
            0x0043: 0x2723, # FOUR BALLOON-SPOKED ASTERISK
            0x0044: 0x2724, # HEAVY FOUR BALLOON-SPOKED ASTERISK
            0x0045: 0x2725, # FOUR CLUB-SPOKED ASTERISK
            0x0046: 0x2726, # BLACK FOUR POINTED STAR
            0x0047: 0x2727, # WHITE FOUR POINTED STAR
            0x0048: 0x2605, # BLACK STAR
            0x0049: 0x2729, # STRESS OUTLINED WHITE STAR
            0x004a: 0x272a, # CIRCLED WHITE STAR
            0x004b: 0x272b, # OPEN CENTRE BLACK STAR
            0x004c: 0x272c, # BLACK CENTRE WHITE STAR
            0x004d: 0x272d, # OUTLINED BLACK STAR
            0x004e: 0x272e, # HEAVY OUTLINED BLACK STAR
            0x004f: 0x272f, # PINWHEEL STAR
            0x0050: 0x2730, # SHADOWED WHITE STAR
            0x0051: 0x2731, # HEAVY ASTERISK
            0x0052: 0x2732, # OPEN CENTRE ASTERISK
            0x0053: 0x2733, # EIGHT SPOKED ASTERISK
            0x0054: 0x2734, # EIGHT POINTED BLACK STAR
            0x0055: 0x2735, # EIGHT POINTED PINWHEEL STAR
            0x0056: 0x2736, # SIX POINTED BLACK STAR
            0x0057: 0x2737, # EIGHT POINTED RECTILINEAR BLACK STAR
            0x0058: 0x2738, # HEAVY EIGHT POINTED RECTILINEAR BLACK STAR
            0x0059: 0x2739, # TWELVE POINTED BLACK STAR
            0x005a: 0x273a, # SIXTEEN POINTED ASTERISK
            0x005b: 0x273b, # TEARDROP-SPOKED ASTERISK
            0x005c: 0x273c, # OPEN CENTRE TEARDROP-SPOKED ASTERISK
            0x005d: 0x273d, # HEAVY TEARDROP-SPOKED ASTERISK
            0x005e: 0x273e, # SIX PETALLED BLACK AND WHITE FLORETTE
            0x005f: 0x273f, # BLACK FLORETTE
            0x0060: 0x2740, # WHITE FLORETTE
            0x0061: 0x2741, # EIGHT PETALLED OUTLINED BLACK FLORETTE
            0x0062: 0x2742, # CIRCLED OPEN CENTRE EIGHT POINTED STAR
            0x0063: 0x2743, # HEAVY TEARDROP-SPOKED PINWHEEL ASTERISK
            0x0064: 0x2744, # SNOWFLAKE
            0x0065: 0x2745, # TIGHT TRIFOLIATE SNOWFLAKE
            0x0066: 0x2746, # HEAVY CHEVRON SNOWFLAKE
            0x0067: 0x2747, # SPARKLE
            0x0068: 0x2748, # HEAVY SPARKLE
            0x0069: 0x2749, # BALLOON-SPOKED ASTERISK
            0x006a: 0x274a, # EIGHT TEARDROP-SPOKED PROPELLER ASTERISK
            0x006b: 0x274b, # HEAVY EIGHT TEARDROP-SPOKED PROPELLER ASTERISK
            0x006c: 0x25cf, # BLACK CIRCLE
            0x006d: 0x274d, # SHADOWED WHITE CIRCLE
            0x006e: 0x25a0, # BLACK SQUARE
            0x006f: 0x274f, # LOWER RIGHT DROP-SHADOWED WHITE SQUARE
            0x0070: 0x2750, # UPPER RIGHT DROP-SHADOWED WHITE SQUARE
            0x0071: 0x2751, # LOWER RIGHT SHADOWED WHITE SQUARE
            0x0072: 0x2752, # UPPER RIGHT SHADOWED WHITE SQUARE
            0x0073: 0x25b2, # BLACK UP-POINTING TRIANGLE
            0x0074: 0x25bc, # BLACK DOWN-POINTING TRIANGLE
            0x0075: 0x25c6, # BLACK DIAMOND
            0x0076: 0x2756, # BLACK DIAMOND MINUS WHITE X
            0x0077: 0x25d7, # RIGHT HALF BLACK CIRCLE
            0x0078: 0x2758, # LIGHT VERTICAL BAR
            0x0079: 0x2759, # MEDIUM VERTICAL BAR
            0x007a: 0x275a, # HEAVY VERTICAL BAR
            0x007b: 0x275b, # HEAVY SINGLE TURNED COMMA QUOTATION MARK ORNAMENT
            0x007c: 0x275c, # HEAVY SINGLE COMMA QUOTATION MARK ORNAMENT
            0x007d: 0x275d, # HEAVY DOUBLE TURNED COMMA QUOTATION MARK ORNAMENT
            0x007e: 0x275e, # HEAVY DOUBLE COMMA QUOTATION MARK ORNAMENT
            0x007f: None, # UNDEFINED
            0x0080: 0x2768, # MEDIUM LEFT PARENTHESIS ORNAMENT
            0x0081: 0x2769, # MEDIUM RIGHT PARENTHESIS ORNAMENT
            0x0082: 0x276a, # MEDIUM FLATTENED LEFT PARENTHESIS ORNAMENT
            0x0083: 0x276b, # MEDIUM FLATTENED RIGHT PARENTHESIS ORNAMENT
            0x0084: 0x276c, # MEDIUM LEFT-POINTING ANGLE BRACKET ORNAMENT
            0x0085: 0x276d, # MEDIUM RIGHT-POINTING ANGLE BRACKET ORNAMENT
            0x0086: 0x276e, # HEAVY LEFT-POINTING ANGLE QUOTATION MARK ORNAMENT
            0x0087: 0x276f, # HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT
            0x0088: 0x2770, # HEAVY LEFT-POINTING ANGLE BRACKET ORNAMENT
            0x0089: 0x2771, # HEAVY RIGHT-POINTING ANGLE BRACKET ORNAMENT
            0x008a: 0x2772, # LIGHT LEFT TORTOISE SHELL BRACKET ORNAMENT
            0x008b: 0x2773, # LIGHT RIGHT TORTOISE SHELL BRACKET ORNAMENT
            0x008c: 0x2774, # MEDIUM LEFT CURLY BRACKET ORNAMENT
            0x008d: 0x2775, # MEDIUM RIGHT CURLY BRACKET ORNAMENT
            0x008e: None, # UNDEFINED
            0x008f: None, # UNDEFINED
            0x0090: None, # UNDEFINED
            0x0091: None, # UNDEFINED
            0x0092: None, # UNDEFINED
            0x0093: None, # UNDEFINED
            0x0094: None, # UNDEFINED
            0x0095: None, # UNDEFINED
            0x0096: None, # UNDEFINED
            0x0097: None, # UNDEFINED
            0x0098: None, # UNDEFINED
            0x0099: None, # UNDEFINED
            0x009a: None, # UNDEFINED
            0x009b: None, # UNDEFINED
            0x009c: None, # UNDEFINED
            0x009d: None, # UNDEFINED
            0x009e: None, # UNDEFINED
            0x009f: None, # UNDEFINED
            0x00a0: None, # UNDEFINED
            0x00a1: 0x2761, # CURVED STEM PARAGRAPH SIGN ORNAMENT
            0x00a2: 0x2762, # HEAVY EXCLAMATION MARK ORNAMENT
            0x00a3: 0x2763, # HEAVY HEART EXCLAMATION MARK ORNAMENT
            0x00a4: 0x2764, # HEAVY BLACK HEART
            0x00a5: 0x2765, # ROTATED HEAVY BLACK HEART BULLET
            0x00a6: 0x2766, # FLORAL HEART
            0x00a7: 0x2767, # ROTATED FLORAL HEART BULLET
            0x00a8: 0x2663, # BLACK CLUB SUIT
            0x00a9: 0x2666, # BLACK DIAMOND SUIT
            0x00aa: 0x2665, # BLACK HEART SUIT
            0x00ab: 0x2660, # BLACK SPADE SUIT
            0x00ac: 0x2460, # CIRCLED DIGIT ONE
            0x00ad: 0x2461, # CIRCLED DIGIT TWO
            0x00ae: 0x2462, # CIRCLED DIGIT THREE
            0x00af: 0x2463, # CIRCLED DIGIT FOUR
            0x00b0: 0x2464, # CIRCLED DIGIT FIVE
            0x00b1: 0x2465, # CIRCLED DIGIT SIX
            0x00b2: 0x2466, # CIRCLED DIGIT SEVEN
            0x00b3: 0x2467, # CIRCLED DIGIT EIGHT
            0x00b4: 0x2468, # CIRCLED DIGIT NINE
            0x00b5: 0x2469, # CIRCLED NUMBER TEN
            0x00b6: 0x2776, # DINGBAT NEGATIVE CIRCLED DIGIT ONE
            0x00b7: 0x2777, # DINGBAT NEGATIVE CIRCLED DIGIT TWO
            0x00b8: 0x2778, # DINGBAT NEGATIVE CIRCLED DIGIT THREE
            0x00b9: 0x2779, # DINGBAT NEGATIVE CIRCLED DIGIT FOUR
            0x00ba: 0x277a, # DINGBAT NEGATIVE CIRCLED DIGIT FIVE
            0x00bb: 0x277b, # DINGBAT NEGATIVE CIRCLED DIGIT SIX
            0x00bc: 0x277c, # DINGBAT NEGATIVE CIRCLED DIGIT SEVEN
            0x00bd: 0x277d, # DINGBAT NEGATIVE CIRCLED DIGIT EIGHT
            0x00be: 0x277e, # DINGBAT NEGATIVE CIRCLED DIGIT NINE
            0x00bf: 0x277f, # DINGBAT NEGATIVE CIRCLED NUMBER TEN
            0x00c0: 0x2780, # DINGBAT CIRCLED SANS-SERIF DIGIT ONE
            0x00c1: 0x2781, # DINGBAT CIRCLED SANS-SERIF DIGIT TWO
            0x00c2: 0x2782, # DINGBAT CIRCLED SANS-SERIF DIGIT THREE
            0x00c3: 0x2783, # DINGBAT CIRCLED SANS-SERIF DIGIT FOUR
            0x00c4: 0x2784, # DINGBAT CIRCLED SANS-SERIF DIGIT FIVE
            0x00c5: 0x2785, # DINGBAT CIRCLED SANS-SERIF DIGIT SIX
            0x00c6: 0x2786, # DINGBAT CIRCLED SANS-SERIF DIGIT SEVEN
            0x00c7: 0x2787, # DINGBAT CIRCLED SANS-SERIF DIGIT EIGHT
            0x00c8: 0x2788, # DINGBAT CIRCLED SANS-SERIF DIGIT NINE
            0x00c9: 0x2789, # DINGBAT CIRCLED SANS-SERIF NUMBER TEN
            0x00ca: 0x278a, # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT ONE
            0x00cb: 0x278b, # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT TWO
            0x00cc: 0x278c, # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT THREE
            0x00cd: 0x278d, # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT FOUR
            0x00ce: 0x278e, # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT FIVE
            0x00cf: 0x278f, # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT SIX
            0x00d0: 0x2790, # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT SEVEN
            0x00d1: 0x2791, # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT EIGHT
            0x00d2: 0x2792, # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT NINE
            0x00d3: 0x2793, # DINGBAT NEGATIVE CIRCLED SANS-SERIF NUMBER TEN
            0x00d4: 0x2794, # HEAVY WIDE-HEADED RIGHTWARDS ARROW
            0x00d5: 0x2192, # RIGHTWARDS ARROW
            0x00d6: 0x2194, # LEFT RIGHT ARROW
            0x00d7: 0x2195, # UP DOWN ARROW
            0x00d8: 0x2798, # HEAVY SOUTH EAST ARROW
            0x00d9: 0x2799, # HEAVY RIGHTWARDS ARROW
            0x00da: 0x279a, # HEAVY NORTH EAST ARROW
            0x00db: 0x279b, # DRAFTING POINT RIGHTWARDS ARROW
            0x00dc: 0x279c, # HEAVY ROUND-TIPPED RIGHTWARDS ARROW
            0x00dd: 0x279d, # TRIANGLE-HEADED RIGHTWARDS ARROW
            0x00de: 0x279e, # HEAVY TRIANGLE-HEADED RIGHTWARDS ARROW
            0x00df: 0x279f, # DASHED TRIANGLE-HEADED RIGHTWARDS ARROW
            0x00e0: 0x27a0, # HEAVY DASHED TRIANGLE-HEADED RIGHTWARDS ARROW
            0x00e1: 0x27a1, # BLACK RIGHTWARDS ARROW
            0x00e2: 0x27a2, # THREE-D TOP-LIGHTED RIGHTWARDS ARROWHEAD
            0x00e3: 0x27a3, # THREE-D BOTTOM-LIGHTED RIGHTWARDS ARROWHEAD
            0x00e4: 0x27a4, # BLACK RIGHTWARDS ARROWHEAD
            0x00e5: 0x27a5, # HEAVY BLACK CURVED DOWNWARDS AND RIGHTWARDS ARROW
            0x00e6: 0x27a6, # HEAVY BLACK CURVED UPWARDS AND RIGHTWARDS ARROW
            0x00e7: 0x27a7, # SQUAT BLACK RIGHTWARDS ARROW
            0x00e8: 0x27a8, # HEAVY CONCAVE-POINTED BLACK RIGHTWARDS ARROW
            0x00e9: 0x27a9, # RIGHT-SHADED WHITE RIGHTWARDS ARROW
            0x00ea: 0x27aa, # LEFT-SHADED WHITE RIGHTWARDS ARROW
            0x00eb: 0x27ab, # BACK-TILTED SHADOWED WHITE RIGHTWARDS ARROW
            0x00ec: 0x27ac, # FRONT-TILTED SHADOWED WHITE RIGHTWARDS ARROW
            0x00ed: 0x27ad, # HEAVY LOWER RIGHT-SHADOWED WHITE RIGHTWARDS ARROW
            0x00ee: 0x27ae, # HEAVY UPPER RIGHT-SHADOWED WHITE RIGHTWARDS ARROW
            0x00ef: 0x27af, # NOTCHED LOWER RIGHT-SHADOWED WHITE RIGHTWARDS ARROW
            0x00f0: None, # UNDEFINED
            0x00f1: 0x27b1, # NOTCHED UPPER RIGHT-SHADOWED WHITE RIGHTWARDS ARROW
            0x00f2: 0x27b2, # CIRCLED HEAVY WHITE RIGHTWARDS ARROW
            0x00f3: 0x27b3, # WHITE-FEATHERED RIGHTWARDS ARROW
            0x00f4: 0x27b4, # BLACK-FEATHERED SOUTH EAST ARROW
            0x00f5: 0x27b5, # BLACK-FEATHERED RIGHTWARDS ARROW
            0x00f6: 0x27b6, # BLACK-FEATHERED NORTH EAST ARROW
            0x00f7: 0x27b7, # HEAVY BLACK-FEATHERED SOUTH EAST ARROW
            0x00f8: 0x27b8, # HEAVY BLACK-FEATHERED RIGHTWARDS ARROW
            0x00f9: 0x27b9, # HEAVY BLACK-FEATHERED NORTH EAST ARROW
            0x00fa: 0x27ba, # TEARDROP-BARBED RIGHTWARDS ARROW
            0x00fb: 0x27bb, # HEAVY TEARDROP-SHANKED RIGHTWARDS ARROW
            0x00fc: 0x27bc, # WEDGE-TAILED RIGHTWARDS ARROW
            0x00fd: 0x27bd, # HEAVY WEDGE-TAILED RIGHTWARDS ARROW
            0x00fe: 0x27be, # OPEN-OUTLINED RIGHTWARDS ARROW
            0x00ff: None, # UNDEFINED
            },None),
    'pdfdoc':StdCodecData({
            #compatibility with pike pdf
            0x0000: 0x0000, #(NULL) U
            0x0001: 0x0001, #(START OF HEADING) U
            0x0002: 0x0002, #(START OF TEXT) U
            0x0003: 0x0003, #(END OF TEXT) U
            0x0004: 0x0004, #(END OF TEXT) U
            0x0005: 0x0005, #(END OF TRANSMISSION) U
            0x0006: 0x0006, #(ACKNOWLEDGE) U
            0x0007: 0x0007, #(BELL) U
            0x0008: 0x0008, #(BACKSPACE) U
            0x000B: 0x000B, #(LINE TABULATION) U
            0x000C: 0x000C, #(FORM FEED) U
            0x000E: 0x000E, #(SHIFT OUT) U
            0x000F: 0x000F, #(SHIFT IN) U
            0x0010: 0x0010, #(DATA LINK ESCAPE) U
            0x0011: 0x0011, #(DEVICE CONTROL ONE) U
            0x0012: 0x0012, #(DEVICE CONTROL TWO) U
            0x0013: 0x0013, #(DEVICE CONTROL THREE) U
            0x0014: 0x0014, #(DEVICE CONTROL FOUR) U
            0x0015: 0x0015, #(NEGATIVE ACKNOWLEDGE) U
            0x0016: 0x0016, #was a typo U+0017 in in PDF SPEC U
            0x0017: 0x0017, #(END OF TRANSMISSION BLOCK) U
            0x007f: 0x007f, # delete pdf spec UNDEFINED
            0x009f: 0x009f, # application program command APC pdf spec UNDEFINED
            0x00ad: 0x00ad, # soft hyphen spec UNDEFINED

            #properly defined by the pdf spec
            0x0009: 0x0009, #(CHARACTER TABULATION) SR
            0x000A: 0x000A, #(LINE FEED) SR
            0x000D: 0x000D, #(CARRIAGE RETURN) SR
            0x0080: 0x2022, # BULLET
            0x0081: 0x2020, # DAGGER
            0x0082: 0x2021, # DOUBLE DAGGER
            0x0083: 0x2026, # HORIZONTAL ELLIPSIS
            0x0084: 0x2014, # EM DASH
            0x0085: 0x2013, # EN DASH
            0x0086: 0x0192, # LATIN SMALL LETTER F WITH HOOK
            0x0087: 0x2044, # FRACTION SLASH
            0x0088: 0x2039, # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
            0x0089: 0x203a, # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
            0x008a: 0x2212, # MINUS SIGN
            0x008b: 0x2030, # PER MILLE SIGN
            0x008c: 0x201e, # DOUBLE LOW-9 QUOTATION MARK
            0x008d: 0x201c, # LEFT DOUBLE QUOTATION MARK
            0x008e: 0x201d, # RIGHT DOUBLE QUOTATION MARK
            0x008f: 0x2018, # LEFT SINGLE QUOTATION MARK
            0x0090: 0x2019, # RIGHT SINGLE QUOTATION MARK
            0x0091: 0x201a, # SINGLE LOW-9 QUOTATION MARK
            0x0092: 0x2122, # TRADE MARK SIGN
            0x0093: 0xfb01, # LATIN SMALL LIGATURE FI
            0x0094: 0xfb02, # LATIN SMALL LIGATURE FL
            0x0095: 0x0141, # LATIN CAPITAL LETTER L WITH STROKE
            0x0096: 0x0152, # LATIN CAPITAL LIGATURE OE
            0x0097: 0x0160, # LATIN CAPITAL LETTER S WITH CARON
            0x0098: 0x0178, # LATIN CAPITAL LETTER Y WITH DIAERESIS
            0x0099: 0x017d, # LATIN CAPITAL LETTER Z WITH CARON
            0x009a: 0x0131, # LATIN SMALL LETTER DOTLESS I
            0x009b: 0x0142, # LATIN SMALL LETTER L WITH STROKE
            0x009c: 0x0153, # LATIN SMALL LIGATURE OE
            0x009d: 0x0161, # LATIN SMALL LETTER S WITH CARON
            0x009e: 0x017e, # LATIN SMALL LETTER Z WITH CARON
            0x00a0: 0x20ac, # EURO SIGN
            24: 0x02d8, #breve
            25: 0x02c7, #caron
            26: 0x02c6, #circumflex
            27: 0x02d9, #dotaccent
            28: 0x02dd, #hungarumlaut
            29: 0x02db, #ogonek
            30: 0x02da, #ring
            31: 0x02dc, #tilde
            },None),
    'macexpert':StdCodecData({
            0x0021: 0xf721, # [unknown unicode name for exclamsmall]
            0x0022: 0xf6f8, # [unknown unicode name for Hungarumlautsmall]
            0x0023: 0xf7a2, # [unknown unicode name for centoldstyle]
            0x0024: 0xf724, # [unknown unicode name for dollaroldstyle]
            0x0025: 0xf6e4, # [unknown unicode name for dollarsuperior]
            0x0026: 0xf726, # [unknown unicode name for ampersandsmall]
            0x0027: 0xf7b4, # [unknown unicode name for Acutesmall]
            0x0028: 0x207d, # SUPERSCRIPT LEFT PARENTHESIS
            0x0029: 0x207e, # SUPERSCRIPT RIGHT PARENTHESIS
            0x002a: 0x2025, # TWO DOT LEADER
            0x002b: 0x2024, # ONE DOT LEADER
            0x002f: 0x2044, # FRACTION SLASH
            0x0030: 0xf730, # [unknown unicode name for zerooldstyle]
            0x0031: 0xf731, # [unknown unicode name for oneoldstyle]
            0x0032: 0xf732, # [unknown unicode name for twooldstyle]
            0x0033: 0xf733, # [unknown unicode name for threeoldstyle]
            0x0034: 0xf734, # [unknown unicode name for fouroldstyle]
            0x0035: 0xf735, # [unknown unicode name for fiveoldstyle]
            0x0036: 0xf736, # [unknown unicode name for sixoldstyle]
            0x0037: 0xf737, # [unknown unicode name for sevenoldstyle]
            0x0038: 0xf738, # [unknown unicode name for eightoldstyle]
            0x0039: 0xf739, # [unknown unicode name for nineoldstyle]
            0x003c: None, # UNDEFINED
            0x003d: 0xf6de, # [unknown unicode name for threequartersemdash]
            0x003e: None, # UNDEFINED
            0x003f: 0xf73f, # [unknown unicode name for questionsmall]
            0x0040: None, # UNDEFINED
            0x0041: None, # UNDEFINED
            0x0042: None, # UNDEFINED
            0x0043: None, # UNDEFINED
            0x0044: 0xf7f0, # [unknown unicode name for Ethsmall]
            0x0045: None, # UNDEFINED
            0x0046: None, # UNDEFINED
            0x0047: 0x00bc, # VULGAR FRACTION ONE QUARTER
            0x0048: 0x00bd, # VULGAR FRACTION ONE HALF
            0x0049: 0x00be, # VULGAR FRACTION THREE QUARTERS
            0x004a: 0x215b, # VULGAR FRACTION ONE EIGHTH
            0x004b: 0x215c, # VULGAR FRACTION THREE EIGHTHS
            0x004c: 0x215d, # VULGAR FRACTION FIVE EIGHTHS
            0x004d: 0x215e, # VULGAR FRACTION SEVEN EIGHTHS
            0x004e: 0x2153, # VULGAR FRACTION ONE THIRD
            0x004f: 0x2154, # VULGAR FRACTION TWO THIRDS
            0x0050: None, # UNDEFINED
            0x0051: None, # UNDEFINED
            0x0052: None, # UNDEFINED
            0x0053: None, # UNDEFINED
            0x0054: None, # UNDEFINED
            0x0055: None, # UNDEFINED
            0x0056: 0xfb00, # LATIN SMALL LIGATURE FF
            0x0057: 0xfb01, # LATIN SMALL LIGATURE FI
            0x0058: 0xfb02, # LATIN SMALL LIGATURE FL
            0x0059: 0xfb03, # LATIN SMALL LIGATURE FFI
            0x005a: 0xfb04, # LATIN SMALL LIGATURE FFL
            0x005b: 0x208d, # SUBSCRIPT LEFT PARENTHESIS
            0x005c: None, # UNDEFINED
            0x005d: 0x208e, # SUBSCRIPT RIGHT PARENTHESIS
            0x005e: 0xf6f6, # [unknown unicode name for Circumflexsmall]
            0x005f: 0xf6e5, # [unknown unicode name for hypheninferior]
            0x0060: 0xf760, # [unknown unicode name for Gravesmall]
            0x0061: 0xf761, # [unknown unicode name for Asmall]
            0x0062: 0xf762, # [unknown unicode name for Bsmall]
            0x0063: 0xf763, # [unknown unicode name for Csmall]
            0x0064: 0xf764, # [unknown unicode name for Dsmall]
            0x0065: 0xf765, # [unknown unicode name for Esmall]
            0x0066: 0xf766, # [unknown unicode name for Fsmall]
            0x0067: 0xf767, # [unknown unicode name for Gsmall]
            0x0068: 0xf768, # [unknown unicode name for Hsmall]
            0x0069: 0xf769, # [unknown unicode name for Ismall]
            0x006a: 0xf76a, # [unknown unicode name for Jsmall]
            0x006b: 0xf76b, # [unknown unicode name for Ksmall]
            0x006c: 0xf76c, # [unknown unicode name for Lsmall]
            0x006d: 0xf76d, # [unknown unicode name for Msmall]
            0x006e: 0xf76e, # [unknown unicode name for Nsmall]
            0x006f: 0xf76f, # [unknown unicode name for Osmall]
            0x0070: 0xf770, # [unknown unicode name for Psmall]
            0x0071: 0xf771, # [unknown unicode name for Qsmall]
            0x0072: 0xf772, # [unknown unicode name for Rsmall]
            0x0073: 0xf773, # [unknown unicode name for Ssmall]
            0x0074: 0xf774, # [unknown unicode name for Tsmall]
            0x0075: 0xf775, # [unknown unicode name for Usmall]
            0x0076: 0xf776, # [unknown unicode name for Vsmall]
            0x0077: 0xf777, # [unknown unicode name for Wsmall]
            0x0078: 0xf778, # [unknown unicode name for Xsmall]
            0x0079: 0xf779, # [unknown unicode name for Ysmall]
            0x007a: 0xf77a, # [unknown unicode name for Zsmall]
            0x007b: 0x20a1, # COLON SIGN
            0x007c: 0xf6dc, # [unknown unicode name for onefitted]
            0x007d: 0xf6dd, # [unknown unicode name for rupiah]
            0x007e: 0xf6fe, # [unknown unicode name for Tildesmall]
            0x007f: None, # UNDEFINED
            0x0080: None, # UNDEFINED
            0x0081: 0xf6e9, # [unknown unicode name for asuperior]
            0x0082: 0xf6e0, # [unknown unicode name for centsuperior]
            0x0083: None, # UNDEFINED
            0x0084: None, # UNDEFINED
            0x0085: None, # UNDEFINED
            0x0086: None, # UNDEFINED
            0x0087: 0xf7e1, # [unknown unicode name for Aacutesmall]
            0x0088: 0xf7e0, # [unknown unicode name for Agravesmall]
            0x0089: 0xf7e2, # [unknown unicode name for Acircumflexsmall]
            0x008a: 0xf7e4, # [unknown unicode name for Adieresissmall]
            0x008b: 0xf7e3, # [unknown unicode name for Atildesmall]
            0x008c: 0xf7e5, # [unknown unicode name for Aringsmall]
            0x008d: 0xf7e7, # [unknown unicode name for Ccedillasmall]
            0x008e: 0xf7e9, # [unknown unicode name for Eacutesmall]
            0x008f: 0xf7e8, # [unknown unicode name for Egravesmall]
            0x0090: 0xf7ea, # [unknown unicode name for Ecircumflexsmall]
            0x0091: 0xf7eb, # [unknown unicode name for Edieresissmall]
            0x0092: 0xf7ed, # [unknown unicode name for Iacutesmall]
            0x0093: 0xf7ec, # [unknown unicode name for Igravesmall]
            0x0094: 0xf7ee, # [unknown unicode name for Icircumflexsmall]
            0x0095: 0xf7ef, # [unknown unicode name for Idieresissmall]
            0x0096: 0xf7f1, # [unknown unicode name for Ntildesmall]
            0x0097: 0xf7f3, # [unknown unicode name for Oacutesmall]
            0x0098: 0xf7f2, # [unknown unicode name for Ogravesmall]
            0x0099: 0xf7f4, # [unknown unicode name for Ocircumflexsmall]
            0x009a: 0xf7f6, # [unknown unicode name for Odieresissmall]
            0x009b: 0xf7f5, # [unknown unicode name for Otildesmall]
            0x009c: 0xf7fa, # [unknown unicode name for Uacutesmall]
            0x009d: 0xf7f9, # [unknown unicode name for Ugravesmall]
            0x009e: 0xf7fb, # [unknown unicode name for Ucircumflexsmall]
            0x009f: 0xf7fc, # [unknown unicode name for Udieresissmall]
            0x00a0: None, # UNDEFINED
            0x00a1: 0x2078, # SUPERSCRIPT EIGHT
            0x00a2: 0x2084, # SUBSCRIPT FOUR
            0x00a3: 0x2083, # SUBSCRIPT THREE
            0x00a4: 0x2086, # SUBSCRIPT SIX
            0x00a5: 0x2088, # SUBSCRIPT EIGHT
            0x00a6: 0x2087, # SUBSCRIPT SEVEN
            0x00a7: 0xf6fd, # [unknown unicode name for Scaronsmall]
            0x00a8: None, # UNDEFINED
            0x00a9: 0xf6df, # [unknown unicode name for centinferior]
            0x00aa: 0x2082, # SUBSCRIPT TWO
            0x00ab: None, # UNDEFINED
            0x00ac: 0xf7a8, # [unknown unicode name for Dieresissmall]
            0x00ad: None, # UNDEFINED
            0x00ae: 0xf6f5, # [unknown unicode name for Caronsmall]
            0x00af: 0xf6f0, # [unknown unicode name for osuperior]
            0x00b0: 0x2085, # SUBSCRIPT FIVE
            0x00b1: None, # UNDEFINED
            0x00b2: 0xf6e1, # [unknown unicode name for commainferior]
            0x00b3: 0xf6e7, # [unknown unicode name for periodinferior]
            0x00b4: 0xf7fd, # [unknown unicode name for Yacutesmall]
            0x00b5: None, # UNDEFINED
            0x00b6: 0xf6e3, # [unknown unicode name for dollarinferior]
            0x00b7: None, # UNDEFINED
            0x00b8: None, # UNDEFINED
            0x00b9: 0xf7fe, # [unknown unicode name for Thornsmall]
            0x00ba: None, # UNDEFINED
            0x00bb: 0x2089, # SUBSCRIPT NINE
            0x00bc: 0x2080, # SUBSCRIPT ZERO
            0x00bd: 0xf6ff, # [unknown unicode name for Zcaronsmall]
            0x00be: 0xf7e6, # [unknown unicode name for AEsmall]
            0x00bf: 0xf7f8, # [unknown unicode name for Oslashsmall]
            0x00c0: 0xf7bf, # [unknown unicode name for questiondownsmall]
            0x00c1: 0x2081, # SUBSCRIPT ONE
            0x00c2: 0xf6f9, # [unknown unicode name for Lslashsmall]
            0x00c3: None, # UNDEFINED
            0x00c4: None, # UNDEFINED
            0x00c5: None, # UNDEFINED
            0x00c6: None, # UNDEFINED
            0x00c7: None, # UNDEFINED
            0x00c8: None, # UNDEFINED
            0x00c9: 0xf7b8, # [unknown unicode name for Cedillasmall]
            0x00ca: None, # UNDEFINED
            0x00cb: None, # UNDEFINED
            0x00cc: None, # UNDEFINED
            0x00cd: None, # UNDEFINED
            0x00ce: None, # UNDEFINED
            0x00cf: 0xf6fa, # [unknown unicode name for OEsmall]
            0x00d0: 0x2012, # FIGURE DASH
            0x00d1: 0xf6e6, # [unknown unicode name for hyphensuperior]
            0x00d2: None, # UNDEFINED
            0x00d3: None, # UNDEFINED
            0x00d4: None, # UNDEFINED
            0x00d5: None, # UNDEFINED
            0x00d6: 0xf7a1, # [unknown unicode name for exclamdownsmall]
            0x00d7: None, # UNDEFINED
            0x00d8: 0xf7ff, # [unknown unicode name for Ydieresissmall]
            0x00d9: None, # UNDEFINED
            0x00da: 0x00b9, # SUPERSCRIPT ONE
            0x00db: 0x00b2, # SUPERSCRIPT TWO
            0x00dc: 0x00b3, # SUPERSCRIPT THREE
            0x00dd: 0x2074, # SUPERSCRIPT FOUR
            0x00de: 0x2075, # SUPERSCRIPT FIVE
            0x00df: 0x2076, # SUPERSCRIPT SIX
            0x00e0: 0x2077, # SUPERSCRIPT SEVEN
            0x00e1: 0x2079, # SUPERSCRIPT NINE
            0x00e2: 0x2070, # SUPERSCRIPT ZERO
            0x00e3: None, # UNDEFINED
            0x00e4: 0xf6ec, # [unknown unicode name for esuperior]
            0x00e5: 0xf6f1, # [unknown unicode name for rsuperior]
            0x00e6: 0xf6f3, # [unknown unicode name for tsuperior]
            0x00e7: None, # UNDEFINED
            0x00e8: None, # UNDEFINED
            0x00e9: 0xf6ed, # [unknown unicode name for isuperior]
            0x00ea: 0xf6f2, # [unknown unicode name for ssuperior]
            0x00eb: 0xf6eb, # [unknown unicode name for dsuperior]
            0x00ec: None, # UNDEFINED
            0x00ed: None, # UNDEFINED
            0x00ee: None, # UNDEFINED
            0x00ef: None, # UNDEFINED
            0x00f0: None, # UNDEFINED
            0x00f1: 0xf6ee, # [unknown unicode name for lsuperior]
            0x00f2: 0xf6fb, # [unknown unicode name for Ogoneksmall]
            0x00f3: 0xf6f4, # [unknown unicode name for Brevesmall]
            0x00f4: 0xf7af, # [unknown unicode name for Macronsmall]
            0x00f5: 0xf6ea, # [unknown unicode name for bsuperior]
            0x00f6: 0x207f, # SUPERSCRIPT LATIN SMALL LETTER N
            0x00f7: 0xf6ef, # [unknown unicode name for msuperior]
            0x00f8: 0xf6e2, # [unknown unicode name for commasuperior]
            0x00f9: 0xf6e8, # [unknown unicode name for periodsuperior]
            0x00fa: 0xf6f7, # [unknown unicode name for Dotaccentsmall]
            0x00fb: 0xf6fc, # [unknown unicode name for Ringsmall]
            0x00fc: None, # UNDEFINED
            0x00fd: None, # UNDEFINED
            0x00fe: None, # UNDEFINED
            0x00ff: None, # UNDEFINED
            },None),
        }
    __rl_extension_codecs = {
            'extpdfdoc':ExtCodecData('pdfdoc',None,None),
            }
    #for k,v in __rl_codecs_data.items():
    #   __rl_codecs_data[k+'enc'] = __rl_codecs_data[k+'encoding'] = v
    #del k,v

    __rl_dynamic_codecs = []

    def __init__(self):
        raise NotImplementedError

    @staticmethod
    def _makeCodecInfo(name,encoding_map,decoding_map):
        ### Codec APIs
        class Codec(codecs.Codec):
            def encode(self,input,errors='strict',charmap_encode=codecs.charmap_encode,encoding_map=encoding_map):
                return charmap_encode(input,errors,encoding_map)

            def decode(self,input,errors='strict',charmap_decode=codecs.charmap_decode,decoding_map=decoding_map):
                return charmap_decode(input,errors,decoding_map)

        class StreamWriter(Codec,codecs.StreamWriter):
            pass

        class StreamReader(Codec,codecs.StreamReader):
            pass
        C = Codec()
        return codecs.CodecInfo(C.encode,C.decode,streamreader=StreamReader,streamwriter=StreamWriter,name=name)

    @staticmethod
    def _256_exception_codec(name,exceptions,rexceptions,baseRange=range(32,256)):
        decoding_map = codecs.make_identity_dict(baseRange)
        decoding_map.update(exceptions)
        encoding_map = codecs.make_encoding_map(decoding_map)
        if rexceptions: encoding_map.update(rexceptions)
        return RL_Codecs._makeCodecInfo(name,encoding_map,decoding_map)

    __rl_codecs_cache = {}

    @staticmethod
    def __rl_codecs(name,cache=__rl_codecs_cache,data=__rl_codecs_data,extension_codecs=__rl_extension_codecs,_256=True):
        try:
            return cache[name]
        except KeyError:
            if name in extension_codecs:
                x = extension_codecs[name]
                e,r = data[x.baseName]
                if x.exceptions:
                    if e:
                        e = e.copy()
                        e.update(x.exceptions)
                    else:
                        e = x.exceptions
                if x.rexceptions:
                    if r:
                        r = r.copy()
                        r.update(x.rexceptions)
                    else:
                        r = x.exceptions
            else:
                e,r = data[name]
            cache[name] = c = RL_Codecs._256_exception_codec(name,e,r) if _256 else RL_Codecs._makeCodecInfo(name, e,r or {})
        return c

    @staticmethod
    def _rl_codecs(name):
        name = name.lower()
        from reportlab.pdfbase.pdfmetrics import standardEncodings
        for e in standardEncodings+('ExtPdfdocEncoding',):
            e = e[:-8].lower()
            if name.startswith(e): return RL_Codecs.__rl_codecs(e)
        if name in RL_Codecs.__rl_dynamic_codecs:
            return RL_Codecs.__rl_codecs(name,_256=False)
        return None

    @staticmethod
    def register():
        codecs.register(RL_Codecs._rl_codecs)

    @staticmethod
    def add_dynamic_codec(name,exceptions,rexceptions):
        name = name.lower()
        RL_Codecs.remove_dynamic_codec(name)
        RL_Codecs.__rl_codecs_data[name] = (exceptions,rexceptions)
        RL_Codecs.__rl_dynamic_codecs.append(name)

    @staticmethod
    def remove_dynamic_codec(name):
        name = name.lower()
        if name in RL_Codecs.__rl_dynamic_codecs:
            RL_Codecs.__rl_codecs_data.pop(name,None)
            RL_Codecs.__rl_codecs_cache.pop(name,None)
            RL_Codecs.__rl_dynamic_codecs.remove(name)

    @staticmethod
    def reset_dynamic_codecs():
        map(RL_Codecs.remove_dynamic_codec, RL_Codecs.__rl_dynamic_codecs)
