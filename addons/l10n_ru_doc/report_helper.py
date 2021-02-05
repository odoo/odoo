# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo
#    Copyright (C) 2014-2018 CodUP (<http://codup.com>).
#
##############################################################################

from datetime import datetime
import re
from pytils import numeral,dt
from odoo.tools import pycompat


class QWebHelper(object):

    def img(self, img, type='png', width=0, height=0) :
        if width :
            width = "width='%spx'"%(width)
        else :
            width = " "
        if height :
            height = "height='%spx'"%(height)
        else :
            height = " "
        toreturn = "<img %s %s src='data:image/%s;base64,%s' />"%(
            width,
            height,
            type, 
            str(pycompat.to_text(img)))
        return toreturn

    def numer(self, name):
        if name:
            numeration = re.findall('\d+$', name)
            if numeration: return numeration[0]
        return ''

    def ru_date(self, date):
        if date and date != 'False':
            return dt.ru_strftime(u'"%d" %B %Y года', date=datetime.strptime(str(date), "%Y-%m-%d"), inflected=True)
        return ''

    def ru_date2(self, date):
        if date and date != 'False':
            return dt.ru_strftime(u'%d %B %Y г.', date=datetime.strptime(str(date), "%Y-%m-%d %H:%M:%S"), inflected=True)
        return ''

    def in_words(self, number):
        return numeral.in_words(number)

    def rubles(self, sum):
        "Transform sum number in rubles to text"
        text_rubles = numeral.rubles(int(sum))
        copeck = round((sum - int(sum))*100)
        text_copeck = numeral.choose_plural(int(copeck), (u"копейка", u"копейки", u"копеек"))
        return ("%s %02d %s")%(text_rubles, copeck, text_copeck)

    def initials(self, fio):
        if fio:
            return (fio.split()[0]+' '+''.join([fio[0:1]+'.' for fio in fio.split()[1:]])).strip()
        return ''

    def address(self, partner):
        repr = []
        if partner.zip: repr.append(partner.zip)
        if partner.city: repr.append(partner.city)
        if partner.street: repr.append(partner.street)
        if partner.street2: repr.append(partner.street2)
        return ', '.join(repr)

    def representation(self, partner):
        repr = []
        if partner.name: repr.append(partner.name)
        if partner.inn: repr.append(u"ИНН " + partner.inn)
        if partner.kpp: repr.append(u"КПП " + partner.kpp)
        repr.append(self.address(partner))
        return ', '.join(repr)

    def full_representation(self, partner):
        repr = [self.representation(partner)]
        if partner.phone: repr.append(u"тел.: " + partner.phone)
        elif partner.parent_id.phone: repr.append(u"тел.: " + partner.parent_id.phone)
        bank = None
        if partner.bank_ids: bank = partner.bank_ids[0]
        elif partner.parent_id.bank_ids: bank = partner.parent_id.bank_ids[0]
        if bank and bank.acc_number: repr.append(u"р/сч " + bank.acc_number)
        if bank and bank.bank_name: repr.append(u"в банке " + bank.bank_name)
        if bank and bank.bank_bic: repr.append(u"БИК " + bank.bank_bic)
        if bank and bank.bank_corr_acc: repr.append(u"к/с " + bank.bank_corr_acc)
        return ', '.join(repr)
