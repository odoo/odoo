from odoo import fields, models, api


MX_PACKAGING_CATALOG = [
    ('1A1', 'Bidones (Tambores) de Acero 1 de tapa no desmontable'),
    ('1A2', 'Bidones (Tambores) de Acero 1 de tapa desmontable'),
    ('1B1', 'Bidones (Tambores) de Aluminio de tapa no desmontable'),
    ('1B2', 'Bidones (Tambores) de Aluminio de tapa desmontable'),
    ('1D', 'Bidones (Tambores) de Madera contrachapada'),
    ('1G', 'Bidones (Tambores) de Cartón'),
    ('1H1', 'Bidones (Tambores) de Plástico de tapa no desmontable'),
    ('1H2', 'Bidones (Tambores) de Plástico de tapa desmontable'),
    ('1N1', 'Bidones (Tambores) de Metal que no sea acero ni aluminio de tapa no desmontable'),
    ('1N2', 'Bidones (Tambores) de Metal que no sea acero ni aluminio de tapa desmontable'),
    ('3A1', 'Jerricanes (Porrones) de Acero de tapa no desmontable'),
    ('3A2', 'Jerricanes (Porrones) de Acero de tapa desmontable'),
    ('3B1', 'Jerricanes (Porrones) de Aluminio de tapa no desmontable'),
    ('3B2', 'Jerricanes (Porrones) de Aluminio de tapa desmontable'),
    ('3H1', 'Jerricanes (Porrones) de Plástico de tapa no desmontable'),
    ('3H2', 'Jerricanes (Porrones) de Plástico de tapa desmontable'),
    ('4A', 'Cajas de Acero'),
    ('4B', 'Cajas de Aluminio'),
    ('4C1', 'Cajas de Madera natural ordinaria'),
    ('4C2', 'Cajas de Madera natural de paredes a prueba de polvos (estancas a los pulverulentos)'),
    ('4D', 'Cajas de Madera contrachapada'),
    ('4F', 'Cajas de Madera reconstituida'),
    ('4G', 'Cajas de Cartón'),
    ('4H1', 'Cajas de Plástico Expandido'),
    ('4H2', 'Cajas de Plástico Rígido'),
    ('5H1', 'Sacos (Bolsas) de Tejido de plástico sin forro ni revestimientos interiores'),
    ('5H2', 'Sacos (Bolsas) de Tejido de plástico a prueba de polvos (estancos a los pulverulentos)'),
    ('5H3', 'Sacos (Bolsas) de Tejido de plástico resistente al agua'),
    ('5H4', 'Sacos (Bolsas) de Película de plástico'),
    ('5L1', 'Sacos (Bolsas) de Tela sin forro ni revestimientos interiores'),
    ('5L2', 'Sacos (Bolsas) de Tela a prueba de polvos (estancos a los pulverulentos)'),
    ('5L3', 'Sacos (Bolsas) de Tela resistentes al agua'),
    ('5M1', 'Sacos (Bolsas) de Papel de varias hojas'),
    ('5M2', 'Sacos (Bolsas) de Papel de varias hojas, resistentes al agua'),
    ('6HA1', 'Envases y embalajes compuestos de Recipiente de plástico, con bidón (tambor) de acero'),
    ('6HA2', 'Envases y embalajes compuestos de Recipiente de plástico, con una jaula o caja de acero'),
    ('6HB1', 'Envases y embalajes compuestos de Recipiente de plástico, con un bidón (tambor) exterior de aluminio'),
    ('6HB2', 'Envases y embalajes compuestos de Recipiente de plástico, con una jaula o caja de aluminio'),
    ('6HC', 'Envases y embalajes compuestos de Recipiente de plástico, con una caja de madera'),
    ('6HD1', 'Envases y embalajes compuestos de Recipiente de plástico, con un bidón (tambor) de madera contrachapada'),
    ('6HD2', 'Envases y embalajes compuestos de Recipiente de plástico, con una caja de madera contrachapada'),
    ('6HG1', 'Envases y embalajes compuestos de Recipiente de plástico, con un bidón (tambor) de cartón'),
    ('6HG2', 'Envases y embalajes compuestos de Recipiente de plástico, con una caja de cartón'),
    ('6HH1', 'Envases y embalajes compuestos de Recipiente de plástico, con un bidón (tambor) de plástico'),
    ('6HH2', 'Envases y embalajes compuestos de Recipiente de plástico, con caja de plástico rígido'),
    ('6PA1', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con un bidón (tambor) de acero'),
    ('6PA2', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con una jaula o una caja de acero'),
    ('6PB1', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con un bidón (tambor) exterior de aluminio'),
    ('6PB2', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con una jaula o una caja de aluminio'),
    ('6PC', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con una caja de madera'),
    ('6PD1', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con bidón (tambor) de madera contrachapada'),
    ('6PD2', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con canasta de mimbre'),
    ('6PG1', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con un bidón (tambor) de cartón'),
    ('6PG2', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con una caja de cartón'),
    ('6PH1', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con un envase y embalaje de plástico expandido'),
    ('6PH2', 'Envases y embalajes compuestos de Recipiente de vidrio, porcelana o de gres, con un envase y embalaje de plástico rígido'),
    ('7H1', 'Bultos de Plástico'),
    ('7L1', 'Bultos de Tela'),
    ('Z01', 'No aplica')
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_mx_edi_hazardous_material = fields.Selection(related='unspsc_code_id.l10n_mx_edi_hazardous_material')
    l10n_mx_edi_hazardous_material_code_id = fields.Many2one(
        comodel_name='l10n_mx_edi.hazardous.material',
        string="Hazardous Material Designation Code",
        compute='_compute_hazardous_material_fields',
        store=True,
        readonly=False,
    )
    l10n_mx_edi_hazard_package_type = fields.Selection(
        selection=MX_PACKAGING_CATALOG,
        string="Packaging type for hazardous material",
        compute='_compute_hazardous_material_fields',
        store=True,
        readonly=False,
    )
    l10n_mx_edi_material_type = fields.Selection(
        selection=[
            ('01', 'Materia prima'),
            ('02', 'Materia procesada'),
            ('03', 'Materia terminada(producto terminado)'),
            ('04', 'Materia para la industria manufacturera'),
            ('05', 'Otra'),
        ],
        string="Material Type",
        help="State of the material or product when performing a foreign trade operation.",
    )
    l10n_mx_edi_material_description = fields.Char(
        string="Material Description",
        help="Description of the state of the material or product when performing a foreign trade operation.",
    )

    @api.depends('unspsc_code_id')
    def _compute_hazardous_material_fields(self):
        for product in self:
            if not product.unspsc_code_id.l10n_mx_edi_hazardous_material:
                product.l10n_mx_edi_hazardous_material_code_id = False
                product.l10n_mx_edi_hazard_package_type = False
