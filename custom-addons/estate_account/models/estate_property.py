from odoo import models, fields, Command
import logging

_logger = logging.getLogger(__name__)


class EstateProperty(models.Model):
    _inherit = 'estate.property'
    
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    
    def action_sold(self):
        """Override action_sold to create invoice when property is sold"""
        _logger.info("=== ESTATE ACCOUNT: Starting action_sold with invoice lines ===")
        
        # CRITICAL SECURITY CHECK: Verify user has permission to update this property
        # This check happens BEFORE we use sudo() to create the invoice
        # Without this check, any user could trigger invoice creation by calling this method
        try:
            self.check_access('write')
            _logger.info(f"Security check passed for user {self.env.user.name} on property {self.name}")
        except Exception as e:
            _logger.error(f"Security check failed for user {self.env.user.name} on property {self.name}: {e}")
            raise
        
        # Call parent method to set state to 'sold'
        result = super().action_sold()
        
        # Create invoice for the buyer
        # We use sudo() here because agents don't have full accounting permissions
        # but we've already verified they have permission to sell this property above
        
        _logger.info("=" * 100)
        _logger.info(" " * 29 + "REACHED: About to create invoice with sudo()")
        _logger.info("=" * 100)
        
        # SECURITY: Input validation before sudo()
        # Validate that we have a buyer and selling price
        if not self.buyer_id:
            raise ValueError("Cannot create invoice without a buyer")
        if not self.selling_price or self.selling_price <= 0:
            raise ValueError("Cannot create invoice with invalid selling price")
        
        # Find the journal for invoices (using sudo because agents may not have journal access)
        journal = self.env['account.journal'].sudo().search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not journal:
            raise ValueError("No sales journal found for invoice creation")
        
        # Calculate invoice amounts
        # 6% commission on selling price
        commission = self.selling_price * 0.06
        # Administrative fee
        admin_fee = 100.0
        
        # Create invoice (using sudo to bypass accounting permissions)
        invoice = self.env['account.move'].sudo().create({
            'partner_id': self.buyer_id.id,
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'invoice_line_ids': [
                Command.create({
                    'name': f'Commission for property: {self.name}',
                    'quantity': 1,
                    'price_unit': commission,
                }),
                Command.create({
                    'name': 'Administrative fees',
                    'quantity': 1,
                    'price_unit': admin_fee,
                }),
            ],
        })
        
        # Link invoice to property (also using sudo)
        self.sudo().write({
            'invoice_id': invoice.id,
        })
        
        _logger.info(f"Created invoice: {invoice.name} (using sudo for security bypass)")
        _logger.info(f"Commission (6%%): {commission}")
        _logger.info(f"Admin fee: {admin_fee}")
        _logger.info(f"Total: {commission + admin_fee}")
        
        return result
