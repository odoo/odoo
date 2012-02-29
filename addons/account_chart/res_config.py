class account_configuration(osv.osv_memory):
    _inherit = 'res.config'

    _columns = {
            'tax_value' : fields.many2one('account.tax', 'Value'),
    }

account_configuration()