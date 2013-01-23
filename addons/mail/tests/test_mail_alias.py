# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.tools import mute_logger
from openerp.tests import common

class test_mail_alias(common.TransactionCase):

    def setUp(self):
        super(test_mail_alias, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.ir_model = self.registry('ir.model')
        self.mail_alias = self.registry('mail.alias')

    #@mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
    def test_00_mail_alias(self):
        """ Testing mail_group access rights and basic mail_thread features """
        cr, uid = self.cr, self.uid

        alias_name_0 = "global+alias+test_0"
        alias_name_1 = "document+alias+test_1"
        alias_defaults_1 = {'field_pigs': 11}
        alias_name_2 = "document+alias+test_2"
        alias_defaults_2 = {'field_pigs': 112}

        # Create an alias
        partner_model_id = self.ir_model.search(cr, uid, [('model', '=', 'mail.alias')])[0]
        alias_id_0 = self.mail_alias.create(cr, uid,
            {'alias_model_id': partner_model_id, 'alias_name': alias_name_0, 'alias_defaults': {}})
        alias_id_1 = self.mail_alias.create(cr, uid,
            {'alias_model_id': partner_model_id, 'alias_name': alias_name_1, 'alias_defaults': alias_defaults_1})
        alias_id_2 = self.mail_alias.create(cr, uid,
            {'alias_model_id': partner_model_id, 'alias_name': alias_name_2, 'alias_defaults': alias_defaults_2})

        # alias of the model and alias for a docmuent
        alias = self.mail_alias.get_alias(cr, uid, 'mail.alias', {'field_pigs': 11})
        self.assertEqual(len(alias), 2, "get_alias don't return the alias of the document and the default alias of the model")
        self.assertEqual(alias[0].get('id'), alias_id_1, "get_alias don't return the alias of the document")
        self.assertEqual(alias[1].get('id'), alias_id_0, "get_alias don't return the default alias of the model")