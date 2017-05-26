# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from translate import _

_logger = logging.getLogger(__name__)

#-------------------------------------------------------------
#SPANISH
#-------------------------------------------------------------

to_9_es = ( '',  'Un', 'Dos', 'Tres', 'Cuatro', 'Cinco', 'Seis', 'Siete', 'Ocho', 'Nueve')
ten_to_19_es = ('Cero', 'Diez', 'Once', 'Doce', 'Trece', 'Catorce', 'Quince', 'Dieciseis', 'Diecisiete',
                'Dieciocho', 'Diecinueve')
tens_es  = ( '', 'Diez', 'Veinte', 'Treinta', 'Cuarenta', 'Cincuenta', 'Sesenta', 'Setenta',
             'Ochenta', 'Noventa')
cents_es = ( '', 'Ciento', 'Doscientos', 'Trescientos', 'Cuatrocientos', 'Quinientos', 'Seiscientos',
             'Setecientos', 'Ochocientos', 'Novecientos')

def _convert_nn_es(val):
    """ convert a value < 100 to spanish
    """
    if val < 10:
        return to_9_es[val]
    tens, units = divmod(val, 10)
    if val <= 19:
        word = tens[units]
    elif val == 20:
        word = 'Veinte'
    elif val <= 29:
        word = 'Veinte y %s' % to_9_es[units]
    else:
        word = tens_es[tens]
        if units > 0:
            word = '%s y %s' % (word, to_9_es[units])
    return word

def _convert_nnn_es(val):
    """ convert a value < 1000 to spanish
    """
    hundreds, tens = divmod(val, 100)
    if val == 100:
        word = 'Cien'
    else:
        word = cents_es[hundreds]
        if tens > 0:
            word = '%s %s' % (word, _convert_nn_es(tens))
    return word

def _convert_nnnn_es(val):
    """ convert a value < 10000 to spanish
    """
    thousands, hundreds = divmod(val, 1000)
    word = ''
    if (thousands == 1):
        word = ''
    if (thousands >= 2) and (thousands <= 9):
        word = to_9_es[thousands]
    elif (thousands >= 10) and (thousands <= 99):
        word = _convert_nn_es(thousands)
    elif (thousands >= 100) and (thousands <= 999):
        word = _convert_nnn_es(thousands)
    word = '%s Mil' % word
    if hundreds > 0:
        word = '%s %s' % (word, _convert_nnn_es(hundreds))
    return word

def _convert_nnnnn_es(val):
    """ convert a value < 100000 to spanish
    """
    millions, thousands = divmod(val, 1000000)
    word = ''
    if (millions == 1):
        word = 'Un Millon'
    if (millions >= 2) and (millions <= 9):
        word = to_9_es[millions]
    elif (millions >= 10) and (millions <= 99):
        word = _convert_nn_es(millions)
    elif (millions >= 100) and (millions <= 999):
        word = _convert_nnn_es(millions)
    if millions > 1:
        word = '%s Millones' % word
    if (thousands > 0) and (thousands <= 999):
        word = '%s %s' % (word, _convert_nnn_es(thousands))
    elif (thousands >= 1000) and (thousands <= 999999):
        word = '%s %s' % (word, _convert_nnnn_es(thousands))
    return word

def spanish_number(val):
    if val < 100:
        return _convert_nn_es(val)
    if val < 1000:
         return _convert_nnn_es(val)
    if val < 10000:
         return _convert_nnnn_es(val)
    if val < 1000000000:
         return _convert_nnnnn_es(val)

def amount_to_text_es(number, currency):
    number = '%.2f' % number
    units_name = currency
    list = str(number).split('.')
    start_word = spanish_number(abs(int(list[0])))
    end_word = spanish_number(int(list[1]))
    cents_number = int(list[1])
    cents_name = (cents_number <> 1) and 'Centavos' or 'Centavo'
    final_result = start_word +' '+units_name+' con '+ end_word +' '+cents_name
    return final_result

#-------------------------------------------------------------
# Generic functions
#-------------------------------------------------------------

_translate_funcs = {'es' : amount_to_text_es}
    
#TODO: we should use the country AND language (ex: septante VS soixante dix)
#TODO: we should use en by default, but the translation func is yet to be implemented
def amount_to_text(nbr, lang='es', currency='euro'):
    """ Converts an integer to its textual representation, using the language set in the context if any.
    
        Example::
        
            1654: thousands six cent cinquante-quatre.
    """
    import odoo.loglevels as loglevels
#    if nbr > 10000000:
#        _logger.warning(_("Number too large '%d', can not translate it"))
#        return str(nbr)
    
    if not _translate_funcs.has_key(lang):
        _logger.warning(_("no translation function found for lang: '%s'"), lang)
        #TODO: (default should be en) same as above
        lang = 'en'
    return _translate_funcs[lang](abs(nbr), currency)

if __name__=='__main__':
    from sys import argv
    
    lang = 'nl'
    if len(argv) < 2:
        for i in range(1,200):
            print i, ">>", int_to_text(i, lang)
        for i in range(200,999999,139):
            print i, ">>", int_to_text(i, lang)
    else:
        print int_to_text(int(argv[1]), lang)
