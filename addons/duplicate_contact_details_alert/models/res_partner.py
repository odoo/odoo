# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2022-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import ast


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals):
        unique_contact_ids = self.env[
            'ir.config_parameter'].sudo().get_param(
            'duplicate_contact_details_alert.unique_contact_ids')
        if unique_contact_ids:
            fields_list = ast.literal_eval(unique_contact_ids)
            for x in fields_list:
                contact_fields = self.env['ir.model.fields'].browse(x)
                field_vals = contact_fields.name
                if vals.get(field_vals):
                    partner = self.env['res.partner'].search(
                        [(field_vals, '=', vals.get(field_vals))], limit=1)
                    if partner:
                        raise ValidationError(
                            _("The %s is already"
                              " used for contact %s.") %
                            (contact_fields.name, partner.name))
            else:
                res = super(ResPartner, self).create(vals)
                return res
        else:
            res = super(ResPartner, self).create(vals)
            return res

    def write(self, vals):
        unique_contact_ids = self.env[
            'ir.config_parameter'].sudo().get_param(
            'duplicate_contact_details_alert.unique_contact_ids')
        if unique_contact_ids:
            fields_list = ast.literal_eval(unique_contact_ids)
            for x in fields_list:
                contact_fields = self.env['ir.model.fields'].browse(x)
                field_vals = contact_fields.name
                if vals.get(field_vals):
                    partner = self.env['res.partner'].search(
                        [(field_vals, '=', vals.get(field_vals))], limit=1)
                    if partner:
                        raise ValidationError(
                            _("The %s is already"
                              " used for contact %s.") %
                            (contact_fields.name, partner.name))
            else:
                res = super(ResPartner, self).write(vals)
                return res

        else:
            res = super(ResPartner, self).write(vals)
            return res
