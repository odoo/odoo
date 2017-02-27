# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

def _100_to_text(chiffre):
    if chiffre in unites:
        return unites[chiffre]
    else:
        if chiffre%10>0:
            return dizaine[chiffre / 10]+'-'+unites[chiffre % 10]
        else:
            return dizaine[chiffre / 10]

def _1000_to_text(chiffre):
    d = _100_to_text(chiffre % 100)
    d2 = chiffre/100
    if d2>0 and d:
        return centaine[d2]+' '+d
    elif d2>1 and not d:
        return centaine[d2]+'s'
    else:
        return centaine[d2] or d

def _10000_to_text(chiffre):
    if chiffre==0:
        return 'zero'
    part1 = _1000_to_text(chiffre % 1000)
    part2 = mille.get(chiffre / 1000,  _1000_to_text(chiffre / 1000)+' mille')
    if part2 and part1:
        part1 = ' '+part1
    return part2+part1

def int_to_text(i):
    return _10000_to_text(i)

if __name__=='__main__':
    for i in range(1,999999,139):
        print int_to_text(i)
