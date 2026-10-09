# -*- coding: utf-8 -*-

import requests
import json
import logging
import time
from odoo import api, fields, models, tools, _

from .map import Foliummap
from odoo.exceptions import UserError
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from datetime import datetime

_logger = logging.getLogger(__name__)


class MapStorage(models.Model):
    _name = 'map_storage'
    _description = 'Module to locally store folium html. Hide views after development'

    name = fields.Char(default='Map Storage')
    map_html = fields.Text("Map HTML")
    last_updated = fields.Datetime(string='Map Update on')

    def update_map_html(self, location:list=[39.8283, -98.5795], zoom=4, skip_location=False, limit_records:int=False):
        sale_orders = self.env['sale.order'].search([], order='date_order desc', limit=limit_records or 2000)
        folium_instance = Foliummap
        map_html = folium_instance.create_folium_map(folium_instance, self, sale_records=sale_orders, location=location, zoom=zoom, skip_location=skip_location)
        map_record = self.env['map_storage'].search([], limit=1)
        if not map_record:     
            raise ValueError("No map record found")
        map_record.write({'map_html':map_html,'last_updated':datetime.now()})
        self.env['map_storage'].create({'map_html': map_html})
        map_record.invalidate_recordset()
        _logger.info(f"returning map_record.id: {map_record.id}")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Open Map View',
            'res_model': 'map_storage',  
            'view_mode': 'form',
            'res_id': map_record.id,  
            'target': 'current', 
        }

    def cron_update_map_html(self):
        """Method to be called by the cron job."""
        self.update_map_html()

class ResPartner(models.Model):
    _inherit = 'res.partner'

    gps_coordinates = fields.Char(string='GPS Coordinates', compute="_compute_gps_coordinates")
    latitude = fields.Float(string='Latitude')
    longitude = fields.Float(string='Longitude')

    @api.onchange('street','city','state_id')
    def _onchange_street_get_coordinates(self):
        if self.street and self.city and self.state_id:
            street = self.street or ""
            city = self.city or ""
            state = self.state_id.name if self.state_id else ""
            address = f"{street} {city} {state}"
            geolocator = Nominatim(user_agent="myGeocodeApp_v1")
            try:
                location = geolocator.geocode(address, timeout=10) 
                if location:
                    _logger.info(f"location found for {address}! - {location.latitude, location.longitude}")
                    self.latitude = location.latitude
                    self.longitude = location.longitude
                    self.write({
                        'latitude': location.latitude,
                        'longitude': location.longitude
                    })
                else:
                    _logger.warning(f"location not found for address {address} ")
            except Exception as e:
                _logger.warning(f"error at {e}")

    @api.onchange('street','city','state_id')
    def _compute_gps_coordinates(self):
        if self.latitude and self.longitude:
            self.gps_coordinates = f"{self.latitude}, {self.longitude}"
        else: self.gps_coordinates = "GPS Not Available"

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    latitude = fields.Float(string='Latitude', compute="_compute_gps")
    longitude = fields.Float(string='Longitude', compute="_compute_gps")
    map_html = fields.Text("Map HTML", help="Store single customer's map", compute='_compute_map_location')

    @api.depends('partner_id.latitude', 'partner_id.longitude')
    def _compute_gps(self):
        for record in self:
            if record.partner_id:
                record.latitude = record.partner_id.latitude
                record.longitude = record.partner_id.longitude
            else:
                record.latitude = 0.0
                record.longitude = 0.0

    @api.depends('partner_id.street', 'partner_id.longitude')
    def _compute_map_location(self):
        """
        Create map for single sale order record
        """
        for record in self:
            location = [record.latitude, record.longitude]
            _logger.warning(f"moving map to {location}")
            folium_instance = Foliummap
            map_html = folium_instance.create_folium_map(folium_instance, self, sale_records=record, location=location, zoom=18, skip_location=True)
            record.map_html = map_html
