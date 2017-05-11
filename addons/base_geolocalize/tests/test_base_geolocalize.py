# -*- coding: utf-8 -*-
#
#    Authors: Laurent Mignon
#    Copyright (c) 2015 Acsone SA/NV (http://www.acsone.eu)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import openerp.tests.common as common


class TestPartnerGeolocalize(common.TransactionCase):

    def test_geo_localize(self):
        vals = {
            'name': 'Partner Project',
            'street': 'Rue de la drève 3',
            'country_id': self.env.ref('base.be').id,
            'zip': '4052',
        }
        partner_id = self.env['res.partner'].create(vals)
        partner_id.name = 'Other Partner'
        partner_id.geo_localize()
        self.assertAlmostEqual(
            partner_id.partner_latitude, 50.55149, 5,
            'Latitude Should be equals')
        self.assertAlmostEqual(
            partner_id.partner_longitude, 5.66744, 5,
            'Longitude Should be equals')
        domain = [('id', '=', partner_id.id)]
        partner_id.unlink()
        self.assertFalse(
            self.env['res.partner'].search(domain),
            'Should not have this partner anymore')
