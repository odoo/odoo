# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_br_cest_code = fields.Char(
        string='CEST Code',
        help='A tax classification code used to identify goods and products subject to tax substitution under ICMS regulations.'
             'It helps determine the applicable tax treatment and procedures for specific items.'
             'Check if your product is subject or not to this in https://www.codigocest.com.br/.'
    )
    l10n_br_ncm_code_id = fields.Many2one('l10n_br.ncm.code', string='Mercosul NCM Code', help='Brazil: NCM (Nomenclatura Comun do Mercosul) Code from the Mercosur List')

    # technical names of these selections fields are directly passed to the API
    l10n_br_source_origin = fields.Selection([
            ('0', 'National goods - except those treated in codes 3,4, 5 and 8'),
            ('1', 'Foreign goods - Imported directly by seller, except those in code 6'),
            ('2', 'Foreign goods - Acquired in the internal market (inside Brazil), except those in code 7'),
            ('3', 'National goods - Merchandise or goods with imported content above 40% and with less than or equal to 70%'),
            ('4',
             'National goods from production following \'standard basic processes\' as stablished by legislation (standard basic processes are devised to separate simple assembly from manufaturing processes)'),
            ('5', 'National goods - Merchandise or goods with imported content equal or below 40%'),
            ('6',
             'Foreign goods - Directly imported by Seller, without a National Equivalent as listed by Comex and natural gas'),
            ('7', 'Foreign goods - Acquired inside Brazil, without a National Equivalent as listed by Comex and natural gas'),
            ('8', 'National goods - Merchandise or goods with imported content above 70% (pt)'),
        ],
        string='Source of Origin',
        help='Brazil: Product Source of Origin indicates if the product has a foreing or national origin with different variations and characteristics dependin on the product use case'
    )
    l10n_br_sped_type = fields.Selection([
        ('FOR PRODUCT', 'For product'),
        ('FOR MERCHANDISE', 'For merchandise'),
        ('NO RESTRICTION', 'No restriction'),
        ('SERVICE', 'Service'),
        ('FEEDSTOCK', 'Feedstock'),
        ('FIXED ASSETS', 'Fixed assets'),
        ('PACKAGING', 'Packaging'),
        ('PRODUCT IN PROCESS', 'Product in process'),
        ('SUBPRODUCT', 'Subproduct'),
        ('INTERMEDIATE PRODUCT', 'Intermediate product'),
        ('MATERIAL FOR USAGE AND CONSUMPTION', 'Material for usage and consumption'),
        ('OTHER INPUTS', 'Other inputs'),
    ], string='SPED Fiscal Product Type', help='Brazil: Fiscal product type according to SPED list table')
    l10n_br_use_type = fields.Selection([
        ('use or consumption', 'Use or consumption'),
        ('resale', 'Resale'),
        ('agricultural production', 'Agricultural production'),
        ('production', 'Production'),
        ('fixed assets', 'Fixed assets'),
        ('notApplicable', 'Not applicable'),
    ], string='Purpose of Use', help='Brazil: indicate what is the usage purpose for this product')
    l10n_br_transport_cost_type = fields.Selection([
        ('freight', 'Freight'),
        ('insurance', 'Insurance'),
        ('other', 'Other costs')
    ], string='Transport Cost Type', help='Brazil: select whether this product will be use to register Freight, Insurance or Other Costs amounts related to the transaction.')
