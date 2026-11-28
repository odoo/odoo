# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import SQL


class IrModel(models.Model):
    _inherit = 'ir.model'

    @api.ondelete(at_uninstall=False)
    def _unlink_clear_chatbot_redirect(self):
        """Clear the chatbot redirections to the records of the models being removed.

        Their table is dropped without unlinking the records, so the `ondelete` of the records
        never runs, and once the registry is reloaded without the model, reading a reference to
        it fails.
        """
        self.env['chatbot.script.answer'].flush_model(['redirect_record_ref'])
        self.env.cr.execute(SQL(
            "UPDATE chatbot_script_answer SET redirect_record_ref = NULL"
            " WHERE split_part(redirect_record_ref, ',', 1) IN %s",
            tuple(self.mapped('model')),
        ))
        self.env['chatbot.script.answer'].invalidate_model(['redirect_record_ref'])
