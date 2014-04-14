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

from openerp import tools
from openerp.osv import osv, fields


class MailComposeMessage(osv.TransientModel):
    """Add concept of mass mailing campaign to the mail.compose.message wizard
    """
    _inherit = 'mail.compose.message'

    _columns = {
        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass Mailing Campaign',
        ),
        'mass_mailing_id': fields.many2one(
            'mail.mass_mailing', 'Mass Mailing'
        ),
        'mass_mailing_name': fields.char('Mass Mailing'),
        'mailing_list_ids': fields.many2many(
            'mail.mass_mailing.list', string='Mailing List'
        ),
    }

    def get_mail_values(self, cr, uid, wizard, res_ids, context=None):
        """ Override method that generated the mail content by creating the
        mail.mail.statistics values in the o2m of mail_mail, when doing pure
        email mass mailing. """
        res = super(MailComposeMessage, self).get_mail_values(cr, uid, wizard, res_ids, context=context)
        # use only for allowed models in mass mailing
        if wizard.composition_mode == 'mass_mail' and \
                (wizard.mass_mailing_name or wizard.mass_mailing_id) and \
                wizard.model in [item[0] for item in self.pool['mail.mass_mailing']._get_mailing_model(cr, uid, context=context)]:
            # list_ids = None
            # if wizard.mailing_list_ids:
            #     list_ids = [l.id for l in wizard.mailing_list_ids]
            # if not list_ids:
            #     list_ids = [self.pool['mail.mass_mailing.list'].create(
            #         cr, uid, {
            #             'name': wizard.mass_mailing_name,
            #             'model': wizard.model,
            #             'domain': wizard.active_domain,
            #         }, context=context)]
            mass_mailing = wizard.mass_mailing_id
            if not mass_mailing:
                mass_mailing_id = self.pool['mail.mass_mailing'].create(
                    cr, uid, {
                        'mass_mailing_campaign_id': wizard.mass_mailing_campaign_id and wizard.mass_mailing_campaign_id.id or False,
                        'name': wizard.mass_mailing_name,
                        'template_id': wizard.template_id and wizard.template_id.id or False,
                        'state': 'done',
                        'mailing_type': wizard.model,
                        # 'contact_list_ids': [(4, list_id) for list_id in list_ids],
                    }, context=context)
                mass_mailing = self.pool['mail.mass_mailing'].browse(cr, uid, mass_mailing_id, context=context)
            recipient_values = self.pool['mail.mass_mailing'].get_recipients_data(cr, uid, mass_mailing, res_ids, context=context)
            for res_id in res_ids:
                mail_values = res[res_id]
                recipient = recipient_values[res_id]
                unsubscribe_url = self.pool['mail.mass_mailing'].get_unsubscribe_url(cr, uid, mass_mailing.id, res_id, recipient['email'], context=context)
                if unsubscribe_url:
                    mail_values['body_html'] = tools.append_content_to_html(mail_values['body_html'], unsubscribe_url, plaintext=False, container_tag='p')
                mail_values.update({
                    'email_to': '"%s" <%s>' % (recipient['name'], recipient['email'])
                })
                recipient = recipient_values[res_id]
                res[res_id]['statistics_ids'] = [(0, 0, {
                    'model': wizard.model,
                    'res_id': res_id,
                    'mass_mailing_id': mass_mailing.id,
                })]
        return res
