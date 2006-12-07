# -*- coding: iso8859-1 -*-
##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

#-------------------------------------------------------------
# French
#-------------------------------------------------------------

unites = {
	0: '', 1:'un', 2:'deux', 3:'trois', 4:'quatre', 5:'cinq', 6:'six', 7:'sept', 8:'huit', 9:'neuf',
	10:'dix', 11:'onze', 12:'douze', 13:'treize', 14:'quatorze', 15:'quinze', 16:'seize',
	21:'vingt et un', 31:'trente et un', 41:'quarante et un', 51:'cinquante et un', 61:'soixante et un',
	71:'septante et un', 91:'nonante et un', 80:'quatre-vingts'
}

dizaine = {
	1: 'dix', 2:'vingt', 3:'trente',4:'quarante', 5:'cinquante', 6:'soixante', 7:'septante', 8:'quatre-vingt', 9:'nonante'
}

centaine = {
	0:'', 1: 'cent', 2:'deux cent', 3:'trois cent',4:'quatre cent', 5:'cinq cent', 6:'six cent', 7:'sept cent', 8:'huit cent', 9:'neuf cent'
}

mille = {
	0:'', 1:'mille'
}

def _100_to_text_fr(chiffre):
	if chiffre in unites:
		return unites[chiffre]
	else:
		if chiffre%10>0:
			return dizaine[chiffre / 10]+'-'+unites[chiffre % 10]
		else:
			return dizaine[chiffre / 10]

def _1000_to_text_fr(chiffre):
	d = _100_to_text_fr(chiffre % 100)
	d2 = chiffre/100
	if d2>0 and d:
		return centaine[d2]+' '+d
	elif d2>1 and not(d):
		return centaine[d2]+'s'
	else:
		return centaine[d2] or d

def _10000_to_text_fr(chiffre):
	if chiffre==0:
		return 'zero'
	part1 = _1000_to_text_fr(chiffre % 1000)
	part2 = mille.get(chiffre / 1000,  _1000_to_text_fr(chiffre / 1000)+' mille')
	if part2 and part1:
		part1 = ' '+part1
	return part2+part1
	
def amount_to_text_fr(number, currency):
	units_number = int(number)
	units_name = currency
	if units_number > 1:
		units_name += 's'
	units = _10000_to_text_fr(units_number)
	units = units_number and '%s %s' % (units, units_name) or ''
	
	cents_number = int(number * 100) % 100
	cents_name = (cents_number > 1) and 'cents' or 'cent'
	cents = _100_to_text_fr(cents_number)
	cents = cents_number and '%s %s' % (cents, cents_name) or ''
	
	if units and cents:
		cents = ' '+cents
		
	return units + cents

#-------------------------------------------------------------
# Dutch
#-------------------------------------------------------------

units_nl = {
	0:'', 1:'een', 2:'twee', 3:'drie', 4:'vier', 5:'vijf', 6:'zes', 7:'zeven', 8:'acht', 9:'negen',
	10:'tien', 11:'elf', 12:'twaalf', 13:'dertien', 14:'veertien' 
}

tens_nl = {
	1: 'tien', 2:'twintig', 3:'dertig',4:'veertig', 5:'vijftig', 6:'zestig', 7:'zeventig', 8:'tachtig', 9:'negentig'
}

hundreds_nl = {
	0:'', 1: 'honderd', 
}

thousands_nl = {
	0:'', 1:'duizend'
}

def _100_to_text_nl(number):
	if number in units_nl:
		return units_nl[number]
	else:
		if number%10 > 0:
			if number>10 and number<20:
				return units_nl[number % 10]+tens_nl[number / 10]
			else:
				units = units_nl[number % 10]
				if units[-1] == 'e':
					joinword = 'ën'
				else:
					joinword = 'en'
				return units+joinword+tens_nl[number / 10]
		else:
			return tens_nl[number / 10]

def _1000_to_text_nl(number):
	part1 = _100_to_text_nl(number % 100)
	part2 = hundreds_nl.get(number / 100, units_nl[number/100] + hundreds_nl[1])
	if part2 and part1:
		part1 = ' ' + part1
	return part2 + part1

def _10000_to_text_nl(number):
	if number==0:
		return 'nul'
	part1 = _1000_to_text_nl(number % 1000)
	if thousands_nl.has_key(number / 1000):
		part2 = thousands_nl[number / 1000]
	else:
		if (number / 1000 % 100 > 0) and (number / 1000 > 100):
			space = ' '
		else:
			space = ''
		part2 = _1000_to_text_nl(number / 1000) + space + thousands_nl[1]
	if part2 and part1:
		part1 = ' ' + part1
	return part2 + part1
	
def amount_to_text_nl(number, currency):
	units_number = int(number)
	units_name = currency
	units = _10000_to_text_nl(units_number)
	units = units_number and '%s %s' % (units, units_name) or ''
	
	cents_number = int(number * 100) % 100
	cents_name = 'cent'
	cents = _100_to_text_nl(cents_number)
	cents = cents_number and '%s %s' % (cents, cents_name) or ''

	if units and cents:
		cents = ' ' + cents
		
	return units + cents

#-------------------------------------------------------------
# Generic functions
#-------------------------------------------------------------

_translate_funcs = {'fr' : amount_to_text_fr, 'nl' : amount_to_text_nl}
	
#TODO: we should use the country AND language (ex: septante VS soixante dix)
#TODO: we should use en by default, but the translation func is yet to be implemented
def amount_to_text(nbr, lang='fr', currency='euro'):
	"""
	Converts an integer to its textual representation, using the language set in the context if any.
	Example:
		1654: mille six cent cinquante-quatre.
	"""
	if nbr > 1000000:
#TODO: use logger	
		print "WARNING: number too large '%d', can't translate it!" % (nbr,)
		return str(nbr)
	
	if not _translate_funcs.has_key(lang):
#TODO: use logger	
		print "WARNING: no translation function found for lang: '%s'" % (lang,)
#TODO: (default should be en) same as above
		lang = 'fr'
	return _translate_funcs[lang](nbr, currency)

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

