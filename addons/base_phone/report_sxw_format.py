# -*- encoding: utf-8 -*-
##############################################################################
#
#    Base Phone module for OpenERP
#    Copyright (C) 2014 Alexis de Lattre <alexis@via.ecp.fr>
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

from openerp.osv import orm
from openerp.report import report_sxw
import phonenumbers


class base_phone_installed(orm.AbstractModel):
    '''When you use monkey patching, the code is executed when the module
    is in the addons_path of the OpenERP server, even is the module is not
    installed ! In order to avoid the side-effects it can create,
    we create an AbstractModel inside the module and we test the
    availability of this Model in the code of the monkey patching below.
    At Akretion, we call this the "Guewen trick", in reference
    to a trick used by Guewen Baconnier in the "connector" module.
    '''
    _name = "base.phone.installed"


format_original = report_sxw.rml_parse.format


def format(
        self, text, oldtag=None, phone=False, phone_format='international'):
    if self.pool.get('base.phone.installed') and phone and text:
        # text should already be in E164 format, so we don't have
        # to give a country code to phonenumbers.parse()
        phone_number = phonenumbers.parse(text)
        if phone_format == 'international':
            res = phonenumbers.format_number(
                phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        elif phone_format == 'national':
            res = phonenumbers.format_number(
                phone_number, phonenumbers.PhoneNumberFormat.NATIONAL)
        elif phone_format == 'e164':
            res = phonenumbers.format_number(
                phone_number, phonenumbers.PhoneNumberFormat.E164)
        else:
            res = text
    else:
        res = format_original(self, text, oldtag=oldtag)
    return res

report_sxw.rml_parse.format = format
