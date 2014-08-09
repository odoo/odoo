# -*- coding: utf-8 -*-
from marcos_ncf.idvalidator import is_ncf
from openerp.osv import fields, orm
import openerp.addons.decimal_precision as dp
from openerp import netsvc


class cjc_invoice_wizard(orm.TransientModel):
    _name = "cjc.invoice.wizard"

    def _get_reference_type(self, cr, uid, context=None):
        return [('none', u'Referencia libre / Nº Fact. Proveedor'),
                ('01', '01 - Gastos de personal'),
                ('02', '02 - Gastos por trabajo, suministros y servicios'),
                ('03', '03 - Arrendamientos'),
                ('04', '04 - Gastos de Activos Fijos'),
                ('05', u'05 - Gastos de Representación'),
                ('06', '06 - Otras Deducciones Admitidas'),
                ('07', '07 - Gastos Financieros'),
                ('08', '08 - Gastos Extraordinarios'),
                ('09', '09 - Compras y Gastos que forman parte del Costo de Venta'),
                ('10', '10 - Adquisiciones de Activos'),
                ('11', '11 - Gastos de Seguro')
        ]

    def _get_journals(self, cr, uid, context=None):
        if context.get("active_model", False):
            active_model = self.pool.get("account.bank.statement").browse(cr, uid, context["active_id"])
            informal_journal = active_model.journal_id.informal_journal_id
            gastos_journal_id = active_model.journal_id.gastos_journal_id
            purchase_journal_id = active_model.journal_id.purchase_journal_id
            res = []
            res.append((informal_journal.id, informal_journal.name))
            res.append((gastos_journal_id.id, gastos_journal_id.name))
            res.append((purchase_journal_id.id, purchase_journal_id.name))
            if len(res) != 3:
                raise orm.except_orm('Configuracion pendiente!', "Se deben configurar los diarios para este tipo de docuemnto.")
            return tuple(res)

    def onchenge_journal(self, cr, uid, ids, journal_id, context=None):
        if journal_id:
            journal = self.pool.get("account.journal").browse(cr, uid, journal_id)

            vals = {"value": {"ncf_requierd": True, "ncf_minor": False}}
            if journal.ncf_special in ['gasto','informal']:
                vals["value"].update({"ncf_requierd": False})
                if journal.special_partner:
                    vals["value"].update({"ncf_minor": True, "partner_id": journal.special_partner.id})
            vals["value"].update({"journal_id": int(journal_id)})
            return vals


    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=False),
        "partner_id": fields.many2one("res.partner", "Proveedor", required=True, domain=[('supplier','=', True)]),
        "reference_type": fields.selection(_get_reference_type, "Tipo de comprobante", required=True),
        "date": fields.date("Fecha", required=True),
        "concept": fields.char("Concepto", required=True),
        "ncf": fields.char("NCF", size=19),
        "journal_id": fields.many2one("account.journal", "Diario de compra", domain=[('ncf_special', 'in', ('gasto', 'informal', 'pruchase'))], required=True),
        "line_ids": fields.one2many("cjc.invoice.line.wizard", "invoice_id", "Productos", select=False, required=True, ondelete='cascade'),
        "ncf_requierd": fields.boolean("NCF Requerido."),
        "ncf_minor": fields.boolean()
    }

    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'cjc.invoice.wizard', context=c),
        'ncf_requierd': False,
        "ncf_minor": False
    }

    def _parse_vals(self, cr, uid, ids, current_model, wizard_model, context=None):
        context = context or {}
        vals = {}
        for inv in wizard_model:
            journal_obj = self.pool.get("account.journal").browse(cr, uid, int(inv.journal_id))

            if not journal_obj.default_credit_account_id.id:
                raise orm.except_orm('Configuracion pendiente!', "Se deben configurar las cuentas para este diario.")
            elif not inv.line_ids:
                raise orm.except_orm('Registro sin productos!', "Debe de registrar por lo menos un producto.")

            ncf_required = True
            if journal_obj.ncf_special in ['gasto', 'informal']:
                ncf_required = False
            if ncf_required and not is_ncf(inv.ncf.encode("ascii")):
                raise orm.except_orm(u"NCF Invalido!", u"El NCF del proveedor no es válido!")

            vals.update({
                    u'account_id': inv.partner_id.property_account_payable.id,
                    u'check_total': 0,
                    u'child_ids': [[6, False, []]],
                    u'comment': "Factura de caja chica",
                    u'company_id': inv.company_id.id,
                    u'currency_id': journal_obj.company_id.currency_id.id,
                    u'date_due': False,
                    u'date_invoice': inv.date,
                    u'fiscal_position': inv.partner_id.property_account_position.id,
                    u'internal_number': inv.ncf,
                    u'journal_id': int(inv.journal_id),
                    u'message_follower_ids': False,
                    u'message_ids': False,
                    u'name': False,
                    u'ncf_required': ncf_required,
                    u'origin': current_model.name,
                    u'parent_id': False,
                    u'partner_bank_id': False,
                    u'partner_id': inv.partner_id.id,
                    u'payment_term': False,
                    u'period_id': current_model.period_id.id,
                    u'reference': inv.ncf,
                    u'reference_type': inv.reference_type,
                    u'supplier_invoice_number': False,
                    u'tax_line': [],
                    u'user_id': uid,
                    u'pay_to': current_model.journal_id.pay_to.id,
                    u'invoice_line': []
            })

            for line in inv.line_ids:
                line_list = [0, False]
                line_dict = {}
                line_dict.update({
                        u'account_analytic_id': False,
                        u'account_id': line.concept_id.account_expense.id,
                        u'asset_category_id': False,
                        u'discount': 0,
                        u'invoice_line_tax_id': [[6, False, [t.id for t in line.concept_id.supplier_taxes_id]]],
                        u'name': line.concept_id.name,
                        u'price_unit': abs(line.amount),
                        # u'product_id': line.concept_id.product_id.id,
                        u'quantity': 1,
                        u'uos_id': 1
                })
                line_list.append(line_dict)
                vals["invoice_line"].append(line_list)

            context.update({u'default_type': u'in_invoice',
                            u'journal_type': u'purchase'
                            })
        result = self.pool.get("account.invoice").create(cr, uid, vals, context=context)
        return result

    def create_purchase(self, cr, uid, ids, context=None):
        wizard_model = self.browse(cr, uid, ids, context=context)
        current_model = self.pool.get(context['active_model']).browse(cr, uid, context['active_id'])

        purchase_invoice_id = self._parse_vals(cr, uid, ids, current_model, wizard_model, context=context)
        inv = self.pool.get("account.invoice").browse(cr, uid, purchase_invoice_id, context=context)
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_open', cr)
        lines_vals = {u'account_id': current_model.journal_id.default_credit_account_id.id,
                      u'amount': inv.amount_total * -1,
                      u'analytic_account_id': False,
                      u'date': inv.date_invoice,
                      u'name': wizard_model[0].concept,
                      u'partner_id': inv.partner_id.id,
                      u'ref': inv.reference,
                      u'sequence': 0,
                      u'statement_id': current_model.id,
                      u'type': u'supplier',
                      u'voucher_id': False,
                      u"invoice_id": inv.id}

        self.pool.get('account.bank.statement.line').create(cr, uid, lines_vals, context=context)
        return {'type': 'ir.actions.act_window_close'}


class cjc_invoice_line_wizard(orm.TransientModel):
    _name = "cjc.invoice.line.wizard"


    _columns = {
        "concept_id": fields.many2one("marcos.cjc.concept", "Conceptos", required=True),
        "amount": fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True),
        # "quantity": fields.float('Quantity', digits_compute= dp.get_precision('Product Unit of Measure'), required=True),
        "invoice_id": fields.many2one("cjc.invoice.wizard", "Factura", ondelete='cascade', select=True)

    }

    _defaults = {
        # "quantity": 1,
        "amount": 1
    }