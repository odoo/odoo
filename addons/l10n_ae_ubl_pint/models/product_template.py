from odoo import fields, models

# AE-GoodsType code list, exported as cbc:NatureCode ("Type of goods or services").
# https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/codelist/GoodsType/
L10N_AE_GOODS_SERVICE_TYPE_SELECTION = [
    ('DL8.48.8.2', 'Electronic Devices'),
    ('DL8.48.8.1', 'Gold and Diamonds'),
    ('DL8.48.3.1', 'Crude or refined oil'),
    ('DL8.48.3.2', 'Unprocessed or processed natural gas'),
    ('DL8.48.3.3', 'Pure hydrocarbons'),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_ae_is_good_and_service = fields.Boolean(string='Is Both Good and Service')
    l10n_ae_goods_service_type = fields.Selection(
        string='RCM Goods Type',
        selection=L10N_AE_GOODS_SERVICE_TYPE_SELECTION,
    )
    l10n_ae_hs_code = fields.Char(string='FTA HS Code', help="Harmonized System code of the goods, reported to the FTA.")
    l10n_ae_service_accounting_code = fields.Char(string='Service Accounting Code', help="Service Accounting Code of the services, reported to the FTA.")
