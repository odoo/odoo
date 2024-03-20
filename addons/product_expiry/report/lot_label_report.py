# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

import markupsafe

class ReportLotLabelInherit(models.AbstractModel):
    _inherit = 'report.stock.label_lot_template_view'

    def _get_report_values(self, docids, data):
        lots = super(ReportLotLabelInherit, self)._get_report_values(docids, data)

        for lot in lots.get('docs', []):
            lot_id = self.env['stock.production.lot'].browse(lot['lot_id'])

            lot.update({
                'use_expiration_date': markupsafe.Markup(lot_id.use_expiration_date),
                'use_date': markupsafe.Markup(lot_id.use_date),
                'expiration_date': markupsafe.Markup(lot_id.expiration_date),
            })

        return lots
