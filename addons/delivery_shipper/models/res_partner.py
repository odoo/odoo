from odoo import models, fields, api


# Need to Enable enforce cities
class Partner(models.Model):
    _inherit = 'res.partner'
    district_id = fields.Many2one(
        comodel_name="district",
        string="District ID",
        domain="[('city_id', '=', city_id)]",
    )
    area_id = fields.Many2one(
        comodel_name="area",
        string="Area ID",
        domain="[('district_id', '=', district_id)]",
    )
    shipper_complete_address = fields.Char(compute='_compute_shipper_complete_address')

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            self.zip = self.city_id.zipcode
            self.state_id = self.city_id.state_id
            self.district_id = False
            self.area_id = False
        elif self._origin:
            self.city = False
            self.zip = False
            self.state_id = False
            self.district_id = False
            self.area_id = False

    @api.depends('street', 'zip', 'city', 'district_id', 'area_id', 'country_id')
    def _compute_shipper_complete_address(self):
        for record in self:
            record.shipper_complete_address = ''
            if record.street:
                record.shipper_complete_address += record.street + ', '
            if record.state_id:
                record.shipper_complete_address += record.state_id.name + ', '
            if record.city:
                record.shipper_complete_address += record.city + ', '
            if record.district_id:
                record.shipper_complete_address += record.district_id.name + ', '
            if record.area_id:
                record.shipper_complete_address += record.area_id.name + ', '
            if record.country_id:
                record.shipper_complete_address += record.country_id.name + ', '
            if record.zip:
                record.shipper_complete_address += record.zip
            record.shipper_complete_address = record.shipper_complete_address.strip().strip(',')


class District(models.Model):
    _name = 'district'
    _description = 'District'
    name = fields.Char(string="District Name")
    city_id = fields.Many2one(comodel_name="res.city", string="City ID")


class Area(models.Model):
    _name = 'area'
    _description = 'Area'
    name = fields.Char(string="Area Name")
    district_id = fields.Many2one(comodel_name="district", string="District ID")
