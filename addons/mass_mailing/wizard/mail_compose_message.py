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
        'mass_mail_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass mailing campaign'
        ),
    }

    def onchange_mass_mail_campaign_id(self, cr, uid, ids, mass_mail_campaign_id, context=None):
        values = {}
        if mass_mail_campaign_id:
            campaign = self.pool['mail.mass_mailing.campaign'].browse(cr, uid, mass_mail_campaign_id, context=context)
            if campaign and campaign.template_id:
                values['template_id'] = campaign.template_id.id
        return {'value': values}

    def render_message(self, cr, uid, wizard, res_id, context=None):
        """ Override method that generated the mail content by adding the mass
        mailing campaign, when doing pure email mass mailing. """
        res = super(MailComposeMessage, self).render_message(cr, uid, wizard, res_id, context=context)
        print res, wizard.mass_mail_campaign_id
        if wizard.composition_mode == 'mass_mail' and wizard.mass_mail_campaign_id:  # TODO: which kind of mass mailing ?
            res['mass_mailing_campaign_id'] = wizard.mass_mail_campaign_id.id
        return res
