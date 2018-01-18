# -*- coding: utf-8 -*-

from odoo import fields, models, _

from odoo.tools.float_utils import float_is_zero

from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_move_id = fields.Many2one('stock.move', string='Stock Move')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def get_aml_data_to_fully_reconcile_out_invoices_with_stock_valuation(self, account, product, partner_id, shipped_qty, qty_to_treat, value_to_balance):
        #TODO OCO self=aml des factures à réconclier, account=(interim account), le compte à réconcilier, product, shipped_qty=previously_shipped_qty, value_to_balance=debit_val
        #Pour le produit (et qty_to_treat), à la limite, tu peux commencer la méthode ici par un mapped pour les avoir sans doublon et boucler dessus
        rslt = []

        """product_accounts = product.product_tmpl_id._get_product_accounts()
        interim_output_account = product_accounts['stock_output']

        #TODO OCO Calcul du montant rectificatif à écrire
        qty_to_treat_counter = qty_to_treat #TODO OCO je mets des compteurs pour aider au debug, mais on pourrait directement utiliser les param
        shipped_qty_counter = shipped_qty
        invoice_valuation = 0.0
        total_treated_qty = 0
        company = None
        for invoice_aml in self.filtered(lambda x: x.account_id == account).sorted(key=lambda x: x.date): #TODO OCO filtrer aussi sur quantité !=0 (!float!) ?

            invoice_aml_qty_left = invoice_aml.quantity

            if not float_is_zero(shipped_qty_counter, precision_rounding=product.uom_id.rounding):
                qty_to_substract = min(invoice_aml.quantity, shipped_qty_counter)
                shipped_qty_counter -= qty_to_substract
                invoice_aml_qty_left = invoice_aml.quantity - qty_to_substract

            if invoice_aml_qty_left:
                treated_qty = min(qty_to_treat_counter, invoice_aml_qty_left)
                invoice_valuation += (invoice_aml.balance / invoice_aml.quantity) * treated_qty
                qty_to_treat_counter -= treated_qty
                total_treated_qty += treated_qty

            if company == None:
                company = invoice_aml.company_id
            elif company != invoice_aml.company_id:
                raise UserError(_("Trying to gather data to reconcile lines from different companies"))

            if float_is_zero(qty_to_treat_counter, precision_rounding=self.product_id.uom_id.rounding):
                break

        # TODO OCO génération des données d'aml supplémentaires

        difference_with_invoice = company.currency_id.round((value_to_balance / qty_to_treat) * total_treated_qty + invoice_valuation)

        if not company.currency_id.is_zero(difference_with_invoice):
            balancing_output_line_vals = {
                'name': _('Effective inventory valuation correction'),
                'product_id': product.id,
                'quantity': 0, # This is an adjustment writing, so there is no quantity here
                'product_uom_id': product.uom_id.id,
                'partner_id': partner_id,
                'credit': difference_with_invoice > 0 and difference_with_invoice or 0,
                'debit': difference_with_invoice < 0 and -difference_with_invoice or 0,
                'account_id': interim_output_account.id,
            }

            balancing_output_counterpart_line_vals = {
                'name': _('Effective inventory valuation correction'),
                'product_id': product.id,
                'quantity': 0, # This is an adjustment writing, so there is no quantity here
                'product_uom_id': product.uom_id.id,
                'partner_id': partner_id,
                'credit': difference_with_invoice < 0 and -difference_with_invoice or 0,
                'debit': difference_with_invoice > 0 and difference_with_invoice or 0,
                'account_id': product_accounts['expense'].id, #TODO OCO: avec ça, c'est pas top général ... si ? C'estjuste pour les out invoices, quoi
            }

            rslt.append((0, 0, balancing_output_line_vals))
            rslt.append((0, 0, balancing_output_counterpart_line_vals))"""
        return rslt