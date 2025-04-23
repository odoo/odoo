from odoo import models, Command

class EstateProperty(models.Model):
    _inherit = 'estate.property'

    def action_sold(self):
        print("Method action_sold")
        res = super().action_sold()
        
        # On récupère un compte comptable valide pour les lignes de facture
        account = self.env['account.account'].search([('code', '=', '400000')], limit=1)
        if not account:
            raise ValueError("Compte comptable avec code 400000 introuvable.")

        
        # create invoice
        self.env['account.move'].create({
            'partner_id': self.buyer_id.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'name':f"Commission (6%) vente de {self.name}",
                    'quantity': 1,
                    'price_unit': self.selling_price * 0.6,
                    'account_id': account.id,
                }),
                Command.create({
                    'name':"Frais administratifs",
                    'quantity': 1,
                    'price_unit': 100.0,
                    'account_id': account.id,
                })
            ]
            
        })
        return res

