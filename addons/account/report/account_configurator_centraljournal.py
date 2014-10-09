from openerp import models


class AccountReportsConfiguratorCentralJournal(models.TransientModel):
    _name = 'configurator.centraljournal'
    _inherit = 'configurator.journal'
