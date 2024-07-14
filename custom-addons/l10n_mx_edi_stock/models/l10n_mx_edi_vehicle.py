# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError

class Vehicle(models.Model):
    _name = 'l10n_mx_edi.vehicle'
    _description = 'MX EDI Vehicle'
    _rec_names_search = ['name', 'vehicle_licence']

    def _default_intermediary(self):
        return [(0, 0, {'type': '01'})]

    active = fields.Boolean(default=True)
    name = fields.Char(
        string='SCT Permit Number',
        required=True,
        help='The permit number granted to the unit performing the transfer of goods')
    transport_insurer = fields.Char('Insurance Company', help='The name of the insurer that covers the liability risks of the vehicle')
    transport_insurance_policy = fields.Char('Insurance Policy Number')
    transport_perm_sct = fields.Selection(
        selection=[
            ('TPAF01', 'Autotransporte Federal de carga general.'),
            ('TPAF02', 'Transporte privado de carga.'),
            ('TPAF03', 'Autotransporte Federal de Carga Especializada de materiales y residuos peligrosos.'),
            ('TPAF04', 'Transporte de automóviles sin rodar en vehículo tipo góndola.'),
            ('TPAF05', 'Transporte de carga de gran peso y/o volumen de hasta 90 toneladas.'),
            ('TPAF06', 'Transporte de carga especializada de gran peso y/o volumen de más 90 toneladas.'),
            ('TPAF07', 'Transporte Privado de materiales y residuos peligrosos.'),
            ('TPAF08', 'Autotransporte internacional de carga de largo recorrido.'),
            ('TPAF09', 'Autotransporte internacional de carga especializada de materiales y residuos peligrosos de largo recorrido.'),
            ('TPAF10', 'Autotransporte Federal de Carga General cuyo ámbito de aplicación comprende la franja fronteriza con Estados Unidos.'),
            ('TPAF11', 'Autotransporte Federal de Carga Especializada cuyo ámbito de aplicación comprende la franja fronteriza con Estados Unidos.'),
            ('TPAF12', 'Servicio auxiliar de arrastre en las vías generales de comunicación.'),
            ('TPAF13', 'Servicio auxiliar de servicios de arrastre, arrastre y salvamento, y depósito de vehículos en las vías generales de comunicación.'),
            ('TPAF14', 'Servicio de paquetería y mensajería en las vías generales de comunicación.'),
            ('TPAF15', 'Transporte especial para el tránsito de grúas industriales con peso máximo de 90 toneladas.'),
            ('TPAF16', 'Servicio federal para empresas arrendadoras servicio público federal.'),
            ('TPAF17', 'Empresas trasladistas de vehículos nuevos.'),
            ('TPAF18', 'Empresas fabricantes o distribuidoras de vehículos nuevos.'),
            ('TPAF19', 'Autorización expresa para circular en los caminos y puentes de jurisdicción federal con configuraciones de tractocamión doblemente articulado.'),
            ('TPAF20', 'Autotransporte Federal de Carga Especializada de fondos y valores.'),
            ('TPTM01', 'Permiso temporal para navegación de cabotaje'),
            ('TPTA01', 'Concesión y/o autorización para el servicio regular nacional y/o internacional para empresas mexicanas'),
            ('TPTA02', 'Permiso para el servicio aéreo regular de empresas extranjeras'),
            ('TPTA03', 'Permiso para el servicio nacional e internacional no regular de fletamento'),
            ('TPTA04', 'Permiso para el servicio nacional e internacional no regular de taxi aéreo'),
            ('TPXX00', 'Permiso no contemplado en el catálogo.')
        ],
        string='SCT Permit Type',
        help='The type of permit code to carry out the goods transfer service')
    vehicle_model = fields.Char('Vehicle Model Year')
    vehicle_config = fields.Selection(
        selection=[
            ('VL', 'Vehículo ligero de carga (2 llantas en el eje delantero y 2 llantas en el eje trasero)'),
            ('C2', 'Camión Unitario (2 llantas en el eje delantero y 4 llantas en el eje trasero)'),
            ('C3', 'Camión Unitario (2 llantas en el eje delantero y 6 o 8 llantas en los dos ejes traseros)'),
            ('C2R2', 'Camión-Remolque (6 llantas en el camión y 8 llantas en remolque)'),
            ('C3R2', 'Camión-Remolque (10 llantas en el camión y 8 llantas en remolque)'),
            ('C2R3', 'Camión-Remolque (6 llantas en el camión y 12 llantas en remolque)'),
            ('C3R3', 'Camión-Remolque (10 llantas en el camión y 12 llantas en remolque)'),
            ('T2S1', 'Tractocamión Articulado (6 llantas en el tractocamión, 4 llantas en el semirremolque)'),
            ('T2S2', 'Tractocamión Articulado (6 llantas en el tractocamión, 8 llantas en el semirremolque)'),
            ('T2S3', 'Tractocamión Articulado (6 llantas en el tractocamión, 12 llantas en el semirremolque)'),
            ('T3S1', 'Tractocamión Articulado (10 llantas en el tractocamión, 4 llantas en el semirremolque)'),
            ('T3S2', 'Tractocamión Articulado (10 llantas en el tractocamión, 8 llantas en el semirremolque)'),
            ('T3S3', 'Tractocamión Articulado (10 llantas en el tractocamión, 12 llantas en el semirremolque)'),
            ('T2S1R2', 'Tractocamión Semirremolque-Remolque (6 llantas en el tractocamión, 4 llantas en el semirremolque y 8 llantas en el remolque)'),
            ('T2S2R2', 'Tractocamión Semirremolque-Remolque (6 llantas en el tractocamión, 8 llantas en el semirremolque y 8 llantas en el remolque)'),
            ('T2S1R3', 'Tractocamión Semirremolque-Remolque (6 llantas en el tractocamión, 4 llantas en el semirremolque y 12 llantas en el remolque)'),
            ('T3S1R2', 'Tractocamión Semirremolque-Remolque (10 llantas en el tractocamión, 4 llantas en el semirremolque y 8 llantas en el remolque)'),
            ('T3S1R3', 'Tractocamión Semirremolque-Remolque (10 llantas en el tractocamión, 4 llantas en el semirremolque y 12 llantas en el remolque)'),
            ('T3S2R2', 'Tractocamión Semirremolque-Remolque (10 llantas en el tractocamión, 8 llantas en el semirremolque y 8 llantas en el remolque)'),
            ('T3S2R3', 'Tractocamión Semirremolque-Remolque (10 llantas en el tractocamión, 8 llantas en el semirremolque y 12 llantas en el remolque)'),
            ('T3S2R4', 'Tractocamión Semirremolque-Remolque (10 llantas en el tractocamión, 8 llantas en el semirremolque y 16 llantas en el remolque)'),
            ('T2S2S2', 'Tractocamión Semirremolque-Semirremolque (6 llantas en el tractocamión, 8 llantas en el semirremolque delantero y 8 llantas en el semirremolque trasero)'),
            ('T3S2S2', 'Tractocamión Semirremolque-Semirremolque (10 llantas en el tractocamión, 8 llantas en el semirremolque delantero y 8 llantas en el semirremolque trasero)'),
            ('T3S3S2', 'Tractocamión Semirremolque-Semirremolque (10 llantas en el tractocamión, 12 llantas en el semirremolque delantero y 8 llantas en el semirremolque trasero)'),
            ('OTROEVGP', 'Especializado de carga Voluminosa y/o Gran Peso'),
            ('OTROSG', 'Servicio de Grúas'),
            ('GPLUTA', 'Grúa de Pluma Tipo A'),
            ('GPLUTB', 'Grúa de Pluma Tipo B'),
            ('GPLUTC', 'Grúa de Pluma Tipo C'),
            ('GPLUTD', 'Grúa de Pluma Tipo D'),
            ('GPLATA', 'Grúa de Plataforma Tipo A'),
            ('GPLATB', 'Grúa de Plataforma Tipo B'),
            ('GPLATC', 'Grúa de Plataforma Tipo C'),
            ('GPLATD', 'Grúa de Plataforma Tipo D'),
        ],
        string='Vehicle Configuration',
        help='The type of vehicle used')
    vehicle_licence = fields.Char(
        string='Vehicle Plate Number',
        help='License plate number of the vehicle in which the goods are transferred. Alphanumeric characters only, no dashes and/or spaces',
        required=True)
    trailer_ids = fields.One2many(
        comodel_name='l10n_mx_edi.trailer',
        inverse_name='vehicle_id',
        string='Trailers',
        help='Up to 2 trailers used on this vehicle')
    figure_ids = fields.One2many(
        comodel_name='l10n_mx_edi.figure',
        inverse_name='vehicle_id',
        string='Intermediaries',
        default=_default_intermediary,
        help='Information corresponding to the transport intermediaries, as well as those taxpayers related to the transportation method used to transport the goods')

    @api.depends('vehicle_licence')
    def _compute_display_name(self):
        for vehicle in self:
            vehicle.display_name = f'[{vehicle.vehicle_licence}] {vehicle.name}'

    @api.constrains('figure_ids')
    def _check_figures(self):
        for vehicle in self:
            operators = vehicle.figure_ids.filtered(lambda f: f.type == '01')
            if not operators:
                raise ValidationError(_("The vehicle intermediaries must contain at least one intermediary of type: Operator"))

    @api.constrains('trailer_ids')
    def _check_trailers(self):
        for vehicle in self:
            if len(vehicle.trailer_ids) > 2:
                raise ValidationError(_("A maximum of 2 trailers are allowed per vehicle"))

class Figure(models.Model):
    _name = 'l10n_mx_edi.figure'
    _description = 'MX EDI Vehicle Intermediary Figure'

    vehicle_id = fields.Many2one('l10n_mx_edi.vehicle')
    type = fields.Selection(
        selection=[
            ('01', 'Operador'),
            ('02', 'Propietario'),
            ('03', 'Arrendador'),
            ('04', 'Notificado'),
        ])
    operator_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        help="Register the contact that is involved depending on its responsibility in the transport (Operador, "
             "Propietario, Arrendador, Notificado)")
    part_ids = fields.Many2many('l10n_mx_edi.part', string='Parts')

class Part(models.Model):
    _name = 'l10n_mx_edi.part'
    _description = 'MX EDI Intermediary Part'

    code = fields.Char(required=True)
    name = fields.Char(required=True)

class Trailer(models.Model):
    _name = 'l10n_mx_edi.trailer'
    _description = 'MX EDI Vehicle Trailer'

    vehicle_id = fields.Many2one('l10n_mx_edi.vehicle')
    name = fields.Char('Number Plate')
    sub_type = fields.Selection(
        selection=[
            ('CTR001', 'Caballete'),
            ('CTR002', 'Caja'),
            ('CTR003', 'Caja Abierta'),
            ('CTR004', 'Caja Cerrada'),
            ('CTR005', 'Caja De Recolección Con Cargador Frontal'),
            ('CTR006', 'Caja Refrigerada'),
            ('CTR007', 'Caja Seca'),
            ('CTR008', 'Caja Transferencia'),
            ('CTR009', 'Cama Baja o Cuello Ganso'),
            ('CTR010', 'Chasis Portacontenedor'),
            ('CTR011', 'Convencional De Chasis'),
            ('CTR012', 'Equipo Especial'),
            ('CTR013', 'Estacas'),
            ('CTR014', 'Góndola Madrina'),
            ('CTR015', 'Grúa Industrial'),
            ('CTR016', 'Grúa '),
            ('CTR017', 'Integral'),
            ('CTR018', 'Jaula'),
            ('CTR019', 'Media Redila'),
            ('CTR020', 'Pallet o Celdillas'),
            ('CTR021', 'Plataforma'),
            ('CTR022', 'Plataforma Con Grúa'),
            ('CTR023', 'Plataforma Encortinada'),
            ('CTR024', 'Redilas'),
            ('CTR025', 'Refrigerador'),
            ('CTR026', 'Revolvedora'),
            ('CTR027', 'Semicaja'),
            ('CTR028', 'Tanque'),
            ('CTR029', 'Tolva'),
            ('CTR031', 'Volteo'),
            ('CTR032', 'Volteo Desmontable'),
        ],
        string='Sub Type')
