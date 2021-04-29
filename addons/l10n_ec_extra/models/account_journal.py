class AccountJournal(models.Model):
    
    _inherit = 'account.journal'

    l10n_ec_entity = fields.Char(string='Emission Entity', length=3, default='001')
    l10n_ec_emission = fields.Char(string='Emission Point', length=3, default='001')

    

    
    
