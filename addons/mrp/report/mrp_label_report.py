from odoo import models


class ReportMrpLabelProductionPdf(models.AbstractModel):
    _name = 'report.mrp.label_production_view_pdf'
    _inherit = 'report.product.label.base'
    _description = 'MRP Finished Product Label Report'

    def _prepare_mrp_label(self, move_line, barcode, label_quantity):
        return {
            'barcode': barcode,
            'identifier_text': barcode or 'No barcode available',
            'base_unit_name': '',
            'base_unit_price': 0,
            'product_code': move_line.product_id.default_code or '',
            'currency_id': False,
            'extra_html': False,
            'invisible': False,
            'label_quantity': label_quantity,
            'label_class': 'o_label_without_meta_block',
            'price': 0,
            'price_included': False,
            'title': move_line.product_id.name,
            'uom_name': move_line.uom_id.display_name,
        }

    def _prepare_mrp_labels(self, docs, uom_unit):
        labels = []
        move_lines = docs.move_finished_ids.move_line_ids.filtered(
            lambda ml: ml.move_id.production_id.state == 'done' and ml.state == 'done' and ml.quantity
        )
        for move_line in move_lines:
            is_unit = move_line.product_id.uom_id._has_common_reference(uom_unit)
            label_quantity = 1 if is_unit else move_line.quantity
            barcode = (
                (move_line.lot_name or move_line.lot_id.name)
                if move_line.product_id.tracking in ['lot', 'serial'] and (move_line.lot_name or move_line.lot_id)
                else move_line.product_id.barcode
                if not move_line.product_id.tracking and move_line.product_id.barcode
                else False
            )
            for _index in range(int(move_line.quantity) if is_unit else 1):
                labels.append(self._prepare_mrp_label(move_line, barcode, label_quantity))
        return labels

    def _prepare_data(self, docids, data):
        docs = self.env['mrp.production'].browse(docids)
        uom_unit = self.env.ref('uom.product_uom_unit')
        label_pages = self._organize_labels(self._prepare_mrp_labels(docs, uom_unit), rows=12, columns=4)
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': docs,
            'label_pages': label_pages,
            'page_numbers': len(label_pages),
        }

    def _get_report_values(self, docids, data):
        return self._prepare_data(docids, data)
