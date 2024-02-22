from odoo import models, fields
from datetime import datetime, timedelta

class RealEstate(models.Model):
    _name = "estate"
    _description = "Real Estate"

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
    type_id = fields.Many2one('estate_type', string='Tipo')
    user_id = fields.Many2one('res.users', string='Vendedor', default=lambda self: self.env.user) #Verificar parametros a agregar
    partner_id = fields.Many2one('res.partner', string='Comprador', copy=False) #Verificar parametros a agregar
    tag_ids = fields.Many2many('estate_tag', string='Tags')