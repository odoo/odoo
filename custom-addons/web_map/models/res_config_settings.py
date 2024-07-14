# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models,api, _
from odoo.exceptions import UserError
import requests
from odoo.http import request


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    map_box_token = fields.Char(config_parameter='web_map.token_map_box',string = 'Token Map Box', help='Necessary for some functionalities in the map view', copy=True, default='', store=True)

    @api.onchange('map_box_token')
    def _onchange_map_box_token(self):
        if not self.map_box_token:
            return
        map_box_token = self.env['ir.config_parameter'].get_param('web_map.token_map_box')
        if self.map_box_token == map_box_token:
            return

        url = 'https://api.mapbox.com/directions/v5/mapbox/driving/-73.989%2C40.733%3B-74%2C40.733'
        headers = {
            'referer': request.httprequest.headers.environ.get('HTTP_REFERER'),
        }
        params = {
            'access_token': self.map_box_token,
            'steps': 'true',
            'geometries': 'geojson',
        }
        try:
            result = requests.head(url=url, headers=headers, params=params, timeout=5)
            error_code = result.status_code
        except requests.exceptions.RequestException:
            error_code = 500
        if error_code == 200:
            return
        self.map_box_token = ''
        if error_code == 401:
            return {'warning': {'message': _('The token input is not valid')}}
        elif error_code == 403:
            return {'warning': {'message': _('This referer is not authorized')}}
        elif error_code == 500:
            return {'warning': {'message': _('The MapBox server is unreachable')}}
