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

from . import (lang_AM, lang_AR, lang_AZ, lang_BY, lang_CZ, lang_DE, lang_DK,
               lang_EN, lang_EN_IN, lang_EN_NG, lang_EO, lang_ES, lang_ES_CO,
               lang_ES_GT, lang_ES_NI, lang_ES_VE, lang_FA, lang_FI, lang_FR,
               lang_FR_BE, lang_FR_CH, lang_FR_DZ, lang_HE, lang_HU, lang_ID,
               lang_IS, lang_IT, lang_JA, lang_KN, lang_KO, lang_KZ, lang_LT,
               lang_LV, lang_NL, lang_NO, lang_PL, lang_PT, lang_PT_BR,
               lang_RO, lang_RU, lang_SK, lang_SL, lang_SR, lang_SV, lang_TE,
               lang_TG, lang_TH, lang_TR, lang_UK, lang_VI)

CONVERTER_CLASSES = {
    'am': lang_AM.Num2Word_AM(),
    'ar': lang_AR.Num2Word_AR(),
    'az': lang_AZ.Num2Word_AZ(),
    'by': lang_BY.Num2Word_BY(),
    'cz': lang_CZ.Num2Word_CZ(),
    'en': lang_EN.Num2Word_EN(),
    'en_IN': lang_EN_IN.Num2Word_EN_IN(),
    'en_NG': lang_EN_NG.Num2Word_EN_NG(),
    'fa': lang_FA.Num2Word_FA(),
    'fr': lang_FR.Num2Word_FR(),
    'fr_CH': lang_FR_CH.Num2Word_FR_CH(),
    'fr_BE': lang_FR_BE.Num2Word_FR_BE(),
    'fr_DZ': lang_FR_DZ.Num2Word_FR_DZ(),
    'de': lang_DE.Num2Word_DE(),
    'fi': lang_FI.Num2Word_FI(),
    'eo': lang_EO.Num2Word_EO(),
    'es': lang_ES.Num2Word_ES(),
    'es_CO': lang_ES_CO.Num2Word_ES_CO(),
    'es_GT': lang_ES_GT.Num2Word_ES_GT(),
    'es_NI': lang_ES_NI.Num2Word_ES_NI(),
    'es_VE': lang_ES_VE.Num2Word_ES_VE(),
    'id': lang_ID.Num2Word_ID(),
    'ja': lang_JA.Num2Word_JA(),
    'kn': lang_KN.Num2Word_KN(),
    'ko': lang_KO.Num2Word_KO(),
    'kz': lang_KZ.Num2Word_KZ(),
    'lt': lang_LT.Num2Word_LT(),
    'lv': lang_LV.Num2Word_LV(),
    'pl': lang_PL.Num2Word_PL(),
    'ro': lang_RO.Num2Word_RO(),
    'ru': lang_RU.Num2Word_RU(),
    'sk': lang_SK.Num2Word_SK(),
    'sl': lang_SL.Num2Word_SL(),
    'sr': lang_SR.Num2Word_SR(),
    'sv': lang_SV.Num2Word_SV(),
    'no': lang_NO.Num2Word_NO(),
    'dk': lang_DK.Num2Word_DK(),
    'pt': lang_PT.Num2Word_PT(),
    'pt_BR': lang_PT_BR.Num2Word_PT_BR(),
    'he': lang_HE.Num2Word_HE(),
    'it': lang_IT.Num2Word_IT(),
    'vi': lang_VI.Num2Word_VI(),
    'tg': lang_TG.Num2Word_TG(),
    'th': lang_TH.Num2Word_TH(),
    'tr': lang_TR.Num2Word_TR(),
    'nl': lang_NL.Num2Word_NL(),
    'uk': lang_UK.Num2Word_UK(),
    'te': lang_TE.Num2Word_TE(),
    'hu': lang_HU.Num2Word_HU(),
    'is': lang_IS.Num2Word_IS()
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

    if isinstance(number, str):
        number = converter.str_to_number(number)

    # backwards compatible
    if ordinal:
        to = 'ordinal'

    if to not in CONVERTES_TYPES:
        raise NotImplementedError()

    return getattr(converter, 'to_{}'.format(to))(number, **kwargs)
