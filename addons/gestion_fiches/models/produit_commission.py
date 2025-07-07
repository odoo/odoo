from odoo import models, fields, api

class ProduitCommission(models.Model):
    _name = 'produit.commission'
    _description = 'Produit avec Commissions'

    name = fields.Char(string='Nom du Produit')
    
    categorie = fields.Selection([
        ('ordinateur', 'Ordinateur'),
        ('macbook', 'Macbook'),
        ('accessoire', 'Accessoire'),
        ('telephone', 'Téléphone'),
        ('imprimante', 'Imprimante')
    ], string='Catégorie')
    
    prix = fields.Float(string='Prix')

    commission_senior_pct = fields.Float(string='Commission Senior (%)')
    commission_junior_pct = fields.Float(string='Commission Junior (%)')
    commission_commercial_pct = fields.Float(string='Commission Commercial (%)')

    commission_senior_montant = fields.Float(string='Montant Senior', compute='_compute_commissions')
    commission_junior_montant = fields.Float(string='Montant Junior', compute='_compute_commissions')
    commission_commercial_montant = fields.Float(string='Montant Commercial', compute='_compute_commissions')

    @api.depends('prix', 'commission_senior_pct', 'commission_junior_pct', 'commission_commercial_pct')
    def _compute_commissions(self):
        for record in self:
            prix = record.prix or 0
            record.commission_senior_montant = prix * (record.commission_senior_pct or 0) / 100
            record.commission_junior_montant = prix * (record.commission_junior_pct or 0) / 100
            record.commission_commercial_montant = prix * (record.commission_commercial_pct or 0) / 100

    def appliquer_commissions_standard(self):
        for record in self:
            record.commission_senior_pct = 10.0
            record.commission_junior_pct = 7.0
            record.commission_commercial_pct = 5.0
