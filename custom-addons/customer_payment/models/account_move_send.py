from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_pdf_report_id(self, move):
        """Override to use custom Khmer invoice template for POS orders"""

        # Check if this invoice is from a POS order
        pos_order = self.env['pos.order'].search([('account_move', '=', move.id)], limit=1)

        if pos_order:
            # This is a POS invoice, use the custom Khmer template
            custom_template = self.env.ref(
                'customer_payment.account_invoices_customer_khmer',
                raise_if_not_found=False
            )
            if custom_template:
                return custom_template

        # For non-POS invoices, use the default behavior
        return super()._get_default_pdf_report_id(move)
