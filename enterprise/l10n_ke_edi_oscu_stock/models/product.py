# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import json_float_round


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_l10n_ke_oscu_save_stock_master(self):
        if self.product_variant_count != 1:
            raise UserError(_("This product has multiple variants. You need to do it for each variant separately."))
        return self.product_variant_ids.action_l10n_ke_oscu_save_stock_master()

    def _compute_invoice_policy(self):
        """ Set invoicing policy to on delivery for Kenyan products"""
        kenyan_products = self.filtered(lambda t: t.is_storable and
                                                  (not t.company_id or t.company_id.account_fiscal_country_id.code == 'KE'))
        kenyan_products.invoice_policy = 'delivery'
        super(ProductTemplate, self - kenyan_products)._compute_invoice_policy()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _l10n_ke_oscu_save_stock_master_content(self):
        """ Send the current available stock quantity to eTIMS.
            We explicitly compensate any stock moves that were not yet reported to eTIMS, to ensure that the
            reported stock IO and stock master are consistent one with the other.

        :param qty_to_add float: Quantity to be added to the current available stock quantity, e.g. if some stock moves that affect
                                 the current available quantity correspond to invoices that have not yet been sent, and therefore
                                 must not be taken into account for the purposes of reporting to KRA.
        """
        self.ensure_one()

        # Determine moves that were not yet sent to eTIMS.
        whs = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])

        # We must manually add these domains as this method may be called in a cron, with self.env.company set,
        # but as superuser, which causes issues when using product.read_group()
        _domain_quant_loc, domain_move_in_loc, domain_move_out_loc = (
            self.env['product.product'].with_context(warehouse=whs.ids)._get_domain_locations()
        )

        domain = [
            ('product_id', '=', self.id),
            ('state', '=', 'done'),
            ('l10n_ke_oscu_flow_type_code', '!=', False),
            ('l10n_ke_oscu_sar_number', '=', False),
            ('company_id', '=', self.env.company.id),
        ]
        # This param is set when l10n_ke_edi_oscu_stock is installed, and ensures that old moves are not sent.
        if from_date := self.env['ir.config_parameter'].sudo().get_param('l10n_ke.start_stock_date'):
            domain += [('date', '>=', from_date)]

        domain_move_in = domain + domain_move_in_loc
        domain_move_out = domain + domain_move_out_loc

        moves_in_qty = sum(
            product_uom._compute_quantity(qty, self.uom_id, round=False)
            for product_uom, qty in self.env['stock.move']._read_group(domain_move_in, ['product_uom'], ['quantity:sum'])
        )

        moves_out_qty = sum(
            product_uom._compute_quantity(qty, self.uom_id, round=False)
            for product_uom, qty in self.env['stock.move']._read_group(domain_move_out, ['product_uom'], ['quantity:sum'])
        )

        correction_qty = -moves_in_qty + moves_out_qty
        report_qty = self.with_context(warehouse=whs.ids).qty_available + correction_qty

        content = {
            'itemCd':      self.l10n_ke_item_code,
            'rsdQty':      json_float_round(report_qty, 2),
            **self.env.company._l10n_ke_get_user_dict(self.create_uid, self.write_uid),
        }
        return content

    def _l10n_ke_oscu_save_stock_master(self):
        self.ensure_one()
        content = self._l10n_ke_oscu_save_stock_master_content()
        error, _dummy, _dummy = self.env.company._l10n_ke_call_etims('saveStockMaster', content)
        return error, content

    def action_l10n_ke_oscu_save_stock_master(self):
        for product in self:
            error, _content = product._l10n_ke_oscu_save_stock_master()
            if error:
                raise UserError(error['message'])
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("Stock master successfully reported"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
