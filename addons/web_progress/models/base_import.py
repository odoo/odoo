# Part of web_progress. See LICENSE file for full copyright and licensing details.
from odoo import models, api, registry, fields, _
from odoo.exceptions import UserError


class BaseImport(models.TransientModel):
    _inherit = 'base_import.import'

    def execute_import(self, fields, columns, options, dryrun=False):
        """
        Catch UserError exception and pass it as an error.
        Re-raise all other errors
        """
        try:
            ret = super(BaseImport, self).execute_import(fields, columns, options, dryrun=dryrun)
        except UserError as e:
            ret = {'messages': [{'record': False, 'type': 'warning', 'message': e.args[0], }]}
        except Exception:
            raise
        return ret
