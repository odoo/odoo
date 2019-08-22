# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    @api.model
    def _get_rule_domain(self, location, values):
        if 'sale_line_id' in values and values.get('company_id'):
            return [('location_id', '=', location.id), ('action', '!=', 'push'), ('company_id', '=', values['company_id'].id)]
        else:
            return super(ProcurementGroup, self)._get_rule_domain(location, values)
