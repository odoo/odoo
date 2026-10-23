from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_es_edi_verifactu_required = fields.Boolean(
        related='company_id.l10n_es_edi_verifactu_required',
        readonly=False,
    )
    l10n_es_edi_verifactu_certificate_ids = fields.One2many(
        related='company_id.l10n_es_edi_verifactu_certificate_ids',
        readonly=False,
    )
    l10n_es_edi_verifactu_test_environment = fields.Boolean(
        related='company_id.l10n_es_edi_verifactu_test_environment',
        readonly=False,
    )

    @api.onchange('l10n_es_edi_verifactu_test_environment')
    def _onchange_l10n_es_edi_verifactu_test_environment(self):
        # Opening the form also triggers the onchange: only warn if the company is still saved in test
        leaving_test = self.company_id.l10n_es_edi_verifactu_test_environment
        if leaving_test and not self.l10n_es_edi_verifactu_test_environment:
            return {'warning': {
                'title': _("Switching to production"),
                'message': _(
                    "This cannot be undone: the Veri*Factu chain restarts and the test environment cannot be enabled again once a document is chained. Use a duplicated database to run tests."),
            }}
