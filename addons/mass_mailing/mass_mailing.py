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


class MassMailingCampaign(osv.Model):
    """Model of mass mailing campaigns.
    """
    _name = "mail.mass_mailing.campaign"
    _description = 'Mass Mailing Campaign'

    def _get_statistics(self, cr, uid, ids, name, arg, context=None):
        """ Compute statistics of the mass mailing campaign """
        results = dict.fromkeys(ids, False)
        for campaign in self.browse(cr, uid, ids, context=context):
            if not campaign.mail_ids:
                results[campaign.id] = {
                    'sent': 0,
                    'opened_ratio': 0.0,
                    'replied_ratio': 0.0,
                    'bounce_ratio': 0.0,
                }
                continue
            results[campaign.id] = {
                'sent': len(campaign.mail_ids),
                'opened_ratio': len([mail for mail in campaign.mail_ids if mail.opened]) * 1.0 / len(campaign.mail_ids),
                'replied_ratio': len([mail for mail in campaign.mail_ids if mail.replied]) * 1.0 / len(campaign.mail_ids),
                'bounce_ratio': 0.0,
            }
        return results

    _columns = {
        'name': fields.char(
            'Campaign Name', required=True,
        ),
        'template_id': fields.many2one(
            'email.template', 'Email Template',
            ondelete='set null',
        ),
        'mail_ids': fields.one2many(
            'mail.mail', 'mass_mailing_campaign_id',
            'Send Emails',
        ),
        # stat fields
        'sent': fields.function(
            _get_statistics,
            string='Sent Emails',
            type='integer', multi='_get_statistics'
        ),
        'opened_ratio': fields.function(
            _get_statistics,
            string='Opened Ratio',
            type='float', multi='_get_statistics',
        ),
        'replied_ratio': fields.function(
            _get_statistics,
            string='Replied Ratio',
            type='float', multi='_get_statistics'
        ),
        'bounce_ratio': fields.function(
            _get_statistics,
            string='Bounce Ratio',
            type='float', multi='_get_statistics'
        ),
    }
