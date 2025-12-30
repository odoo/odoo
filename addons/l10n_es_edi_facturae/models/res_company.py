from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_edi_facturae_residence_type = fields.Char(string='Facturae EDI Residency Type Code', related='partner_id.l10n_es_edi_facturae_residence_type')
    l10n_es_edi_facturae_certificate_ids = fields.One2many(string='Facturae EDI signing certificate',
        comodel_name='certificate.certificate', inverse_name='company_id', domain=[('scope', '=', 'facturae')])

    def _l10n_es_edi_facturae_export_check(self):
        checks = {
            'company_currency_check': {
                'fields': [('currency_id',)],
                'message': self.env._("The company's currency must be set to Euro (€)."),
            },
        }
        errors = {}
        for key, check in checks.items():
            for fields_tuple in check.pop('fields'):
                if invalid_records := self.filtered(lambda record: not any(record[field] for field in fields_tuple)):
                    errors[f"l10n_es_edi_facturae_{key}"] = {
                        'level': 'danger',
                        'message': check['message'],
                        'action_text': self.env._("View Company(s)"),
                        'action': invalid_records._get_records_action(name=self.env._("Check Company Data")),
                    }
        if invalid_records := self.filtered(lambda company: not company.sudo().l10n_es_edi_facturae_certificate_ids):
            errors["l10n_es_edi_company_facturae_certificate_check"] = {
                'level': 'danger',
                'message': self.env._("Company must have a valid Factura-e certificate configured."),
                'action_text': self.env._("View Certificate(s)"),
                'action': {
                    'name': self.env._("Settings"),
                    'type': 'ir.actions.act_url',
                    'target': 'self',
                    'url': '/odoo/settings#certificates_settings',
                },
            }
        return errors
