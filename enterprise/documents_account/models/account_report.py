# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _init_options_buttons(self, options, previous_options):
        # OVERRIDE
        super()._init_options_buttons(options, previous_options)
        options['buttons'].append({'name': _('Copy to Documents'), 'sequence': 100, 'action': 'open_report_export_wizard'})

    def open_report_export_wizard(self, options):
        """ Creates a new export wizard for this report and returns an act_window
        opening it. A new account_report_generation_options key is also added to
        the context, containing the current options selected on this report
        (which must hence be taken into account when exporting it to a file).
        """
        self.ensure_one()
        new_context = {
            **self._context,
            'account_report_generation_options': options,
            'default_report_id': self.id,
        }
        view_id = self.env.ref('account_reports.view_report_export_wizard').id

        # We have to create it before returning the action (and not just use a record in 'new' state), so that we can create
        # the transient records used in the m2m for the different export formats.
        new_wizard = self.with_context(new_context).env['account_reports.export.wizard'].create({'report_id': self.id})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Export'),
            'view_mode': 'form',
            'res_model': 'account_reports.export.wizard',
            'res_id': new_wizard.id,
            'target': 'new',
            'views': [[view_id, 'form']],
            'context': new_context,
        }
