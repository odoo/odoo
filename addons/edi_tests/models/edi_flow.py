# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class EdiFlow(models.Model):
    _inherit = 'edi.flow'

    @api.model
    def _abandon_cancel_flow_conditions(self, document):
        if document._name != 'res.partner':
            return super()._abandon_cancel_flow_conditions(document)
        return self.edi_format_id._is_format_required(document, document._name)
