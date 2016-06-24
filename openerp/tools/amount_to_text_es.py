# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from translate import _

_logger = logging.getLogger(__name__)

# -------------------------------------------------------------
# Español
# -------------------------------------------------------------

to_19 = ('Cero', 'Un', 'Dos', 'Tres', 'Cuatro', 'Cinco', 'Seis',
         'Siete', 'Ocho', 'Nueve', 'Diez', 'Once', 'Doce', 'Trece',
         'Catorce', 'Quince', 'Dieciséis', 'Diecisiete', 'Dieciocho',
         'Diecinueve')
tens = (
'Veinte', 'Treinta', 'Cuarenta', 'Cincuenta', 'Sesenta', 'Setenta', 'Ochenta',
'Noventa')
denom = ('',
         'Mil', 'Millón', 'Billón', 'Trillón', 'Cuatrillón',
         'Quintillón', 'Sextillion', 'Septillion', 'Octillion', 'Nonillion',
         'Decillion', 'Undecillion', 'Duodecillion', 'Tredecillion',
         'Quattuordecillion',
         'Sexdecillion', 'Septendecillion', 'Octodecillion', 'Novemdecillion',
         'Vigintillion')


def _convert_nn(val):
    if val < 20:
        return to_19[val]
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens)):
        if dval + 10 > val:
            if val % 10:
                return dcap + '-' + to_19[val % 10]
            return dcap


def _convert_nnn(val):
    word = ''
    (mod, rem) = (val % 100, val // 100)
    if rem > 1:
        word = to_19[rem] + 'Cientos'
        if mod > 0:
            word += ' '
    else:
        word = 'Cien'
        if mod > 0:
            word += ' '
    if mod > 0:
        word += _convert_nn(mod)
    return word


def spanish_number(val):
    if val < 100:
        return _convert_nn(val)
    if val < 1000:
        return _convert_nnn(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)

            if denom[didx] == "Mil":
                if l > 1:
                    ret = _convert_nnn(l) + ' ' + denom[didx]
                else:
                    ret = denom[didx]
            else:
                if l > 1:
                    ret = _convert_nnn(l) + ' ' + denom[didx] + 'es de '
                else:
                    ret = _convert_nnn(l) + ' ' + denom[didx] + ' de '
            if r > 0:
                ret = ret + ', ' + spanish_number(r)
            return ret


def amount_to_text(number, currency):
    number = '%.2f' % number
    units_name = currency
    number = number.replace('.', ',')
    list = number.split(',')

    if len(list[1]) > 2:
        start_word = spanish_number(int(list[0]))
    else:
        number = str(number).replace(',', '.')
        start_word = spanish_number(int(float(number)))

    end_word = ""
    if len(list) > 1:
        end_word = spanish_number(int(list[1]))

    return ' '.join(filter(None, [(start_word or end_word), units_name]))


# -------------------------------------------------------------
# Generic functions
# -------------------------------------------------------------

_translate_funcs = {'es': amount_to_text}


def amount_to_text(nbr, lang='es', currency='Pesos'):
    if not _translate_funcs.has_key(lang):
        lang = 'es'
    return _translate_funcs[lang](abs(nbr), currency)


if __name__ == '__main__':
    from sys import argv

    lang = 'nl'
