# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext


class EwaybillExtendValidity(models.TransientModel):
    """
    Extend Validity of the ewaybill
    """
    _name = 'ewaybill.update.transporter'
    _description = 'Update Transporter'

    ewaybill_id = fields.Many2one("l10n.in.ewaybill")
    transporter_id = fields.Many2one("res.partner", "Transporter", required=True, compute="_compute_wizard_values", store=True, readonly=False)

    @api.depends('ewaybill_id')
    def _compute_wizard_values(self):
        self.transporter_id = self.ewaybill_id.transporter_id

    def update_transporter(self):
        update_values = {
            'transporter_id': self.transporter_id.id,
        }
        res = self.ewaybill_id._l10n_in_ewaybill_update_transporter(self.ewaybill_id, update_values)
        if res.get(self.ewaybill_id).get('success') is True:
            self.ewaybill_id.write({
            'transporter_id': self.transporter_id.id,
            })
            self.ewaybill_id.message_post(body=_("Transporter of the Ewaybill has been updated to %s .") % (self.transporter_id.name))
        else:
            raise ValidationError(_("\nEwaybill Transporter not updated \n\n%s") % (html2plaintext(res.get(self.ewaybill_id).get("error", False))))
