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


class ReportStockLotLabel(models.AbstractModel):
    _name = 'report.stock.report_lot_label'
    _inherit = 'report.product.label.base'
    _description = 'Lot Label Report'

    def _prepare_lot_label(self, lot):
        product = lot.product_id.with_context(display_default_code=False)
        return {
            'barcode': lot.name,
            'identifier_text': lot.name,
            'base_unit_name': '',
            'base_unit_price': 0,
            'product_code': lot.product_id.default_code or '',
            'currency_id': False,
            'extra_html': False,
            'invisible': False,
            'label_class': 'o_label_without_meta_block',
            'price': 0,
            'price_included': False,
            'title': product.display_name,
            'use_date': False,
            'expiration_date': False,
        }

    def _prepare_labels(self, lots, pricelist=None, extra_html=False, price_included=False):
        return [self._prepare_lot_label(lot) for lot in lots]

    def _prepare_data(self, docids, data):
        docs = self.env['stock.lot'].browse(docids)
        label_pages = self._organize_labels(self._prepare_labels(docs), rows=12, columns=4)
        return {
            'doc_ids': docids,
            'doc_model': 'stock.lot',
            'docs': docs,
            'label_pages': label_pages,
            'page_numbers': len(label_pages),
        }

    def _get_report_values(self, docids, data):
        return self._prepare_data(docids, data)
