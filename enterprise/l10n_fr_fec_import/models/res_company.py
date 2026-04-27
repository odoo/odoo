# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def fec_import_action(self):
        """ This action is triggered when the Configuration > FEC Import menu button is pressed."""
        return self.env['ir.actions.act_window']._for_xml_id("l10n_fr_fec_import.import_action")
