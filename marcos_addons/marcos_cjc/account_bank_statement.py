# -*- coding: utf-8 -*-
from openerp.osv import fields, orm
from openerp import netsvc


class account_cash_statement(orm.Model):
    _inherit = "account.bank.statement"

    def journal_id_change(self, cr, uid, context=None, *args):
        context = context or {}
        is_cjc = self.pool.get("account.journal").browse(cr, uid, args[0], context=context).is_cjc
        return {"value": {"is_cjc": is_cjc}}

    _columns = {
        "is_cjc": fields.boolean("Control de caja chica", readonly=False)
    }

    def create_invoice_wizard(self, cr, uid, ids, context=None):
        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'marcos_cjc', 'cjc_wizard_view_form')[1]
        wizard = {
            'name': 'Gasto de caja chica',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view_id, 'form')],
            'view_type': 'form',
            'res_model': 'cjc.invoice.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
        return wizard

    def button_confirm_cash(self, cr, uid, ids, context=None):
        result = super(account_cash_statement, self).button_confirm_bank(cr, uid, ids, context=context)
        try:
            wf_service = netsvc.LocalService("workflow")
            invoiced = []
            uninvoiced = []
            for statement in self.browse(cr, uid, ids):
                for line in statement.line_ids:
                    if line.invoice_id:
                        invoiced.append(line.invoice_id.id)
                    elif line.amount < 0:
                        uninvoiced.append(line)

            # for inv_id in invoiced:
            #     wf_service.trg_validate(uid, 'account.invoice', inv_id, 'invoice_open', cr)

            statement = self.browse(cr, uid, ids)[0]
            journal = statement.journal_id
            minor_journal = journal.gastos_journal_id
            minor_partner = minor_journal.special_partner
            minor_product = minor_journal.special_product
            vals = {}
            vals.update({
                        u'account_id': journal.default_credit_account_id.id,
                        u'check_total': 0,
                        u'child_ids': [[6, False, []]],
                        u'comment': "Gasto menor generado por caja chica",
                        u'company_id': 1,
                        u'currency_id': journal.company_id.currency_id.id,
                        u'date_due': False,
                        u'date_invoice': statement.date,
                        u'fiscal_position': minor_partner.property_account_position.id,
                        u'internal_number': False,
                        u'journal_id': minor_journal.id,
                        u'message_follower_ids': False,
                        u'message_ids': False,
                        u'name': False,
                        u'ncf_required': False,
                        u'origin': statement.name,
                        u'parent_id': False,
                        u'partner_bank_id': False,
                        u'partner_id': minor_partner.id,
                        u'payment_term': False,
                        u'period_id': statement.period_id.id,
                        u'reference': False,
                        u'reference_type': "02",
                        u'supplier_invoice_number': False,
                        u'tax_line': [],
                        u'user_id': uid,
                        u'pay_to': statement.journal_id.pay_to.id,
                        u'invoice_line': []
                })
            if uninvoiced:
                line_ids = []
                for line in uninvoiced:
                    line_ids.append(line.id)
                    line_list = [0, False]
                    line_dict = {}
                    line_dict.update({
                            u'account_analytic_id': False,
                            u'account_id': minor_product.property_account_expense.id,
                            u'asset_category_id': False,
                            u'discount': 0,
                            u'invoice_line_tax_id': [[6, False, [t.id for t in minor_product.supplier_taxes_id]]],
                            u'name': line.name,
                            u'price_unit': abs(line.amount),
                            u'product_id': minor_product.id,
                            u'quantity': 1,
                            u'uos_id': 1
                    })
                    line_list.append(line_dict)
                    vals["invoice_line"].append(line_list)

                context.update({u'default_type': u'in_invoice', u'journal_type': u'purchase'})
                inv_id  = self.pool.get("account.invoice").create(cr, uid, vals, context=context)
                self.pool.get("account.bank.statement.line").write(cr, uid, line_ids, {"invoice_id": inv_id})
                wf_service.trg_validate(uid, 'account.invoice', inv_id, 'invoice_open', cr)
        except:
            pass

        return result





class account_bank_statement_line(orm.Model):
    _inherit = "account.bank.statement.line"

    _columns = {
        "invoice_id": fields.many2one("account.invoice", "Factura")
    }

    def unlink(self, cr, uid, ids, context=None):
        context = context or {}
        for line in self.browse(cr, uid, ids):
            if context.get("journal_type", False) == "cash" and line.invoice_id:
                self.pool.get("account.invoice").unlink(cr, uid, [line.invoice_id.id], context=context)

        return super(account_bank_statement_line, self).unlink(cr, uid, ids, context=context)
