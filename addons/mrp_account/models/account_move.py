from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _stock_account_anglo_saxon_reconcile_valuation(self, product=False):
        super()._stock_account_anglo_saxon_reconcile_valuation(product=product)

        for move in self:
            if not move.is_invoice():
                continue
            if not move.company_id.anglo_saxon_accounting:
                continue

            # find out stock moves of any kit products
            stock_moves = move._stock_account_get_last_step_stock_moves()
            stock_moves = stock_moves.filtered(lambda l: l.bom_id and l.bom_id.type == 'phantom')

            if not stock_moves:
                continue

            products = product or move.mapped('invoice_line_ids.product_id')
            for prod in products:
                # we find all stock moves related to kit bom lines
                def find_bom_product_moves(line):
                    if line.bom_line_id.bom_id.product_id == prod:
                        return True
                    elif line.bom_line_id.bom_id.product_tmpl_id == prod.product_tmpl_id:
                        return True
                    return False

                product_stock_moves = stock_moves.filtered(find_bom_product_moves)

                if not product_stock_moves:
                    continue

                # reconcile our kit stock moves against our invoice
                bom_products = product_stock_moves.mapped('product_id')
                for bom_prod in bom_products:
                    if bom_prod.valuation != 'real_time':
                        continue

                    product_accounts = bom_prod.product_tmpl_id._get_product_accounts()
                    if move.is_sale_document():
                        product_interim_account = product_accounts['stock_output']
                    else:
                        product_interim_account = product_accounts['stock_input']

                    if product_interim_account.reconcile:
                        # Search for anglo-saxon lines linked to the product in the journal entry.
                        product_account_moves = move.line_ids.filtered(
                            lambda line: line.product_id == prod and line.account_id == product_interim_account and not line.reconciled)

                        # Search for anglo-saxon lines linked to the product in the stock moves.
                        product_account_moves += product_stock_moves.mapped('account_move_ids.line_ids')\
                            .filtered(lambda line: line.account_id == product_interim_account and not line.reconciled)

                        # Reconcile.
                        product_account_moves.reconcile()
