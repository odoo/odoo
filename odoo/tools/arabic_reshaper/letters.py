# The following code was copied from the original author's repository
# at https://github.com/mpcabd/python-arabic-reshaper/tree/v3.0.0/arabic_reshaper
# Version: 3.0.0

# This work is licensed under the MIT License.
# To view a copy of this license, visit https://opensource.org/licenses/MIT

# Written by Abdullah Diab (mpcabd)
# Email: mpcabd@gmail.com
# Website: http://mpcabd.xyz

# Each letter is of the format:
#
#   ('<letter>', <replacement>)
#
# And replacement is of the format:
#
#   ('<isolated>', '<initial>', '<medial>', '<final>')
#
# Where <letter> is the string to replace, and <isolated> is the replacement in
# case <letter> should be in isolated form, <initial> is the replacement in
# case <letter> should be in initial form, <medial> is the replacement in case
# <letter> should be in medial form, and <final> is the replacement in case
# <letter> should be in final form. If no replacement is specified for a form,
# then no that means the letter doesn't support this form.

UNSHAPED = 255
ISOLATED = 0
INITIAL = 1
MEDIAL = 2
FINAL = 3

TATWEEL = '\u0640'
ZWJ = '\u200D'
LETTERS_ARABIC = {
    # ARABIC LETTER HAMZA
    '\u0621': ('\uFE80', '', '', ''),
    # ARABIC LETTER ALEF WITH MADDA ABOVE
    '\u0622': ('\uFE81', '', '', '\uFE82'),
    # ARABIC LETTER ALEF WITH HAMZA ABOVE
    '\u0623': ('\uFE83', '', '', '\uFE84'),
    # ARABIC LETTER WAW WITH HAMZA ABOVE
    '\u0624': ('\uFE85', '', '', '\uFE86'),
    # ARABIC LETTER ALEF WITH HAMZA BELOW
    '\u0625': ('\uFE87', '', '', '\uFE88'),
    # ARABIC LETTER YEH WITH HAMZA ABOVE
    '\u0626': ('\uFE89', '\uFE8B', '\uFE8C', '\uFE8A'),
    # ARABIC LETTER ALEF
    '\u0627': ('\uFE8D', '', '', '\uFE8E'),
    # ARABIC LETTER BEH
    '\u0628': ('\uFE8F', '\uFE91', '\uFE92', '\uFE90'),
    # ARABIC LETTER TEH MARBUTA
    '\u0629': ('\uFE93', '', '', '\uFE94'),
    # ARABIC LETTER TEH
    '\u062A': ('\uFE95', '\uFE97', '\uFE98', '\uFE96'),
    # ARABIC LETTER THEH
    '\u062B': ('\uFE99', '\uFE9B', '\uFE9C', '\uFE9A'),
    # ARABIC LETTER JEEM
    '\u062C': ('\uFE9D', '\uFE9F', '\uFEA0', '\uFE9E'),
    # ARABIC LETTER HAH
    '\u062D': ('\uFEA1', '\uFEA3', '\uFEA4', '\uFEA2'),
    # ARABIC LETTER KHAH
    '\u062E': ('\uFEA5', '\uFEA7', '\uFEA8', '\uFEA6'),
    # ARABIC LETTER DAL
    '\u062F': ('\uFEA9', '', '', '\uFEAA'),
    # ARABIC LETTER THAL
    '\u0630': ('\uFEAB', '', '', '\uFEAC'),
    # ARABIC LETTER REH
    '\u0631': ('\uFEAD', '', '', '\uFEAE'),
    # ARABIC LETTER ZAIN
    '\u0632': ('\uFEAF', '', '', '\uFEB0'),
    # ARABIC LETTER SEEN
    '\u0633': ('\uFEB1', '\uFEB3', '\uFEB4', '\uFEB2'),
    # ARABIC LETTER SHEEN
    '\u0634': ('\uFEB5', '\uFEB7', '\uFEB8', '\uFEB6'),
    # ARABIC LETTER SAD
    '\u0635': ('\uFEB9', '\uFEBB', '\uFEBC', '\uFEBA'),
    # ARABIC LETTER DAD
    '\u0636': ('\uFEBD', '\uFEBF', '\uFEC0', '\uFEBE'),
    # ARABIC LETTER TAH
    '\u0637': ('\uFEC1', '\uFEC3', '\uFEC4', '\uFEC2'),
    # ARABIC LETTER ZAH
    '\u0638': ('\uFEC5', '\uFEC7', '\uFEC8', '\uFEC6'),
    # ARABIC LETTER AIN
    '\u0639': ('\uFEC9', '\uFECB', '\uFECC', '\uFECA'),
    # ARABIC LETTER GHAIN
    '\u063A': ('\uFECD', '\uFECF', '\uFED0', '\uFECE'),
    # ARABIC TATWEEL
    TATWEEL:  (TATWEEL, TATWEEL, TATWEEL, TATWEEL),
    # ARABIC LETTER FEH
    '\u0641': ('\uFED1', '\uFED3', '\uFED4', '\uFED2'),
    # ARABIC LETTER QAF
    '\u0642': ('\uFED5', '\uFED7', '\uFED8', '\uFED6'),
    # ARABIC LETTER KAF
    '\u0643': ('\uFED9', '\uFEDB', '\uFEDC', '\uFEDA'),
    # ARABIC LETTER LAM
    '\u0644': ('\uFEDD', '\uFEDF', '\uFEE0', '\uFEDE'),
    # ARABIC LETTER MEEM
    '\u0645': ('\uFEE1', '\uFEE3', '\uFEE4', '\uFEE2'),
    # ARABIC LETTER NOON
    '\u0646': ('\uFEE5', '\uFEE7', '\uFEE8', '\uFEE6'),
    # ARABIC LETTER HEH
    '\u0647': ('\uFEE9', '\uFEEB', '\uFEEC', '\uFEEA'),
    # ARABIC LETTER WAW
    '\u0648': ('\uFEED', '', '', '\uFEEE'),
    # ARABIC LETTER (UIGHUR KAZAKH KIRGHIZ)? ALEF MAKSURA
    '\u0649': ('\uFEEF', '\uFBE8', '\uFBE9', '\uFEF0'),
    # ARABIC LETTER YEH
    '\u064A': ('\uFEF1', '\uFEF3', '\uFEF4', '\uFEF2'),
    # ARABIC LETTER ALEF WASLA
    '\u0671': ('\uFB50', '', '', '\uFB51'),
    # ARABIC LETTER U WITH HAMZA ABOVE
    '\u0677': ('\uFBDD', '', '', ''),
    # ARABIC LETTER TTEH
    '\u0679': ('\uFB66', '\uFB68', '\uFB69', '\uFB67'),
    # ARABIC LETTER TTEHEH
    '\u067A': ('\uFB5E', '\uFB60', '\uFB61', '\uFB5F'),
    # ARABIC LETTER BEEH
    '\u067B': ('\uFB52', '\uFB54', '\uFB55', '\uFB53'),
    # ARABIC LETTER PEH
    '\u067E': ('\uFB56', '\uFB58', '\uFB59', '\uFB57'),
    # ARABIC LETTER TEHEH
    '\u067F': ('\uFB62', '\uFB64', '\uFB65', '\uFB63'),
    # ARABIC LETTER BEHEH
    '\u0680': ('\uFB5A', '\uFB5C', '\uFB5D', '\uFB5B'),
    # ARABIC LETTER NYEH
    '\u0683': ('\uFB76', '\uFB78', '\uFB79', '\uFB77'),
    # ARABIC LETTER DYEH
    '\u0684': ('\uFB72', '\uFB74', '\uFB75', '\uFB73'),
    # ARABIC LETTER TCHEH
    '\u0686': ('\uFB7A', '\uFB7C', '\uFB7D', '\uFB7B'),
    # ARABIC LETTER TCHEHEH
    '\u0687': ('\uFB7E', '\uFB80', '\uFB81', '\uFB7F'),
    # ARABIC LETTER DDAL
    '\u0688': ('\uFB88', '', '', '\uFB89'),
    # ARABIC LETTER DAHAL
    '\u068C': ('\uFB84', '', '', '\uFB85'),
    # ARABIC LETTER DDAHAL
    '\u068D': ('\uFB82', '', '', '\uFB83'),
    # ARABIC LETTER DUL
    '\u068E': ('\uFB86', '', '', '\uFB87'),
    # ARABIC LETTER RREH
    '\u0691': ('\uFB8C', '', '', '\uFB8D'),
    # ARABIC LETTER JEH
    '\u0698': ('\uFB8A', '', '', '\uFB8B'),
    # ARABIC LETTER VEH
    '\u06A4': ('\uFB6A', '\uFB6C', '\uFB6D', '\uFB6B'),
    # ARABIC LETTER PEHEH
    '\u06A6': ('\uFB6E', '\uFB70', '\uFB71', '\uFB6F'),
    # ARABIC LETTER KEHEH
    '\u06A9': ('\uFB8E', '\uFB90', '\uFB91', '\uFB8F'),
    # ARABIC LETTER NG
    '\u06AD': ('\uFBD3', '\uFBD5', '\uFBD6', '\uFBD4'),
    # ARABIC LETTER GAF
    '\u06AF': ('\uFB92', '\uFB94', '\uFB95', '\uFB93'),
    # ARABIC LETTER NGOEH
    '\u06B1': ('\uFB9A', '\uFB9C', '\uFB9D', '\uFB9B'),
    # ARABIC LETTER GUEH
    '\u06B3': ('\uFB96', '\uFB98', '\uFB99', '\uFB97'),
    # ARABIC LETTER NOON GHUNNA
    '\u06BA': ('\uFB9E', '', '', '\uFB9F'),
    # ARABIC LETTER RNOON
    '\u06BB': ('\uFBA0', '\uFBA2', '\uFBA3', '\uFBA1'),
    # ARABIC LETTER HEH DOACHASHMEE
    '\u06BE': ('\uFBAA', '\uFBAC', '\uFBAD', '\uFBAB'),
    # ARABIC LETTER HEH WITH YEH ABOVE
    '\u06C0': ('\uFBA4', '', '', '\uFBA5'),
    # ARABIC LETTER HEH GOAL
    '\u06C1': ('\uFBA6', '\uFBA8', '\uFBA9', '\uFBA7'),
    # ARABIC LETTER KIRGHIZ OE
    '\u06C5': ('\uFBE0', '', '', '\uFBE1'),
    # ARABIC LETTER OE
    '\u06C6': ('\uFBD9', '', '', '\uFBDA'),
    # ARABIC LETTER U
    '\u06C7': ('\uFBD7', '', '', '\uFBD8'),
    # ARABIC LETTER YU
    '\u06C8': ('\uFBDB', '', '', '\uFBDC'),
    # ARABIC LETTER KIRGHIZ YU
    '\u06C9': ('\uFBE2', '', '', '\uFBE3'),
    # ARABIC LETTER VE
    '\u06CB': ('\uFBDE', '', '', '\uFBDF'),
    # ARABIC LETTER FARSI YEH
    '\u06CC': ('\uFBFC', '\uFBFE', '\uFBFF', '\uFBFD'),
    # ARABIC LETTER E
    '\u06D0': ('\uFBE4', '\uFBE6', '\uFBE7', '\uFBE5'),
    # ARABIC LETTER YEH BARREE
    '\u06D2': ('\uFBAE', '', '', '\uFBAF'),
    # ARABIC LETTER YEH BARREE WITH HAMZA ABOVE
    '\u06D3': ('\uFBB0', '', '', '\uFBB1'),

    # ZWJ
    ZWJ: (ZWJ, ZWJ, ZWJ, ZWJ),
}

LETTERS_ARABIC_V2 = {
    # ARABIC LETTER HAMZA
    '\u0621': ('\uFE80', '', '', ''),
    # ARABIC LETTER ALEF WITH MADDA ABOVE
    '\u0622': ('\u0622', '', '', '\uFE82'),
    # ARABIC LETTER ALEF WITH HAMZA ABOVE
    '\u0623': ('\u0623', '', '', '\uFE84'),
    # ARABIC LETTER WAW WITH HAMZA ABOVE
    '\u0624': ('\u0624', '', '', '\uFE86'),
    # ARABIC LETTER ALEF WITH HAMZA BELOW
    '\u0625': ('\u0625', '', '', '\uFE88'),
    # ARABIC LETTER YEH WITH HAMZA ABOVE
    '\u0626': ('\u0626', '\uFE8B', '\uFE8C', '\uFE8A'),
    # ARABIC LETTER ALEF
    '\u0627': ('\u0627', '', '', '\uFE8E'),
    # ARABIC LETTER BEH
    '\u0628': ('\u0628', '\uFE91', '\uFE92', '\uFE90'),
    # ARABIC LETTER TEH MARBUTA
    '\u0629': ('\u0629', '', '', '\uFE94'),
    # ARABIC LETTER TEH
    '\u062A': ('\u062A', '\uFE97', '\uFE98', '\uFE96'),
    # ARABIC LETTER THEH
    '\u062B': ('\u062B', '\uFE9B', '\uFE9C', '\uFE9A'),
    # ARABIC LETTER JEEM
    '\u062C': ('\u062C', '\uFE9F', '\uFEA0', '\uFE9E'),
    # ARABIC LETTER HAH
    '\u062D': ('\uFEA1', '\uFEA3', '\uFEA4', '\uFEA2'),
    # ARABIC LETTER KHAH
    '\u062E': ('\u062E', '\uFEA7', '\uFEA8', '\uFEA6'),
    # ARABIC LETTER DAL
    '\u062F': ('\u062F', '', '', '\uFEAA'),
    # ARABIC LETTER THAL
    '\u0630': ('\u0630', '', '', '\uFEAC'),
    # ARABIC LETTER REH
    '\u0631': ('\u0631', '', '', '\uFEAE'),
    # ARABIC LETTER ZAIN
    '\u0632': ('\u0632', '', '', '\uFEB0'),
    # ARABIC LETTER SEEN
    '\u0633': ('\u0633', '\uFEB3', '\uFEB4', '\uFEB2'),
    # ARABIC LETTER SHEEN
    '\u0634': ('\u0634', '\uFEB7', '\uFEB8', '\uFEB6'),
    # ARABIC LETTER SAD
    '\u0635': ('\u0635', '\uFEBB', '\uFEBC', '\uFEBA'),
    # ARABIC LETTER DAD
    '\u0636': ('\u0636', '\uFEBF', '\uFEC0', '\uFEBE'),
    # ARABIC LETTER TAH
    '\u0637': ('\u0637', '\uFEC3', '\uFEC4', '\uFEC2'),
    # ARABIC LETTER ZAH
    '\u0638': ('\u0638', '\uFEC7', '\uFEC8', '\uFEC6'),
    # ARABIC LETTER AIN
    '\u0639': ('\u0639', '\uFECB', '\uFECC', '\uFECA'),
    # ARABIC LETTER GHAIN
    '\u063A': ('\u063A', '\uFECF', '\uFED0', '\uFECE'),
    # ARABIC TATWEEL
    TATWEEL:  (TATWEEL, TATWEEL, TATWEEL, TATWEEL),
    # ARABIC LETTER FEH
    '\u0641': ('\u0641', '\uFED3', '\uFED4', '\uFED2'),
    # ARABIC LETTER QAF
    '\u0642': ('\u0642', '\uFED7', '\uFED8', '\uFED6'),
    # ARABIC LETTER KAF
    '\u0643': ('\u0643', '\uFEDB', '\uFEDC', '\uFEDA'),
    # ARABIC LETTER LAM
    '\u0644': ('\u0644', '\uFEDF', '\uFEE0', '\uFEDE'),
    # ARABIC LETTER MEEM
    '\u0645': ('\u0645', '\uFEE3', '\uFEE4', '\uFEE2'),
    # ARABIC LETTER NOON
    '\u0646': ('\u0646', '\uFEE7', '\uFEE8', '\uFEE6'),
    # ARABIC LETTER HEH
    '\u0647': ('\u0647', '\uFEEB', '\uFEEC', '\uFEEA'),
    # ARABIC LETTER WAW
    '\u0648': ('\u0648', '', '', '\uFEEE'),
    # ARABIC LETTER (UIGHUR KAZAKH KIRGHIZ)? ALEF MAKSURA
    '\u0649': ('\u0649', '\uFBE8', '\uFBE9', '\uFEF0'),
    # ARABIC LETTER YEH
    '\u064A': ('\u064A', '\uFEF3', '\uFEF4', '\uFEF2'),
    # ARABIC LETTER ALEF WASLA
    '\u0671': ('\u0671', '', '', '\uFB51'),
    # ARABIC LETTER U WITH HAMZA ABOVE
    '\u0677': ('\u0677', '', '', ''),
    # ARABIC LETTER TTEH
    '\u0679': ('\u0679', '\uFB68', '\uFB69', '\uFB67'),
    # ARABIC LETTER TTEHEH
    '\u067A': ('\u067A', '\uFB60', '\uFB61', '\uFB5F'),
    # ARABIC LETTER BEEH
    '\u067B': ('\u067B', '\uFB54', '\uFB55', '\uFB53'),
    # ARABIC LETTER PEH
    '\u067E': ('\u067E', '\uFB58', '\uFB59', '\uFB57'),
    # ARABIC LETTER TEHEH
    '\u067F': ('\u067F', '\uFB64', '\uFB65', '\uFB63'),
    # ARABIC LETTER BEHEH
    '\u0680': ('\u0680', '\uFB5C', '\uFB5D', '\uFB5B'),
    # ARABIC LETTER NYEH
    '\u0683': ('\u0683', '\uFB78', '\uFB79', '\uFB77'),
    # ARABIC LETTER DYEH
    '\u0684': ('\u0684', '\uFB74', '\uFB75', '\uFB73'),
    # ARABIC LETTER TCHEH
    '\u0686': ('\u0686', '\uFB7C', '\uFB7D', '\uFB7B'),
    # ARABIC LETTER TCHEHEH
    '\u0687': ('\u0687', '\uFB80', '\uFB81', '\uFB7F'),
    # ARABIC LETTER DDAL
    '\u0688': ('\u0688', '', '', '\uFB89'),
    # ARABIC LETTER DAHAL
    '\u068C': ('\u068C', '', '', '\uFB85'),
    # ARABIC LETTER DDAHAL
    '\u068D': ('\u068D', '', '', '\uFB83'),
    # ARABIC LETTER DUL
    '\u068E': ('\u068E', '', '', '\uFB87'),
    # ARABIC LETTER RREH
    '\u0691': ('\u0691', '', '', '\uFB8D'),
    # ARABIC LETTER JEH
    '\u0698': ('\u0698', '', '', '\uFB8B'),
    # ARABIC LETTER VEH
    '\u06A4': ('\u06A4', '\uFB6C', '\uFB6D', '\uFB6B'),
    # ARABIC LETTER PEHEH
    '\u06A6': ('\u06A6', '\uFB70', '\uFB71', '\uFB6F'),
    # ARABIC LETTER KEHEH
    '\u06A9': ('\u06A9', '\uFB90', '\uFB91', '\uFB8F'),
    # ARABIC LETTER NG
    '\u06AD': ('\u06AD', '\uFBD5', '\uFBD6', '\uFBD4'),
    # ARABIC LETTER GAF
    '\u06AF': ('\u06AF', '\uFB94', '\uFB95', '\uFB93'),
    # ARABIC LETTER NGOEH
    '\u06B1': ('\u06B1', '\uFB9C', '\uFB9D', '\uFB9B'),
    # ARABIC LETTER GUEH
    '\u06B3': ('\u06B3', '\uFB98', '\uFB99', '\uFB97'),
    # ARABIC LETTER NOON GHUNNA
    '\u06BA': ('\u06BA', '', '', '\uFB9F'),
    # ARABIC LETTER RNOON
    '\u06BB': ('\u06BB', '\uFBA2', '\uFBA3', '\uFBA1'),
    # ARABIC LETTER HEH DOACHASHMEE
    '\u06BE': ('\u06BE', '\uFBAC', '\uFBAD', '\uFBAB'),
    # ARABIC LETTER HEH WITH YEH ABOVE
    '\u06C0': ('\u06C0', '', '', '\uFBA5'),
    # ARABIC LETTER HEH GOAL
    '\u06C1': ('\u06C1', '\uFBA8', '\uFBA9', '\uFBA7'),
    # ARABIC LETTER KIRGHIZ OE
    '\u06C5': ('\u06C5', '', '', '\uFBE1'),
    # ARABIC LETTER OE
    '\u06C6': ('\u06C6', '', '', '\uFBDA'),
    # ARABIC LETTER U
    '\u06C7': ('\u06C7', '', '', '\uFBD8'),
    # ARABIC LETTER YU
    '\u06C8': ('\u06C8', '', '', '\uFBDC'),
    # ARABIC LETTER KIRGHIZ YU
    '\u06C9': ('\u06C9', '', '', '\uFBE3'),
    # ARABIC LETTER VE
    '\u06CB': ('\u06CB', '', '', '\uFBDF'),
    # ARABIC LETTER FARSI YEH
    '\u06CC': ('\u06CC', '\uFBFE', '\uFBFF', '\uFBFD'),
    # ARABIC LETTER E
    '\u06D0': ('\u06D0', '\uFBE6', '\uFBE7', '\uFBE5'),
    # ARABIC LETTER YEH BARREE
    '\u06D2': ('\u06D2', '', '', '\uFBAF'),
    # ARABIC LETTER YEH BARREE WITH HAMZA ABOVE
    '\u06D3': ('\u06D3', '', '', '\uFBB1'),
    # Kurdish letter YEAH
    '\u06ce': ('\uE004', '\uE005', '\uE006', '\uE004'),
    # Kurdish letter Hamza same as arabic Teh without the point
    '\u06d5': ('\u06d5', '', '', '\uE000'),
    # ZWJ
    ZWJ: (ZWJ, ZWJ, ZWJ, ZWJ),
}
LETTERS_KURDISH = {
    # ARABIC LETTER HAMZA
    '\u0621': ('\uFE80', '', '', ''),
    # ARABIC LETTER ALEF WITH MADDA ABOVE
    '\u0622': ('\u0622', '', '', '\uFE82'),
    # ARABIC LETTER ALEF WITH HAMZA ABOVE
    '\u0623': ('\u0623', '', '', '\uFE84'),
    # ARABIC LETTER WAW WITH HAMZA ABOVE
    '\u0624': ('\u0624', '', '', '\uFE86'),
    # ARABIC LETTER ALEF WITH HAMZA BELOW
    '\u0625': ('\u0625', '', '', '\uFE88'),
    # ARABIC LETTER YEH WITH HAMZA ABOVE
    '\u0626': ('\u0626', '\uFE8B', '\uFE8C', '\uFE8A'),
    # ARABIC LETTER ALEF
    '\u0627': ('\u0627', '', '', '\uFE8E'),
    # ARABIC LETTER BEH
    '\u0628': ('\u0628', '\uFE91', '\uFE92', '\uFE90'),
    # ARABIC LETTER TEH MARBUTA
    '\u0629': ('\u0629', '', '', '\uFE94'),
    # ARABIC LETTER TEH
    '\u062A': ('\u062A', '\uFE97', '\uFE98', '\uFE96'),
    # ARABIC LETTER THEH
    '\u062B': ('\u062B', '\uFE9B', '\uFE9C', '\uFE9A'),
    # ARABIC LETTER JEEM
    '\u062C': ('\u062C', '\uFE9F', '\uFEA0', '\uFE9E'),
    # ARABIC LETTER HAH
    '\u062D': ('\uFEA1', '\uFEA3', '\uFEA4', '\uFEA2'),
    # ARABIC LETTER KHAH
    '\u062E': ('\u062E', '\uFEA7', '\uFEA8', '\uFEA6'),
    # ARABIC LETTER DAL
    '\u062F': ('\u062F', '', '', '\uFEAA'),
    # ARABIC LETTER THAL
    '\u0630': ('\u0630', '', '', '\uFEAC'),
    # ARABIC LETTER REH
    '\u0631': ('\u0631', '', '', '\uFEAE'),
    # ARABIC LETTER ZAIN
    '\u0632': ('\u0632', '', '', '\uFEB0'),
    # ARABIC LETTER SEEN
    '\u0633': ('\u0633', '\uFEB3', '\uFEB4', '\uFEB2'),
    # ARABIC LETTER SHEEN
    '\u0634': ('\u0634', '\uFEB7', '\uFEB8', '\uFEB6'),
    # ARABIC LETTER SAD
    '\u0635': ('\u0635', '\uFEBB', '\uFEBC', '\uFEBA'),
    # ARABIC LETTER DAD
    '\u0636': ('\u0636', '\uFEBF', '\uFEC0', '\uFEBE'),
    # ARABIC LETTER TAH
    '\u0637': ('\u0637', '\uFEC3', '\uFEC4', '\uFEC2'),
    # ARABIC LETTER ZAH
    '\u0638': ('\u0638', '\uFEC7', '\uFEC8', '\uFEC6'),
    # ARABIC LETTER AIN
    '\u0639': ('\u0639', '\uFECB', '\uFECC', '\uFECA'),
    # ARABIC LETTER GHAIN
    '\u063A': ('\u063A', '\uFECF', '\uFED0', '\uFECE'),
    # ARABIC TATWEEL
    TATWEEL:  (TATWEEL, TATWEEL, TATWEEL, TATWEEL),
    # ARABIC LETTER FEH
    '\u0641': ('\u0641', '\uFED3', '\uFED4', '\uFED2'),
    # ARABIC LETTER QAF
    '\u0642': ('\u0642', '\uFED7', '\uFED8', '\uFED6'),
    # ARABIC LETTER KAF
    '\u0643': ('\u0643', '\uFEDB', '\uFEDC', '\uFEDA'),
    # ARABIC LETTER LAM
    '\u0644': ('\u0644', '\uFEDF', '\uFEE0', '\uFEDE'),
    # ARABIC LETTER MEEM
    '\u0645': ('\u0645', '\uFEE3', '\uFEE4', '\uFEE2'),
    # ARABIC LETTER NOON
    '\u0646': ('\u0646', '\uFEE7', '\uFEE8', '\uFEE6'),
    # ARABIC LETTER HEH
    '\u0647': ('\uFBAB', '\uFBAB', '\uFBAB', '\uFBAB'),
    # ARABIC LETTER WAW
    '\u0648': ('\u0648', '', '', '\uFEEE'),
    # ARABIC LETTER (UIGHUR KAZAKH KIRGHIZ)? ALEF MAKSURA
    '\u0649': ('\u0649', '\uFBE8', '\uFBE9', '\uFEF0'),
    # ARABIC LETTER YEH
    '\u064A': ('\u064A', '\uFEF3', '\uFEF4', '\uFEF2'),
    # ARABIC LETTER ALEF WASLA
    '\u0671': ('\u0671', '', '', '\uFB51'),
    # ARABIC LETTER U WITH HAMZA ABOVE
    '\u0677': ('\u0677', '', '', ''),
    # ARABIC LETTER TTEH
    '\u0679': ('\u0679', '\uFB68', '\uFB69', '\uFB67'),
    # ARABIC LETTER TTEHEH
    '\u067A': ('\u067A', '\uFB60', '\uFB61', '\uFB5F'),
    # ARABIC LETTER BEEH
    '\u067B': ('\u067B', '\uFB54', '\uFB55', '\uFB53'),
    # ARABIC LETTER PEH
    '\u067E': ('\u067E', '\uFB58', '\uFB59', '\uFB57'),
    # ARABIC LETTER TEHEH
    '\u067F': ('\u067F', '\uFB64', '\uFB65', '\uFB63'),
    # ARABIC LETTER BEHEH
    '\u0680': ('\u0680', '\uFB5C', '\uFB5D', '\uFB5B'),
    # ARABIC LETTER NYEH
    '\u0683': ('\u0683', '\uFB78', '\uFB79', '\uFB77'),
    # ARABIC LETTER DYEH
    '\u0684': ('\u0684', '\uFB74', '\uFB75', '\uFB73'),
    # ARABIC LETTER TCHEH
    '\u0686': ('\u0686', '\uFB7C', '\uFB7D', '\uFB7B'),
    # ARABIC LETTER TCHEHEH
    '\u0687': ('\u0687', '\uFB80', '\uFB81', '\uFB7F'),
    # ARABIC LETTER DDAL
    '\u0688': ('\u0688', '', '', '\uFB89'),
    # ARABIC LETTER DAHAL
    '\u068C': ('\u068C', '', '', '\uFB85'),
    # ARABIC LETTER DDAHAL
    '\u068D': ('\u068D', '', '', '\uFB83'),
    # ARABIC LETTER DUL
    '\u068E': ('\u068E', '', '', '\uFB87'),
    # ARABIC LETTER RREH
    '\u0691': ('\u0691', '', '', '\uFB8D'),
    # ARABIC LETTER JEH
    '\u0698': ('\u0698', '', '', '\uFB8B'),
    # ARABIC LETTER VEH
    '\u06A4': ('\u06A4', '\uFB6C', '\uFB6D', '\uFB6B'),
    # ARABIC LETTER PEHEH
    '\u06A6': ('\u06A6', '\uFB70', '\uFB71', '\uFB6F'),
    # ARABIC LETTER KEHEH
    '\u06A9': ('\u06A9', '\uFB90', '\uFB91', '\uFB8F'),
    # ARABIC LETTER NG
    '\u06AD': ('\u06AD', '\uFBD5', '\uFBD6', '\uFBD4'),
    # ARABIC LETTER GAF
    '\u06AF': ('\u06AF', '\uFB94', '\uFB95', '\uFB93'),
    # ARABIC LETTER NGOEH
    '\u06B1': ('\u06B1', '\uFB9C', '\uFB9D', '\uFB9B'),
    # ARABIC LETTER GUEH
    '\u06B3': ('\u06B3', '\uFB98', '\uFB99', '\uFB97'),
    # ARABIC LETTER NOON GHUNNA
    '\u06BA': ('\u06BA', '', '', '\uFB9F'),
    # ARABIC LETTER RNOON
    '\u06BB': ('\u06BB', '\uFBA2', '\uFBA3', '\uFBA1'),
    # ARABIC LETTER HEH DOACHASHMEE
    '\u06BE': ('\u06BE', '\uFBAC', '\uFBAD', '\uFBAB'),
    # ARABIC LETTER HEH WITH YEH ABOVE
    '\u06C0': ('\u06C0', '', '', '\uFBA5'),
    # ARABIC LETTER HEH GOAL
    '\u06C1': ('\u06C1', '\uFBA8', '\uFBA9', '\uFBA7'),
    # ARABIC LETTER KIRGHIZ OE
    '\u06C5': ('\u06C5', '', '', '\uFBE1'),
    # ARABIC LETTER OE
    '\u06C6': ('\u06C6', '', '', '\uFBDA'),
    # ARABIC LETTER U
    '\u06C7': ('\u06C7', '', '', '\uFBD8'),
    # ARABIC LETTER YU
    '\u06C8': ('\u06C8', '', '', '\uFBDC'),
    # ARABIC LETTER KIRGHIZ YU
    '\u06C9': ('\u06C9', '', '', '\uFBE3'),
    # ARABIC LETTER VE
    '\u06CB': ('\u06CB', '', '', '\uFBDF'),
    # ARABIC LETTER FARSI YEH
    '\u06CC': ('\u06CC', '\uFBFE', '\uFBFF', '\uFBFD'),
    # ARABIC LETTER E
    '\u06D0': ('\u06D0', '\uFBE6', '\uFBE7', '\uFBE5'),
    # ARABIC LETTER YEH BARREE
    '\u06D2': ('\u06D2', '', '', '\uFBAF'),
    # ARABIC LETTER YEH BARREE WITH HAMZA ABOVE
    '\u06D3': ('\u06D3', '', '', '\uFBB1'),
    # Kurdish letter YEAH
    '\u06ce': ('\uE004', '\uE005', '\uE006', '\uE004'),
    # Kurdish letter Hamza same as arabic Teh without the point
    '\u06d5': ('\u06d5', '', '', '\uE000'),
    # ZWJ
    ZWJ: (ZWJ, ZWJ, ZWJ, ZWJ),
}


def connects_with_letter_before(letter, LETTERS):
    if letter not in LETTERS:
        return False
    forms = LETTERS[letter]
    return forms[FINAL] or forms[MEDIAL]


def connects_with_letter_after(letter, LETTERS):
    if letter not in LETTERS:
        return False
    forms = LETTERS[letter]
    return forms[INITIAL] or forms[MEDIAL]


def connects_with_letters_before_and_after(letter, LETTERS):
    if letter not in LETTERS:
        return False
    forms = LETTERS[letter]
    return forms[MEDIAL]
