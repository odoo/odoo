# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError
from odoo.release import series
from odoo.tools import parse_version


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def write(self, values):
        """ Warn the user about updating account if they try to install account_reports with an out of date module

            A change in stable added a dependency between account_reports and a template update in account.
            It could cause a traceback when updating account_reports, or account_accountant with an out of date account
            module. This will inform the user about what to do in such case, by asking him to update invoicing.
        """
        mod_names = self.mapped('name')
        new_state = values.get('state')
        if new_state in ('to upgrade', 'to install') and 'account_reports' in mod_names and 'account' not in mod_names:
            invoicing_mod = self.env.ref('base.module_account')
            # Do not install or update account_report if account version is not >= 1.2, and we are not also installing/updating it
            if parse_version(invoicing_mod.latest_version) < parse_version(f'{series}.1.2') and invoicing_mod.state not in ('to install', 'to upgrade'):
                raise UserError(_("Please update the Invoicing module before continuing."))

        return super().write(values)
