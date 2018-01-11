# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://www.openerp.com>
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

from openerp.addons.base.tests.test_ir_actions import TestServerActionsBase


class TestServerActionsEmail(TestServerActionsBase):

    def test_00_state_email(self):
        """ Test ir.actions.server email type """
        cr, uid = self.cr, self.uid

        # create email_template
        template_id = self.registry('email.template').create(cr, uid, {
            'name': 'TestTemplate',
            'email_from': 'myself@example.com',
            'email_to': 'brigitte@example.com',
            'partner_to': '%s' % self.test_partner_id,
            'model_id': self.res_partner_model_id,
            'subject': 'About ${object.name}',
            'body_html': '<p>Dear ${object.name}, your parent is ${object.parent_id and object.parent_id.name or "False"}</p>',
        })

        self.ir_actions_server.write(cr, uid, self.act_id, {
            'state': 'email',
            'template_id': template_id,
        })
        run_res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)
        self.assertFalse(run_res, 'ir_actions_server: email server action correctly finished should return False')

        # check an email is waiting for sending
        mail_ids = self.registry('mail.mail').search(cr, uid, [('subject', '=', 'About TestingPartner')])
        self.assertEqual(len(mail_ids), 1, 'ir_actions_server: TODO')
        # check email content
        mail = self.registry('mail.mail').browse(cr, uid, mail_ids[0])
        self.assertEqual(mail.body, '<p>Dear TestingPartner, your parent is False</p>',
                         'ir_actions_server: TODO')
