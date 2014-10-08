from openerp import models


class AccountReportsConfiguratorGeneralJournal(models.TransientModel):
    _name = 'configurator.generaljournal'
    _inherit = 'configurator.journal'
