# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies (<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
################################################################################
from odoo import models, fields


class DynamicFieldWidgets(models.Model):
    """We can't filter a selection field dynamically so when we select a
    field its widgets also need to change according to the selected field
    type, we can't do it by a 'selection' field, need a 'Many2one' field.
    """

    _name = 'dynamic.field.widgets'
    _rec_name = 'description'
    _description = 'Field Widgets'

    name = fields.Char(string="Name", help='Name of the record')
    description = fields.Char(string="Description", help='Description given to '
                                                         'the record')
