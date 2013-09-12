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
        'use_mass_mailing_campaign': fields.boolean(
            'Use mass mailing campaigns',
        ),
        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass mailing campaign',
        ),
        'mass_mailing_segment_id': fields.many2one(
            'mail.mass_mailing.segment', 'Mass mailing segment',
            domain="[('mass_mailing_campaign_id', '=', mass_mailing_campaign_id)]",
        ),
    }

    _defaults = {
        'use_mass_mailing_campaign': False,
    }

    def onchange_mass_mail_campaign_id(self, cr, uid, ids, mass_mailing_campaign_id, mass_mail_segment_id, context=None):
        if mass_mail_segment_id:
            segment = self.pool['mail.mass_mailing.segment'].browse(cr, uid, mass_mail_segment_id, context=context)
            if segment.mass_mailing_campaign_id.id == mass_mailing_campaign_id:
                return {}
        return {'value': {'mass_mailing_segment_id': False}}

    def render_message_batch(self, cr, uid, wizard, res_ids, context=None):
        """ Override method that generated the mail content by adding the mass
        mailing campaign, when doing pure email mass mailing. """
        res = super(MailComposeMessage, self).render_message_batch(cr, uid, wizard, res_ids, context=context)
        if wizard.composition_mode == 'mass_mail' and wizard.use_mass_mailing_campaign and wizard.mass_mailing_segment_id:  # TODO: which kind of mass mailing ?
            for res_id in res_ids:
                res[res_id]['mass_mailing_segment_id'] = wizard.mass_mailing_segment_id.id
        return res
