# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HmrcSendWizard(models.TransientModel):
    _name = 'l10n_uk.hmrc.send.wizard'
    _description = "HMRC Send Wizard"

    @api.model
    def default_get(self, fields_list):
        res = super(HmrcSendWizard, self).default_get(fields_list)
        if 'client_data' not in self.env.context:
            return res

        # Check obligations: should be logged in by now
        self.env['l10n_uk.vat.obligation'].import_vat_obligations(self.env.context['client_data'])

        if 'obligation_id' in fields_list:
            obligations = self.env['l10n_uk.vat.obligation'].search([('status', '=', 'open')])
            if not obligations:
                raise UserError(_('You have no open obligations anymore'))

            date_from = fields.Date.from_string(self.env.context['options']['date']['date_from'])
            date_to = fields.Date.from_string(self.env.context['options']['date']['date_to'])
            for obl in obligations:
                if obl.date_start == date_from and obl.date_end == date_to:
                    res['obligation_id'] = obl.id
                    break
        
        if 'hmrc_gov_client_device_id' in fields_list:
            res['hmrc_gov_client_device_id'] = self.env.context['client_data']['hmrc_gov_client_device_id']
        
        if 'message' in fields_list:
            res['message'] = not res.get('obligation_id')
        return res

    obligation_id = fields.Many2one('l10n_uk.vat.obligation', 'Obligation', domain=[('status', '=', 'open')], required=True)
    message = fields.Boolean('Message', readonly=True) # Show message if no obligation corresponds to report options
    accept_legal = fields.Boolean('Accept Legal Statement') # A checkbox to warn the user that what he sends is legally binding
    hmrc_gov_client_device_id = fields.Char(default=lambda x: uuid.uuid4())
