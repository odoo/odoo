from odoo import fields, models


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    # This field is there to avoid having to do a lot of .ref() to check
    # if a tax has 1 of the 2 octroi de mer tax group.
    l10n_fr_om_rate = fields.Selection(selection=[
        ('general', "General"),
        ('regional', "Regional"),
    ])
