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

from __future__ import unicode_literals

from . import lang_AR
from . import lang_CZ
from . import lang_EN
from . import lang_EN_IN
from . import lang_FR
from . import lang_FR_CH
from . import lang_FR_BE
from . import lang_FR_DZ
from . import lang_DE
from . import lang_ES
from . import lang_FI
from . import lang_LT
from . import lang_LV
from . import lang_PL
from . import lang_RO
from . import lang_RU
from . import lang_ID
from . import lang_JA
from . import lang_NO
from . import lang_DK
from . import lang_PT
from . import lang_PT_BR
from . import lang_HE
from . import lang_IT
from . import lang_ES_VE
from . import lang_ES_CO
from . import lang_VI
from . import lang_TR
from . import lang_NL
from . import lang_UK
from . import lang_SL
from . import lang_SR
from . import lang_TH
from . import lang_KO

CONVERTER_CLASSES = {
    'ar': lang_AR.Num2Word_AR(),
    'cz': lang_CZ.Num2Word_CZ(),
    'en': lang_EN.Num2Word_EN(),
    'en_IN': lang_EN_IN.Num2Word_EN_IN(),
    'fr': lang_FR.Num2Word_FR(),
    'fr_CH': lang_FR_CH.Num2Word_FR_CH(),
    'fr_BE': lang_FR_BE.Num2Word_FR_BE(),
    'fr_DZ': lang_FR_DZ.Num2Word_FR_DZ(),
    'de': lang_DE.Num2Word_DE(),
    'fi': lang_FI.Num2Word_FI(),
    'es': lang_ES.Num2Word_ES(),
    'es_CO': lang_ES_CO.Num2Word_ES_CO(),
    'es_VE': lang_ES_VE.Num2Word_ES_VE(),
    'id': lang_ID.Num2Word_ID(),
    'ja': lang_JA.Num2Word_JA(),
    'ko': lang_KO.Num2Word_KO(),
    'lt': lang_LT.Num2Word_LT(),
    'lv': lang_LV.Num2Word_LV(),
    'pl': lang_PL.Num2Word_PL(),
    'ro': lang_RO.Num2Word_RO(),
    'ru': lang_RU.Num2Word_RU(),
    'sl': lang_SL.Num2Word_SL(),
    'sr': lang_SR.Num2Word_SR(),
    'no': lang_NO.Num2Word_NO(),
    'dk': lang_DK.Num2Word_DK(),
    'pt': lang_PT.Num2Word_PT(),
    'pt_BR': lang_PT_BR.Num2Word_PT_BR(),
    'he': lang_HE.Num2Word_HE(),
    'it': lang_IT.Num2Word_IT(),
    'vi': lang_VI.Num2Word_VI(),
    'th': lang_TH.Num2Word_TH(),
    'tr': lang_TR.Num2Word_TR(),
    'nl': lang_NL.Num2Word_NL(),
    'uk': lang_UK.Num2Word_UK()
}


CONVERTES_TYPES = ['cardinal', 'ordinal', 'ordinal_num', 'year', 'currency']


def num2words(number, ordinal=False, lang='en', to='cardinal', **kwargs):
    # We try the full language first
    if lang not in CONVERTER_CLASSES:
        # ... and then try only the first 2 letters
        lang = lang[:2]
    if lang not in CONVERTER_CLASSES:
        raise NotImplementedError()
    converter = CONVERTER_CLASSES[lang]
    # backwards compatible
    if ordinal:
        return converter.to_ordinal(number)

    if to not in CONVERTES_TYPES:
        raise NotImplementedError()

    return getattr(converter, 'to_{}'.format(to))(number, **kwargs)
