# -*- encoding: utf-8 -*-

from openerp.osv import fields
from openerp.osv import orm


class account_invoice(orm.Model):
    _inherit = 'account.invoice'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.refund',
            'openerp_id',
            string="Prestashop Bindings"
        ),
    }

    def action_move_create(self, cr, uid, ids, context=None):
        so_obj = self.pool.get('prestashop.sale.order')
        line_replacement = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            so_ids = so_obj.search(cr, uid, [('name', '=', invoice.origin)])
            if not so_ids:
                continue
            sale_order = so_obj.browse(cr, uid, so_ids[0])
            discount_product_id = sale_order.backend_id.discount_product_id.id

            for invoice_line in invoice.invoice_line:
                if invoice_line.product_id.id != discount_product_id:
                    continue
                amount = invoice_line.price_subtotal
                if invoice.partner_id.parent_id:
                    partner_id = invoice.partner_id.parent_id.id
                else:
                    invoice.partner_id.id
                refund_id = self._find_refund(
                    cr, uid, -1 * amount, partner_id,
                    context=context)
                if refund_id:
                    self.pool.get('account.invoice.line').unlink(
                        cr, uid, invoice_line.id)
                    line_replacement[invoice.id] = refund_id
                    self.button_reset_taxes(cr, uid, [invoice.id],
                                            context=context)

        result = super(account_invoice, self).action_move_create(
            cr, uid, ids, context=None
        )
        # reconcile invoice with refund
        for invoice_id, refund_id in line_replacement.items():
            self._reconcile_invoice_refund(
                cr, uid, invoice_id, refund_id, context=context
            )
        return result

    def _reconcile_invoice_refund(self, cr, uid, invoice_id, refund_id,
                                  context=None):
        move_line_obj = self.pool.get('account.move.line')
        invoice_obj = self.pool.get('account.invoice')

        invoice = invoice_obj.browse(cr, uid, invoice_id, context=context)
        refund = invoice_obj.browse(cr, uid, refund_id, context=context)

        move_line_ids = move_line_obj.search(cr, uid, [
            ('move_id', '=', invoice.move_id.id),
            ('debit', '!=', 0.0),
        ], context=context)
        move_line_ids += move_line_obj.search(cr, uid, [
            ('move_id', '=', refund.move_id.id),
            ('credit', '!=', 0.0),
        ], context=context)
        move_line_obj.reconcile_partial(
            cr, uid, move_line_ids, context=context
        )

    def _find_refund(self, cr, uid, amount, partner_id, context=None):
        ids = self.search(cr, uid, [
            ('amount_untaxed', '=', amount),
            ('type', '=', 'out_refund'),
            ('state', '=', 'open'),
            ('partner_id', '=', partner_id),
        ])
        if not ids:
            return None
        return ids[0]


class prestashop_refund(orm.Model):
    _name = 'prestashop.refund'
    _inherit = 'prestashop.binding'
    _inherits = {'account.invoice': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'account.invoice',
            string='Invoice',
            required=True,
            ondelete='cascade',
        ),
    }
