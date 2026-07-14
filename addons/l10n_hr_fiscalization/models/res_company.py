from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_hr_fiscalization_mode = fields.Selection(
        selection=[
            ('prod', 'Production'),
            ('test', 'Test'),
            ('demo', 'Demo'),
        ],
        string='Fiscalization Operating mode',
        default='demo',
    )

    l10n_hr_fiscalization_certificate = fields.Many2one(
        string="Fiscalization RDC Certificate",
        help="FINA RDC CA certificate for fiscalization",
        comodel_name='certificate.certificate',
    )

    l10n_hr_fiscalization_ca_intermediate_pem = fields.Binary(
        string="TA CA Intermediate (PEM)",
        help="FINA RDC 2020 intermediate CA certificate in PEM. Used to verify the TA production TLS certificate.",
        attachment=True,
    )

    l10n_hr_fiscalization_ca_root_pem = fields.Binary(
        string="TA CA Root (PEM)",
        help="FINA Root CA certificate in PEM. Used to verify the TA production TLS certificate.",
        attachment=True,
    )

    l10n_hr_fiscalization_sequence_identifier = fields.Selection(
        [
            ('P', 'P - Business Premises Level'),
            ('N', 'N - Issuing Device Level')
        ],
        string="Sequence Level Indicator",
        default='P',
        help="Specifies whether invoice numbering is maintained at the business premises level or at the issuing device level."
    )
