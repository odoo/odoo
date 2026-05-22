from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_tr_nilvera_export_alias = fields.Char(
        string="Nilvera Export Alias",
        config_parameter='l10n_tr_nilvera_einvoice.export_alias',
        default='urn:mail:ihracatpk@gtb.gov.tr',
        help="Set the default GİB 'Posta Kutusu' (mailbox) alias for sending "
        "export invoices (İhracat Faturası). \nThis is almost always "
        "'urn:mail:ihracatpk@gtb.gov.tr' (Turkish Ministry of Trade) and "
        "should not be changed unless you have a specific reason.",
    )
