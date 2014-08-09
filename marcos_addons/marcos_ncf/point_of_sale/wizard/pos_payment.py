# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp import netsvc


class pos_make_payment(osv.Model):
    _inherit = "pos.make.payment"

    def _journal_ids_shop(self, cr, uid, context=None):
        context = context or {}
        session_id = context.get("pos_session_id", False)
        journal_ids_list = []
        if session_id:

            journal_ids =  self.pool.get("pos.session").browse(cr, uid, session_id, context=context).config_id.journal_ids
            for journal in journal_ids:
                journal_ids_list.append((journal.id, journal.name))

        return journal_ids_list

    _columns = {
        'journal_id': fields.selection(_journal_ids_shop, u"Método de pago")
    }


    def action_print_pos_order(self, cr, uid, ids, context=None):
        """
        Print pos_order on fiscal printer.

        """

        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'marcos_ncf', 'marcos_view_confirm_print_fiscal_invoice')[1]
        wizard = {
            'name': u'Confirmar Impresión',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view_id, 'form')],
            'view_type': 'form',
            'res_model': 'pos.print.fiscal.invoice',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
        return wizard

    def action_print_customer_receipt(self, cr, uid, ids, context=None):
        """
        Print customer payment receipt.

        """

        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'marcos_ncf', 'marcos_view_confirm_print_customer_receipt')[1]
        wizard = {
            'name': u'Confirmar Impresión',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view_id, 'form')],
            'view_type': 'form',
            'res_model': 'pos.print.customer.receipt',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
        return wizard

    def fix_payment(self, cr, uid, ids, context=None):
        for amount in self.read(cr, uid, ids, ["amount"]):
            if amount["amount"] == 0.00:
                raise osv.except_osv(u'Monto invalido!', u'No puede hacer un pago en 0.00!')

        context = context or {}
        if self.pool.get("pos.session").read(cr, uid, context.get("pos_session_id", []), ['state'])["state"] == "closed":
            raise osv.except_osv(u'Session cerrada!', u'La session con la que fue cobrado este documento fue cerrada no se puede cambiar la foma de pago!')

        order_obj = self.pool.get('pos.order')
        active_id = context and context.get('active_id', False)

        order = order_obj.browse(cr, uid, active_id, context=context)
        if not context.get("fix_start", False):
            st_obj = self.pool.get("account.bank.statement.line")
            st_obj.unlink(cr, uid, [st.id for st in order.statement_ids])
            order.statement_ids = []
            context.update({"fix_start": True})

        amount = order.amount_total - order.amount_paid
        data = self.read(cr, uid, ids, context=context)[0]
        # this is probably a problem of osv_memory as it's not compatible with normal OSV's
        data['journal'] = int(data['journal_id'])

        if amount != 0.0:
            order_obj.add_payment(cr, uid, active_id, data, context=context)

        if order_obj.test_paid(cr, uid, [active_id]):
            return {'type': 'ir.actions.act_window_close'}

        return self.launch_payment(cr, uid, ids, context=context)

    def check(self, cr, uid, ids, context=None):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        if context.get("fix_payment", False):
            return self.fix_payment(cr, uid, ids, context=context)

        context = context or {}
        order_obj = self.pool.get('pos.order')
        active_id = context and context.get('active_id', False)

        order = order_obj.browse(cr, uid, active_id, context=context)
        amount = order.amount_total - order.amount_paid
        data = self.read(cr, uid, ids, context=context)[0]

        if order.parent_return_order:
            refund_order_name = order_obj.browse(cr, uid, int(order.parent_return_order), context=context).name
            try:
                inv_obj = self.pool.get('account.invoice')
                refund_inv_ids = inv_obj.search(cr, uid, [("name", "=", refund_order_name)])[0]
            except Exception:
                raise osv.except_osv(u'Factura sin cobrar!', u'No puede devolver dinero sin haber cobrado la factura de origen!')
            context["refund_inv_ids"] = refund_inv_ids

        data['journal'] = int(data['journal_id'])

        if amount != 0.0:
            order_obj.add_payment(cr, uid, active_id, data, context=context)

        if order_obj.test_paid(cr, uid, [active_id]):
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'pos.order', active_id, 'paid', cr)

            # If pos.order is receipt, don't create invoice or show printing popup.
            if order.type == 'receipt':
                account_voucher_obj = self.pool.get("account.voucher")
                if not account_voucher_obj.read(cr, uid, int(order.pos_reference), ['state'])['state'] == "posted":
                    result = account_voucher_obj.proforma_voucher(cr, uid, [int(order.pos_reference)])
                account_voucher_obj.write(cr, uid, [int(order.pos_reference)], {"reference": order.name}, context=context)
                voucher_obj = account_voucher_obj.read(cr, uid, int(order.pos_reference), ['number', 'id'])
                number = voucher_obj['number']
                order_obj.write(cr, uid, active_id, {"pos_reference": number}, context=context)
                context['voucher_id'] = voucher_obj['id']
                return self.action_print_customer_receipt(cr, uid, ids, context=context)

            invoice = self.pool.get('pos.order').action_create_invoice(cr, uid, [order.id], context=context)
            # stop the lag on close box, assing the move_id to the pos_order after create invoice
            order_obj.account_move = self.pool.get("account.invoice").read(cr, uid, invoice[0], ["move_id"])["move_id"][0]
            return self.action_print_pos_order(cr, uid, ids, context=context)
            # self.print_report(cr, uid, ids, context=context)

        return self.launch_payment(cr, uid, ids, context=context)


class pos_print_fiscal_invoice(osv.osv_memory):
    _name = "pos.print.fiscal.invoice"

    def _default_name(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('pos.order')
        order = order_obj.browse(cr, uid, ids.get('active_id'), context=context)
        return order.name

    _columns = {
            'name': fields.char('Nombre', readonly=True),
            }

    _defaults = {
            'name': _default_name
            }


class pos_print_customer_receipt(osv.osv_memory):
    _name = "pos.print.customer.receipt"

    def print_customer_receipt(self, cr, uid, ids, context=None):
        voucher_obj = self.pool.get("account.voucher").browse(cr, uid, context['voucher_id'], context=context)
        return voucher_obj.print_receipt()
