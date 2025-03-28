from odoo import models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """This action will be called by the POST button on a tax report account move.
           As posting this move will generate the XML report, it won't call `action_post`
           immediately, but will open the wizard that configures this XML file.
           Validating the wizard will resume the `action_post` and take these options in
           consideration when generating the XML report.
        """
        closing_move = self.filtered(lambda move: move.tax_closing_end_date and move.move_type == 'entry' and move.tax_country_code == 'IT')[:1]
        if closing_move and "l10n_it_xml_export_monthly_tax_report_options" not in self.env.context:
            view_id = self.env.ref('l10n_it_xml_export.monthly_tax_report_xml_export_wizard_view').id

            return {
                'name': _('Post a tax report entry'),
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'res_model': 'l10n_it_xml_export.monthly.tax.report.xml.export.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    **self.env.context,
                    'l10n_it_xml_export_monthly_tax_report_options': {
                        'date': {'date_to': closing_move.tax_closing_end_date}
                    },
                },
            }

        return super().action_post()
