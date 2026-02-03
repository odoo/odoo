from odoo import models, fields, api, Command
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class EstatePropertyInherit(models.Model):
    """Inherit estate.property to add invoicing functionality"""
    _inherit = 'estate.property'
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        readonly=True,
        copy=False,
        tracking=True
    )
    
    def action_sold(self):
        """Override sold action to create invoice with lines"""
        _logger.info("=== ESTATE ACCOUNT: Starting action_sold with invoice lines ===")
        
       
        result = super().action_sold()
        
        for property in self:
            if not property.buyer_id:
                raise UserError(f"Cannot create invoice: No buyer for property {property.name}")
            
            if property.selling_price <= 0:
                raise UserError(f"Cannot create invoice: Selling price must be positive for {property.name}")
            
            
            company = self.env.company
            
            
            journal = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', company.id)
            ], limit=1)
            
            if not journal:
                
                journal = self.env['account.journal'].search([
                    ('company_id', '=', company.id)
                ], limit=1)
                
            if not journal:
                raise UserError("No journal found. Please configure Accounting settings.")
            
            
            commission_amount = property.selling_price * 0.06  
            admin_fee = 100.00 
            
            
            invoice = self.env['account.move'].create({
                'partner_id': property.buyer_id.id,
                'move_type': 'out_invoice',
                'journal_id': journal.id,
                'invoice_date': fields.Date.today(),
                'invoice_origin': f"Property Sale: {property.name}",
                'ref': f"RE-{property.name}",
                
                'invoice_line_ids': [
                   
                    Command.create({
                        'name': f"Sales commission for property: {property.name}",
                        'quantity': 1,
                        'price_unit': commission_amount,
                    }),
                    
                    Command.create({
                        'name': "Administrative fees",
                        'quantity': 1,
                        'price_unit': admin_fee,
                    }),
                ]
            })
            
           
            property.invoice_id = invoice.id
            
            _logger.info(f"Created invoice: {invoice.name}")
            _logger.info(f"Commission (6%): {commission_amount}")
            _logger.info(f"Admin fee: {admin_fee}")
            _logger.info(f"Total: {commission_amount + admin_fee}")
        
        return result
    
    def action_view_invoice(self):
        """Open the invoice"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }