# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import osv, fields


class MailComposeMessage(osv.TransientModel):
    """Add concept of mass mailing campaign to the mail.compose.message wizard
    """
    _inherit = 'mail.compose.message'

    _columns = {
        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass mailing campaign',
        ),
        'mass_mailing_name': fields.char('Mass Mailing'),
    }

    def get_mail_values(self, cr, uid, wizard, res_ids, context=None):
        """ Override method that generated the mail content by creating the
        mail.mail.statistics values in the o2m of mail_mail, when doing pure
        email mass mailing. """
        res = super(MailComposeMessage, self).get_mail_values(cr, uid, wizard, res_ids, context=context)
        # use only for allowed models in mass mailing
        if wizard.composition_mode == 'mass_mail' and wizard.mass_mailing_name and \
                wizard.model in [item[0] for item in self.pool['mail.mass_mailing']._get_mailing_model()]:
            list_id = self.pool['mail.mass_mailing.list'].create(
                cr, uid, {
                    'name': wizard.mass_mailing_name,
                    'model': wizard.model,
                    'domain': wizard.active_domain,
                }, context=context)
            mass_mailing_id = self.pool['mail.mass_mailing'].create(
                cr, uid, {
                    'mass_mailing_campaign_id': wizard.mass_mailing_campaign_id and wizard.mass_mailing_campaign_id.id or False,
                    'name': wizard.mass_mailing_name,
                    'template_id': wizard.template_id and wizard.template_id.id or False,
                    'state': 'done',
                    'mailing_type': wizard.model,
                    'contact_list_ids': [(4, list_id)],
                }, context=context)
            for res_id in res_ids:
                res[res_id]['statistics_ids'] = [(0, 0, {
                    'model': wizard.model,
                    'res_id': res_id,
                    'mass_mailing_id': mass_mailing_id,
                })]
        return res
