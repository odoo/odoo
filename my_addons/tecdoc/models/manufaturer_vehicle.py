# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TecdocManufacturer(models.Model):
    _name = 'tecdoc.manufacturer'
    _description = 'Manufacturer'
    _order = 'her_nr asc'

    her_nr = fields.Integer("ID Tecdoc")
    hkz = fields.Char("Short Code", required=True)
    name = fields.Char("Manufacturer", required=True)
    vms_id = fields.One2many('tecdoc.vehicle.model.series',
                             'manufacturer_id',
                             string="Vehicle Model Series")
    logo = fields.Binary('Logo')


class TecdocVehicleModelSeries(models.Model):
    _name = 'tecdoc.vehicle.model.series'
    _description = 'Vehicle Model Series'
    _order = 'kmod_nr, sort_nr asc'

    kmod_nr = fields.Integer("Kmod ID", required=True)
    name = fields.Char("Serial Model Name", required=True)
    sort_nr = fields.Integer("Sorting Key")
    from_year = fields.Date('Model Year from')
    to_year = fields.Date('Model Year to')
    manufacturer_id = fields.Many2one('tecdoc.manufacturer')
    model_picture = fields.Binary("Picture")
    vts_id = fields.One2many('tecdoc.vehicles.types',
                             'vehicle_model_id',
                             string='Vehicle Types')


class TecdocVehicleTypes(models.Model):
    _name = 'tecdoc.vehicles.types'
    _description = 'Vehicle Types'
    _order = 'ktyp_nr, sort_nr asc'

    def _key_engine_type(self, key):
        models = self.env['tecdoc.tables.entries'].search([('tab_nr', '=', key)])
        return [(x.key, x.name) for x in models]

    ktyp_nr = fields.Integer("Ktyp ID", required=True)
    name = fields.Char("Vehicle Type Name")
    kmod_nr = fields.Integer("Model Series")
    sort_nr = fields.Integer("Sorting Key")
    bjvon = fields.Date('Model Year from')
    bjbis = fields.Date('Model Year to')
    kw = fields.Integer("kW")
    ps = fields.Integer("HP")
    ccm_steuer = fields.Integer("Engine capacity in cc (taxation value)")
    ccm_tech = fields.Integer("Engine capacity in cc (technical value)")
    lit = fields.Float("Engine capacity in litre (99V99)")
    zyl = fields.Integer("Number of cylinders")
    tueren = fields.Integer("Number of doors")
    tank_inhalt = fields.Integer("Fuel tank capacity")
    spannung = fields.Integer("Main current voltage")
    abs = fields.Selection([('0', "No"), ('1', "Yes"), ('2', "Optional"), ('9', "Unknown")],
                           "ABS", default='9')
    asr = fields.Selection([('0', "No"), ('1', "Yes"), ('2', "Optional"), ('9', "Unknown")],
                           "ASR", default='9')
    mot_art = fields.Selection(lambda self: self._key_engine_type('080'),
                               "Engine type")
    kraftstoffaufbereitungsprinzip = fields.Selection(lambda self: self._key_engine_type('097'),
                                                      "Fuel mixture formation")
    antr_art = fields.Selection(lambda self: self._key_engine_type('082'),
                                "Drive type")
    brems_art = fields.Selection(lambda self: self._key_engine_type('083'),
                                 "Brake type")
    brems_sys = fields.Selection(lambda self: self._key_engine_type('084'),
                                 "Brake system")
    ventile_brennraum = fields.Integer("Number of valves")
    kr_stoff_art = fields.Selection(lambda self: self._key_engine_type('182'),
                                    "Fuel type")
    kat_art = fields.Selection(lambda self: self._key_engine_type('089'),
                               "Catalyst converter type")
    getr_art = fields.Selection(lambda self: self._key_engine_type('085'),
                                "Transmission type")
    aufbau_art = fields.Selection(lambda self: self._key_engine_type('086'),
                                  "Body type")
    vehicle_model_id = fields.Many2one('tecdoc.vehicle.model.series')
