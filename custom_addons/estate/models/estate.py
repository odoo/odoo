from odoo import models, fields
from datetime import datetime, timedelta

class RealEstate(models.Model):
    _name = "estate"
    _description = "Real Estate"

#    create_uid = fields.Many2one('res.users', string='Create User', ondelete='SET NULL')
#    write_uid = fields.Many2one('res.users', string='Write User', ondelete='SET NULL')

    name = fields.Char(default="Desconocido",string='Titulo', required=True)
    description = fields.Text(string='Descripcion')
    postcode = fields.Char(string='Codigo Postal')
    active = fields.Boolean(string='Activo', default=True)
    date_availability = fields.Date(string='Fecha de disponibilidad', default=lambda self: (datetime.today() + timedelta(days=90)).strftime('%Y-%m-%d'), copy=False)  # Fecha de disponibilidad predeterminada en 3 meses
    expected_price = fields.Float(string='Precio Esperado', required=True)
    selling_price = fields.Float(string='Precio de Venta', readonly=True, copy=False)
    bedrooms = fields.Integer(string='Numero de Habitaciones', default=2)
    living_area = fields.Integer(string='Sala de Estar')
    facades = fields.Integer(string='Fachadas')
    garage = fields.Boolean(string='Garage')
    garden = fields.Boolean(string='Jardin')
    garden_area = fields.Integer(string='Zona de Jardin')
    garden_orientation = fields.Selection([('norte', 'Norte'), ('sur', 'Sur'), ('este', 'Este'), ('oeste', 'Oeste')], string='Orientacion del Jardin')
    state = fields.Selection([('nuevo', 'Nuevo'), ('oferta_recibida', 'Oferta recibida'), ('oferta_aceptada', 'Oferta aceptada'), ('vendido', 'Vendido'), ('cancelado', 'Cancelado')], string='Estado', default='nuevo', required=True)

