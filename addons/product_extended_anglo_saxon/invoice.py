from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp.tools.float_utils import float_round


class account_invoice_line(osv.Model):
    _inherit = "account.invoice.line"


    def _invoiced_product_move_lines(self, cr, uid, inv, i_line, dacc, cacc, context=None):
        """
        anglo-saxon accounting generates stock accounting entries for COGS
        In case of product based on phantom BoM, do not generate accounting
        entries based on the final product but on the components (as the final
        product is not in stock).
        """
        def _get_product_price(cr, uid, inv, bom_line, product, context=None):
            price_unit = sub_product.standard_price
            company_currency = inv.company_id.currency_id.id
            decimal_precision = self.pool['decimal.precision']
            cur_obj = self.pool['res.currency']
            if inv.currency_id.id != company_currency:
                price = cur_obj.compute(cr, uid, company_currency, inv.currency_id.id, price_unit * line['product_qty'], context={'date': inv.date_invoice})
            else:
                price = price_unit * bom_line['product_qty']
            return float_round(price, decimal_precision.precision_get(cr, uid, 'Account'))

        bom_obj = self.pool['mrp.bom']
        uom_obj = self.pool['product.uom']
        product_obj = self.pool['product.product']
        product = i_line.product_id
        bom_ids = self.pool['stock.move']._check_product_phantom_bom(cr, uid, product, context=context)
        if not bom_ids:
            return super(account_invoice_line, self)._invoiced_product_move_lines(cr, uid, inv, i_line, dacc, cacc, context=context)

        # product is based on phantom bom, meaning it is not actually moved
        # instead of invoicing phantom product, use raw material for COGS
        bom_point = bom_obj.browse(cr, SUPERUSER_ID, bom_ids[0], context=context)
        factor = uom_obj._compute_qty(cr, SUPERUSER_ID, i_line.uos_id.id, i_line.quantity, bom_point.product_uom.id) / bom_point.product_qty
        res = bom_obj._bom_explode(cr, SUPERUSER_ID, bom_point, product, factor, [], context=context)
        
        generated_move_lines = []
        for line in res[0]:
            sub_product = product_obj.browse(cr, uid, line['product_id'], context=context)
            generated_move_lines.append({
                'type': 'src',
                'name': line['name'],
                'price_unit': sub_product.standard_price,
                'quantity': line['product_qty'],
                'price': _get_product_price(cr, uid, inv, line, product, context=context),
                'account_id': dacc,
                'product_id': line['product_id'],
                'uos_id': line['product_uom'],
                'account_analytic_id': False,
                'taxes': i_line.invoice_line_tax_id,
            })
            generated_move_lines.append({
                'type': 'src',
                'name': line['name'],
                'price_unit': sub_product.standard_price,
                'quantity': line['product_qty'],
                'price': -1 * _get_product_price(cr, uid, inv, line, product, context=context),
                'account_id': cacc,
                'product_id': line['product_id'],
                'uos_id': line['product_uom'],
                'account_analytic_id': False,
                'taxes': i_line.invoice_line_tax_id,
            })

        return generated_move_lines
