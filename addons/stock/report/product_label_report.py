import markupsafe

from odoo import models


class ReportStockLabel_Lot_Template_View(models.AbstractModel):
    _name = 'report.stock.label_lot_template_view'
    _description = 'Lot Label Report'

    def _get_report_values(self, docids, data):
        lots = self.env['stock.lot'].browse(docids)
        lot_list = []
        for lot in lots:
            lot_list.append({
                'display_name_markup': markupsafe.Markup(lot.product_id.display_name),
                'name': markupsafe.Markup(lot.name),
                'lot_record': lot
            })
        return {
            'docs': lot_list,
        }
