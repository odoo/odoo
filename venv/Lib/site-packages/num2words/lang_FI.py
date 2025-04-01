# -*- coding: utf-8 -*-
# Copyright (c) 2003, Taro Ogawa.  All Rights Reserved.
# Copyright (c) 2013, Savoir-faire Linux inc.  All Rights Reserved.

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301 USA

from __future__ import division, print_function, unicode_literals

from collections import OrderedDict

from . import lang_EU

GENERIC_CENTS = ('sentti', 'senttiä')
GENERIC_CENTAVOS = ('centavo', 'centavoa')

# grammatical cases
NOM = 10  # nominative: the dictionary form
GEN = 11  # genitive: ~of/'s
ACC = 12  # accusative: not used; either nominative or genitive
PTV = 13  # partitive: as an object
# locative cases (internal)
INE = 14  # inessive: in
ELA = 15  # elative: from/out of
ILL = 16  # illative: into
# locative cases (external)
ADE = 17  # adessive: at/on
ABL = 18  # ablative: from (after being at/on, not in)
ALL = 19  # allative: to
# essive
ESS = 20     # essive: as (in the role of)
TRANSL = 21  # translative: to (the role of; being sth)
# rare
INSTRUC = 22  # instructive: with (plural is the same as singular)
ABE = 23      # abessive: without
COM = 24      # comitative: together with (plural = singular)

NAME_TO_CASE = {
    'nominative': NOM,
    'genitive': GEN,
    'accusative': ACC,
    'partitive': PTV,
    'inessive': INE,
    'elative': ELA,
    'illative': ILL,
    'adessive': ADE,
    'ablative': ABL,
    'allative': ALL,
    'essive': ESS,
    'translative': TRANSL,
    'instructive': INSTRUC,
    'abessive': ABE,
    'comitative': COM,
}

# https://en.wikibooks.org/wiki/Finnish/Grammar-Vowel_harmony
BACK_TO_FRONT = {
    'a': 'ä',
    'o': 'ö',
    'u': 'y',
}

# https://en.wiktionary.org/wiki/Appendix:Finnish_nominal_inflection
# CASE: (SINGULAR_SUFFIX+, PLURAL_SUFFIX+)
KOTUS_TYPE = {

    # Kotus type 5/risti, no gradation
    5: {
        # grammatical
        NOM: ('i', 'it'),
        GEN: ('in', 'ien'),
        PTV: ('ia', 'eja'),
        # locative, internal
        INE: ('issa', 'eissa'),
        ELA: ('ista', 'eista'),
        ILL: ('iin', 'eihin'),
        # locative, external
        ADE: ('illa', 'eilla'),
        ABL: ('ilta', 'eilta'),
        ALL: ('ille', 'eille'),
        # essive
        ESS: ('ina', 'eina'),
        TRANSL: ('iksi', 'eiksi'),
        # rare
        INSTRUC: ('ein', 'ein'),
        ABE: ('itta', 'eitta'),
        COM: ('eine', 'eine'),  # works better
    },

    # Kotus type 7/ovi, no gradation
    7: {
        # grammatical
        NOM: ('i', 'et'),
        GEN: ('en', 'ien'),
        PTV: ('ea', 'ia'),
        # locative, internal
        INE: ('essa', 'issa'),
        ELA: ('esta', 'ista'),
        ILL: ('een', 'iin'),
        # locative, external
        ADE: ('ella', 'illa'),
        ABL: ('elta', 'ilta'),
        ALL: ('elle', 'ille'),
        # essive
        ESS: ('ena', 'ina'),
        TRANSL: ('eksi', 'iksi'),
        # rare
        INSTRUC: ('in', 'in'),
        ABE: ('etta', 'itta'),
        COM: ('ine', 'ine'),  # works better
    },

    # Kotus type 8/nalle, no gradation
    8: {
        # grammatical
        NOM: ('e', 'et'),
        GEN: ('en', ('ejen', 'ein')),
        PTV: ('ea', 'eja'),
        # locative, internal
        INE: ('essa', 'eissa'),
        ELA: ('esta', 'eista'),
        ILL: ('een', 'eihin'),
        # locative, external
        ADE: ('ella', 'eilla'),
        ABL: ('elta', 'eilta'),
        ALL: ('elle', 'eille'),
        # essive
        ESS: ('ena', 'eina'),
        TRANSL: ('eksi', 'eiksi'),
        # rare
        INSTRUC: ('ein', 'ein'),
        ABE: ('etta', 'eitta'),
        COM: ('eine', 'eine'),  # works better
    },

    # Kotus type 9/kala, t-d gradation (sata)
    109: {
        # grammatical
        NOM: ('ta', 'dat'),
        GEN: ('dan', ('tojen', 'tain')),
        PTV: ('taa', 'toja'),
        # locative, internal
        INE: ('dassa', 'doissa'),
        ELA: ('dasta', 'doista'),
        ILL: ('taan', 'toihin'),
        # locative, external
        ADE: ('dalla', 'doilla'),
        ABL: ('dalta', 'doilta'),
        ALL: ('dalle', 'doille'),
        # essive
        ESS: ('tana', 'toina'),
        TRANSL: ('daksi', 'doiksi'),
        # rare
        INSTRUC: ('doin', 'doin'),
        ABE: ('datta', 'doitta'),
        COM: ('toine', 'toine'),  # works better
    },

    # Kotus type 10/koira, no gradation
    10: {
        # grammatical
        NOM: ('a', 'at'),
        GEN: ('an', ('ien', 'ain')),
        PTV: ('aa', 'ia'),
        # locative, internal
        INE: ('assa', 'issa'),
        ELA: ('asta', 'ista'),
        ILL: ('aan', 'iin'),
        # locative, external
        ADE: ('alla', 'illa'),
        ABL: ('alta', 'ilta'),
        ALL: ('alle', 'ille'),
        # essive
        ESS: ('ana', 'ina'),
        TRANSL: ('aksi', 'iksi'),
        # rare
        INSTRUC: ('in', 'in'),
        ABE: ('atta', 'itta'),
        COM: ('ine', 'ine'),  # works better
    },

    # Kotus type 27/käsi, t-d gradation
    27: {
        # grammatical
        NOM: ('si', 'det'),
        GEN: ('den', ('sien', 'tten')),
        PTV: ('tta', 'sia'),
        # locative, internal
        INE: ('dessa', 'sissa'),
        ELA: ('desta', 'sista'),
        ILL: ('teen', 'siin'),
        # locative, external
        ADE: ('della', 'silla'),
        ABL: ('delta', 'silta'),
        ALL: ('delle', 'sille'),
        # essive
        ESS: ('tena', 'sina'),
        TRANSL: ('deksi', 'siksi'),
        # rare
        INSTRUC: ('sin', 'sin'),
        ABE: ('detta', 'sitta'),
        COM: ('sine', 'sine'),  # works better
    },

    # Kotus type 31/kaksi, t-d gradation
    31: {
        # grammatical
        NOM: ('ksi', 'hdet'),
        GEN: ('hden', 'ksien'),
        PTV: ('hta', 'ksia'),
        # locative, internal
        INE: ('hdessa', 'ksissa'),
        ELA: ('hdesta', 'ksista'),
        ILL: ('hteen', 'ksiin'),
        # locative, external
        ADE: ('hdella', 'ksilla'),
        ABL: ('hdelta', 'ksilta'),
        ALL: ('hdelle', 'ksille'),
        # essive
        ESS: ('htena', 'ksina'),
        TRANSL: ('hdeksi', 'ksiksi'),
        # rare
        INSTRUC: ('ksin', 'ksin'),
        ABE: ('hdetta', 'ksitta'),
        COM: ('ksine', 'ksine'),  # works better
    },

    # Kotus type 32/sisar, no gradation
    32: {
        # grammatical
        NOM: ('', 'et'),
        GEN: ('en', ('ien', 'ten')),
        PTV: ('ta', 'ia'),
        # locative, internal
        INE: ('essa', 'issa'),
        ELA: ('esta', 'ista'),
        ILL: ('een', 'iin'),
        # locative, external
        ADE: ('ella', 'illa'),
        ABL: ('elta', 'ilta'),
        ALL: ('elle', 'ille'),
        # essive
        ESS: ('ena', 'ina'),
        TRANSL: ('eksi', 'iksi'),
        # rare
        INSTRUC: ('in', 'in'),
        ABE: ('etta', 'itta'),
        COM: ('ine', 'ine'),  # works better
    },

    # Kotus type 38/nainen, no gradation
    38: {
        # grammatical
        NOM: ('nen', 'set'),
        GEN: ('sen', ('sten', 'sien')),
        PTV: ('sta', 'sia'),
        # locative, internal
        INE: ('sessa', 'sissa'),
        ELA: ('sesta', 'sista'),
        ILL: ('seen', 'siin'),
        # locative, external
        ADE: ('sella', 'silla'),
        ABL: ('selta', 'silta'),
        ALL: ('selle', 'sille'),
        # essive
        ESS: ('sena', 'sina'),
        TRANSL: ('seksi', 'siksi'),
        # rare
        INSTRUC: ('sin', 'sin'),
        ABE: ('setta', 'sitta'),
        COM: ('sine', 'sine'),  # works better
    },

    # Kotus type 45/kahdeksas, nt-nn gradation
    45: {
        # grammatical
        NOM: ('s', 'nnet'),
        GEN: ('nnen', 'nsien'),
        PTV: ('tta', 'nsia'),
        # locative, internal
        INE: ('nnessa', 'nsissa'),
        ELA: ('nnesta', 'nsista'),
        ILL: ('nteen', 'nsiin'),
        # locative, external
        ADE: ('nnella', 'nsilla'),
        ABL: ('nnelta', 'nsilta'),
        ALL: ('nnelle', 'nsille'),
        # essive
        ESS: ('ntena', 'nsina'),
        TRANSL: ('nneksi', 'nsiksi'),
        # rare
        INSTRUC: ('nsin', 'nsin'),
        ABE: ('nnetta', 'nsitta'),
        COM: ('nsine', 'nsine'),  # works better
    },

    # Kotus type 46/tuhat, nt-nn gradation
    46: {
        # grammatical
        NOM: ('t', 'nnet'),
        GEN: ('nnen', ('nsien', 'nten')),
        PTV: ('tta', 'nsia'),
        # locative, internal
        INE: ('nnessa', 'nsissa'),
        ELA: ('nnesta', 'nsista'),
        ILL: ('nteen', 'nsiin'),
        # locative, external
        ADE: ('nnella', 'nsilla'),
        ABL: ('nnelta', 'nsilta'),
        ALL: ('nnelle', 'nsille'),
        # essive
        ESS: ('ntena', 'nsina'),
        TRANSL: ('nneksi', 'nsiksi'),
        # rare
        INSTRUC: ('nsin', 'nsin'),
        ABE: ('nnetta', 'nsitta'),
        COM: ('nsine', 'nsine'),  # works better
    },
}

# kolme
KOTUS_TYPE[108] = {
    c: (KOTUS_TYPE[8][c][0], KOTUS_TYPE[7][c][1])
    for c in KOTUS_TYPE[8]
}
KOTUS_TYPE[108][INSTRUC] = ('en', 'in')
KOTUS_TYPE[108][ABE] = ('etta', 'itta')
KOTUS_TYPE[108][COM] = ('ine', 'ine')

# seitsemän, kahdeksan, yhdeksän
KOTUS_TYPE[110] = KOTUS_TYPE[10].copy()
KOTUS_TYPE[110][NOM] = ('an', 'at')

# kymmenen
KOTUS_TYPE[132] = KOTUS_TYPE[32].copy()
KOTUS_TYPE[132][NOM] = ('en', 'et')


def inflect(parts, options):
    if not isinstance(parts, list):
        parts = [parts]

    out = ''
    for part in parts:
        # part is plain text, concat and continue
        if not isinstance(part, tuple):
            out += part
            continue
        # predefined case (kaksikymmentä, ...)
        tmp_case = options.case
        if len(part) == 3:
            # override singular nominative only
            if options.case == NOM and not options.plural:
                tmp_case = part[2]
            part = part[:2]
        # stem and suffix
        stem, kotus_type = part
        suffix = KOTUS_TYPE[kotus_type][tmp_case][options.plural]
        # many choices, choose preferred or first
        if isinstance(suffix, tuple):
            common = set(suffix) & set(options.prefer or set())
            if len(common) == 1:
                suffix = common.pop()
            else:
                suffix = suffix[0]
        # apply vowel harmony
        if not set(BACK_TO_FRONT) & set(stem):
            for back, front in BACK_TO_FRONT.items():
                suffix = suffix.replace(back, front)
        # concat
        out += stem + suffix

    return out


class Options(object):
    def __init__(self, ordinal, case, plural, prefer):
        self.ordinal = ordinal
        self.case = case
        self.plural = plural
        self.prefer = prefer

    def variation(self, ordinal=None, case=None, plural=None, prefer=None):
        return Options(
            ordinal if ordinal is not None else self.ordinal,
            case if case is not None else self.case,
            plural if plural is not None else self.plural,
            prefer if prefer is not None else self.prefer,
        )


class Num2Word_FI(lang_EU.Num2Word_EU):
    CURRENCY_FORMS = {
        'BRL': (('real', 'realia'), GENERIC_CENTAVOS),
        'CHF': (('frangi', 'frangia'), ('rappen', 'rappenia')),
        'CNY': (('juan', 'juania'), ('fen', 'feniä')),
        'EUR': (('euro', 'euroa'), GENERIC_CENTS),
        'FIM': (('markka', 'markkaa'), ('penni', 'penniä')),  # historical
        'INR': (('rupia', 'rupiaa'), ('paisa', 'paisaa')),
        'JPY': (('jeni', 'jeniä'), ('sen', 'seniä')),  # rare subunit
        'KRW': (('won', 'wonia'), ('jeon', 'jeonia')),  # rare subunit
        'KPW': (('won', 'wonia'), ('chon', 'chonia')),  # rare subunit
        'MXN': (('peso', 'pesoa'), GENERIC_CENTAVOS),
        'RUB': (('rupla', 'ruplaa'), ('kopeekka', 'kopeekkaa')),
        'TRY': (('liira', 'liiraa'), ('kuruş', 'kuruşia')),
        'ZAR': (('randi', 'randia'), GENERIC_CENTS),
    }

    # crowns
    for curr_code in 'DKK', 'ISK', 'NOK', 'SEK':
        CURRENCY_FORMS[curr_code] = (('kruunu', 'kruunua'), ('äyri', 'äyriä'))

    # dollars
    for curr_code in 'AUD', 'CAD', 'HKD', 'NZD', 'SGD', 'USD':
        CURRENCY_FORMS[curr_code] = (
            ('dollari', 'dollaria'), GENERIC_CENTS)

    # pounds
    for curr_code in ('GBP',):
        CURRENCY_FORMS[curr_code] = (('punta', 'puntaa'), ('penny', 'pennyä'))

    CURRENCY_ADJECTIVES = {
        'AUD': 'Australian',
        'BRL': 'Brasilian',
        'CAD': 'Kanadan',
        'CHF': 'Sveitsin',
        'DKK': 'Tanskan',
        'FIM': 'Suomen',  # historical
        'GBP': 'Englannin',
        'HKD': 'Hongkongin',
        'INR': 'Intian',
        'ISK': 'Islannin',
        'KRW': 'Etelä-Korean',
        'KPW': 'Pohjois-Korean',
        'MXN': 'Meksikon',
        'NOK': 'Norjan',
        'NZD': 'Uuden-Seelannin',
        'RUB': 'Venäjän',
        'SEK': 'Ruotsin',
        'SGD': 'Singaporen',
        'TRY': 'Turkin',
        'USD': 'Yhdysvaltain',
        'ZAR': 'Etelä-Afrikan',
    }

    def __init__(self):
        self.ords = OrderedDict()
        super(Num2Word_FI, self).__init__()

    def set_numwords(self):
        self.set_high_numwords(self.high_numwords)
        self.set_mid_numwords(self.mid_numwords, self.mid_ords)
        self.set_low_numwords(self.low_numwords, self.low_ords)

    def set_high_numwords(self, high):
        # references:
        # https://fi.wikipedia.org/wiki/Suurten_lukujen_nimet
        # https://en.wikipedia.org/wiki/Names_of_large_numbers#Standard_dictionary_numbers

        # translate to Finnish
        replacements = [
            ("qu", "kv"),
            ("x", "ks"),
            ("c", "k"),
            ("kent", "sent"),  # applied after c -> k to cent
        ]
        translated = []
        for i, numword in enumerate(high):
            # notes:
            # - 1e6**9 can be either noviljoona or noniljoona
            # - 1e6**38 and above are untested

            # 1e6**6 is sekstiljoona but 1e6**16 is sedekiljoona
            if numword.startswith("sex") and numword != "sext":
                numword = numword.replace("sex", "se")
            # 1e6**7 is septiljoona but 1e6**17 is septendekiljoona
            elif numword.startswith("sept") and numword != "sept":
                numword = "septen" + numword[len("sept"):]
            # 1e6**8 is oktiljoona but 1e6**18 is duodevigintiljoona
            # (2 from 20)
            elif numword.startswith("octo"):
                numword = high[i + -10]
                numword = "duode" + numword[len("octo"):]
            # 1e6**9 is noniljoona but 1e6**19 is undevigintiljoona (1 from 20)
            elif numword.startswith("nove"):
                numword = high[i + -10]
                numword = "unde" + numword[len("nove") + 1:]

            # apply general replacements to all numwords
            for repl in replacements:
                numword = numword.replace(repl[0], repl[1])
            translated.append(numword)

        max = 6 * len(translated)
        for word, n in zip(translated, range(max, 0, -6)):
            if n == 6:
                # irregularity considering short scale and long scale
                self.cards[10 ** 9] = ("miljard", 5)
                self.ords[10 ** 9] = ("miljardi", 45)
            self.cards[10 ** n] = (word + "iljoon", 10)
            self.ords[10 ** n] = (word + "iljoona", 45)

    def set_mid_numwords(self, cards, ords):
        for key, val in cards:
            self.cards[key] = val
        for key, val in ords:
            self.ords[key] = val

    def set_low_numwords(self, cards, ords):
        for key, val in cards:
            self.cards[key] = val
        for key, val in ords:
            self.ords[key] = val

    def setup(self):
        super(Num2Word_FI, self).setup()

        self.negword = "miinus "
        self.pointword = "pilkku"
        self.exclude_title = ["pilkku", "miinus"]

        self.mid_numwords = [
            (1000, ("tuha", 46)),
            (100, ("sa", 109)),
            (90, [("yhdeks", 110), ("kymmen", 132, PTV)]),
            (80, [("kahdeks", 110), ("kymmen", 132, PTV)]),
            (70, [("seitsem", 110), ("kymmen", 132, PTV)]),
            (60, [("kuu", 27), ("kymmen", 132, PTV)]),
            (50, [("vii", 27), ("kymmen", 132, PTV)]),
            (40, [("nelj", 10), ("kymmen", 132, PTV)]),
            (30, [("kolm", 108), ("kymmen", 132, PTV)]),
        ]

        self.mid_ords = [
            (1000, ("tuhanne", 45)),
            (100, ("sada", 45)),
            (90, [("yhdeksä", 45), ("kymmene", 45)]),
            (80, [("kahdeksa", 45), ("kymmene", 45)]),
            (70, [("seitsemä", 45), ("kymmene", 45)]),
            (60, [("kuude", 45), ("kymmene", 45)]),
            (50, [("viide", 45), ("kymmene", 45)]),
            (40, [("neljä", 45), ("kymmene", 45)]),
            (30, [("kolma", 45), ("kymmene", 45)]),
        ]

        self.low_numwords = [
            (20, [("ka", 31), ("kymmen", 132, PTV)]),
            (19, [("yhdeks", 110), "toista"]),
            (18, [("kahdeks", 110), "toista"]),
            (17, [("seitsem", 110), "toista"]),
            (16, [("kuu", 27), "toista"]),
            (15, [("vii", 27), "toista"]),
            (14, [("nelj", 10), "toista"]),
            (13, [("kolm", 108), "toista"]),
            (12, [("ka", 31), "toista"]),
            (11, [("y", 31), "toista"]),
            (10, ("kymmen", 132)),
            (9, ("yhdeks", 110)),
            (8, ("kahdeks", 110)),
            (7, ("seitsem", 110)),
            (6, ("kuu", 27)),
            (5, ("vii", 27)),
            (4, ("nelj", 10)),
            (3, ("kolm", 108)),
            (2, ("ka", 31)),
            (1, ("y", 31)),
            (0, ("noll", 10)),
        ]

        self.low_ords = [
            (20, [("kahde", 45), ("kymmene", 45)]),
            (19, [("yhdeksä", 45), "toista"]),
            (18, [("kahdeksa", 45), "toista"]),
            (17, [("seitsemä", 45), "toista"]),
            (16, [("kuude", 45), "toista"]),
            (15, [("viide", 45), "toista"]),
            (14, [("neljä", 45), "toista"]),
            (13, [("kolma", 45), "toista"]),
            (12, [("kahde", 45), "toista"]),
            (11, [("yhde", 45), "toista"]),
            (10, ("kymmene", 45)),
            (9, ("yhdeksä", 45)),
            (8, ("kahdeksa", 45)),
            (7, ("seitsemä", 45)),
            (6, ("kuude", 45)),
            (5, ("viide", 45)),
            (4, ("neljä", 45)),
            (3, ("kolma", 45)),
            (2, ("toi", 38)),
            (1, ("ensimmäi", 38)),
            (0, ("nolla", 45)),
        ]

    def merge(self, lpair, rpair, options):
        ltext, lnum = lpair
        rtext, rnum = rpair

        # http://www.kielitoimistonohjepankki.fi/ohje/49
        fmt = "%s%s"
        # ignore lpair if lnum is 1
        if lnum == 1:
            rtext = inflect(rtext, options)
            return (rtext, rnum)
        # rnum is added to lnum
        elif lnum > rnum:
            ltext = inflect(ltext, options)
            rtext = inflect(rtext, options)
            # separate groups with space
            if lnum >= 1000:
                fmt = "%s %s"
            return (fmt % (ltext, rtext), lnum + rnum)
        # rnum is multiplied by lnum
        elif lnum < rnum:
            if options.ordinal:
                # kahdessadas, not toinensadas
                if lnum == 2:
                    ltext = ("kahde", 45)
                rtext = inflect(rtext, options)
            else:
                # kaksituhatta but kahdettuhannet
                rcase = options.case
                if options.case == NOM and not options.plural:
                    rcase = PTV
                rtext = inflect(rtext, options.variation(case=rcase))
            ltext = inflect(ltext, options)
            return (fmt % (ltext, rtext), lnum * rnum)

    def to_cardinal(self, value, case='nominative', plural=False, prefer=None):
        case = NAME_TO_CASE[case]
        options = Options(False, case, plural, prefer)
        try:
            assert int(value) == value
        except (ValueError, TypeError, AssertionError):
            if case != NOM:
                raise NotImplementedError(
                    "Cases other than nominative are not implemented for "
                    "cardinal floating point numbers.")
            return self.to_cardinal_float(value)

        out = ""
        if value < 0:
            value = abs(value)
            out = self.negword

        if value >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig % (value, self.MAXVAL))

        val = self.splitnum(value, options)
        words, num = self.clean(val, options)
        return self.title(out + words)

    def to_ordinal(self, value, case='nominative', plural=False, prefer=None):
        case = NAME_TO_CASE[case]
        options = Options(True, case, plural, prefer)

        self.verify_ordinal(value)
        if value >= self.MAXVAL:
            raise OverflowError(self.errmsg_toobig % (value, self.MAXVAL))

        val = self.splitnum(value, options)
        words, num = self.clean(val, options)
        return self.title(words)

    def to_ordinal_num(self, value, case='nominative', plural=False):
        case = NAME_TO_CASE[case]
        raise NotImplementedError

    def to_year(self, val, suffix=None, longval=True):
        suffix = suffix or ""
        if val < 0:
            val = abs(val)
            suffix = suffix or " ennen ajanlaskun alkua"
        return self.to_cardinal(val).replace(" ", "") + suffix

    def to_currency(self, val, currency="EUR", cents=True, seperator=" ja",
                    adjective=False):
        return super(Num2Word_FI, self).to_currency(
            val, currency=currency, cents=cents, seperator=seperator,
            adjective=adjective)

    def splitnum(self, value, options):
        elems = self.ords if options.ordinal else self.cards
        for elem in elems:
            if elem > value:
                continue

            out = []
            if value == 0:
                div, mod = 1, 0
            else:
                div, mod = divmod(value, elem)

            if div == 1:
                out.append((elems[1], 1))
            else:
                if div == value:  # The system tallies, eg Roman Numerals
                    return [(div * elems[elem], div*elem)]
                out.append(self.splitnum(div, options))

            out.append((elems[elem], elem))

            if mod:
                out.append(self.splitnum(mod, options))

            return out

    def clean(self, val, options):
        out = val
        while len(val) != 1:
            out = []
            left, right = val[:2]
            if isinstance(left, tuple) and isinstance(right, tuple):
                out.append(self.merge(left, right, options))
                if val[2:]:
                    out.append(val[2:])
            else:
                for elem in val:
                    if isinstance(elem, list):
                        if len(elem) == 1:
                            out.append(elem[0])
                        else:
                            out.append(self.clean(elem, options))
                    else:
                        out.append(elem)
            val = out
        return out[0]
