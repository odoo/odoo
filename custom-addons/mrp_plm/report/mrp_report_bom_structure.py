# -*- coding: utf-8 -*-

from odoo import models


class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _get_pdf_doc(self, bom_id, data, quantity, product_variant_id=None):
        doc = super()._get_pdf_doc(bom_id, data, quantity, product_variant_id)
        doc['show_ecos'] = True if data and data.get('show_ecos') == 'true' and self.env.user.user_has_groups('mrp_plm.group_plm_user') else False
        return doc

    def _get_report_data(self, bom_id, searchQty=0, searchVariant=False):
        res = super()._get_report_data(bom_id, searchQty, searchVariant)
        res['is_eco_applied'] = self.env.user.user_has_groups('mrp_plm.group_plm_user')
        return res

    def _get_bom_data(self, bom, warehouse, product=False, line_qty=False, bom_line=False, level=0, parent_bom=False, parent_product=False, index=0, product_info=False, ignore_stock=False):
        res = super()._get_bom_data(bom, warehouse, product, line_qty, bom_line, level, parent_bom, parent_product, index, product_info, ignore_stock)
        if self.env.user.user_has_groups('mrp_plm.group_plm_user'):
            res['version'] = res['bom'] and res['bom'].version or ''
            product_tmpl_id = (res['product'] and res['product'].product_tmpl_id.id) or (res['bom'] and res['product'].product_tmpl_id.id)
            res['ecos'] = self.env['mrp.eco'].search_count([('product_tmpl_id', '=', product_tmpl_id), ('state', '!=', 'done')]) or ''
        return res

    def _get_component_data(self, parent_bom, parent_product, warehouse, bom_line, line_quantity, level, index, product_info, ignore_stock=False):
        res = super()._get_component_data(parent_bom, parent_product, warehouse, bom_line, line_quantity, level, index, product_info, ignore_stock)
        if self.env.user.user_has_groups('mrp_plm.group_plm_user'):
            res['version'] = False
            res['ecos'] = self.env['mrp.eco'].search_count([('product_tmpl_id', '=', res['product'].product_tmpl_id.id), ('state', '!=', 'done')]) or ''
        return res

    def _get_bom_array_lines(self, data, level, unfolded_ids, unfolded, parent_unfolded):
        lines = super()._get_bom_array_lines(data, level, unfolded_ids, unfolded, parent_unfolded)
        if not self.env.user.user_has_groups('mrp_plm.group_plm_user'):
            return lines
        for component in data.get('components', []):
            if not component['bom_id']:
                continue
            bom_line = next(filter(lambda l: l.get('bom_id', None) == component['bom_id'], lines))
            if bom_line:
                bom_line['version'] = component['version']
                bom_line['ecos'] = component['ecos']

        return lines
