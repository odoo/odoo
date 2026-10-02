# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class WebsiteCustomerPortal(CustomerPortal):
    """Class for inheriting _prepare_home_portal_values function """

    def _prepare_home_portal_values(self, counters):
        """Function for updating the counts of vaccinations, lab tests and op
        of portal user"""
        values = super()._prepare_home_portal_values(counters)
        if 'vaccination_count' in counters:
            values['vaccination_count'] = request.env[
                'hospital.vaccination'].sudo(). \
                search_count([('patient_id.user_ids', '=', request.uid)])
        if 'lab_test_count' in counters:
            values['lab_test_count'] = request.env['patient.lab.test'].sudo(). \
                search_count([('patient_id.user_ids', '=', request.uid)])
        if 'op_count' in counters:
            values['op_count'] = request.env[
                'hospital.outpatient'].sudo().search_count(
                [('patient_id.user_ids', '=', request.uid)])
        return values
