# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2020-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author:  Ajmal JK (<https://www.cybrosys.com>)
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

import xml.etree.ElementTree as xee
from odoo import api, models, fields, _


class ProductDynamicFields(models.TransientModel):
    _name = 'product.dynamic.fields'
    _description = 'Dynamic Fields'
    _inherit = 'ir.model.fields'

    @api.model
    def get_possible_field_types(self):
        """Return all available field types other than 'one2many' and 'reference' fields."""
        field_list = sorted((key, key) for key in fields.MetaField.by_type)
        field_list.remove(('one2many', 'one2many'))
        field_list.remove(('reference', 'reference'))
        return field_list

    def set_domain(self):
        """Return the fields that currently present in the form"""
        view_id = self.env.ref('product.product_template_only_form_view')
        view_arch = str(view_id.arch_base)
        doc = xee.fromstring(view_arch)
        field_list = []
        for tag in doc.findall('.//field'):
            field_list.append(tag.attrib['name'])
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'product.template')])
        return [('model_id', '=', model_id.id), ('state', '=', 'base'), ('name', 'in', field_list)]

    def _set_default(self):
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'product.template')])
        return [('id', '=', model_id.id)]

    def create_fields(self):
        self.env['ir.model.fields'].sudo().create({'name': self.name,
                                                   'field_description': self.field_description,
                                                   'model_id': self.model_id.id,
                                                   'ttype': self.field_type,
                                                   'relation': self.ref_model_id.model,
                                                   'required': self.required,
                                                   'index': self.index,
                                                   'store': self.store,
                                                   'help': self.help,
                                                   'readonly': self.readonly,
                                                   'selection': self.selection_field,
                                                   'copied': self.copied,
                                                   'is_dynamic': True
                                                   })
        inherit_id = self.env.ref('product.product_template_only_form_view')
        arch_base = _('<?xml version="1.0"?>'
                      '<data>'
                      '<field name="%s" position="%s">'
                      '<field name="%s"/>'
                      '</field>'
                      '</data>') % (self.position_field.name, self.position, self.name)
        if self.widget:
            arch_base = _('<?xml version="1.0"?>'
                          '<data>'
                          '<field name="%s" position="%s">'
                          '<field name="%s" widget="%s"/>'
                          '</field>'
                          '</data>') % (self.position_field.name, self.position, self.name, self.widget.name)

        self.env['ir.ui.view'].sudo().create({'name': 'product.dynamic.fields',
                                              'type': 'form',
                                              'model': 'product.template',
                                              'mode': 'extension',
                                              'inherit_id': inherit_id.id,
                                              'arch_base': arch_base,
                                              'active': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    position_field = fields.Many2one('ir.model.fields', string='Field Name',
                                     domain=set_domain, required=True)
    position = fields.Selection([('before', 'Before'),
                                 ('after', 'After')], string='Position', required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, index=True, ondelete='cascade',
                               help="The model this field belongs to", domain=_set_default)
    ref_model_id = fields.Many2one('ir.model', string='Model', index=True)
    # In odoo 13 the field 'selection' is deprecated, so adding a new field to get the selection values.
    selection_field = fields.Char(string="Selection Options")
    rel_field = fields.Many2one('ir.model.fields', string='Related Field')
    field_type = fields.Selection(selection='get_possible_field_types', string='Field Type', required=True)
    ttype = fields.Selection(string="Field Type", related='field_type')
    widget = fields.Many2one('field.widgets', string='Widget')
    groups = fields.Many2many('res.groups', 'product_dynamic_fields_group_rel', 'field_id', 'group_id')
    extra_features = fields.Boolean(string="Show Extra Properties")

    @api.depends('field_type')
    @api.onchange('field_type')
    def onchange_field_type(self):
        if self.field_type:
            if self.field_type == 'binary':
                return {'domain': {'widget': [('name', '=', 'image')]}}
            elif self.field_type == 'many2many':
                return {'domain': {'widget': [('name', 'in', ['many2many_tags', 'binary'])]}}
            elif self.field_type == 'selection':
                return {'domain': {'widget': [('name', 'in', ['radio', 'priority'])]}}
            elif self.field_type == 'float':
                return {'domain': {'widget': [('name', '=', 'monetary')]}}
            elif self.field_type == 'many2one':
                return {'domain': {'widget': [('name', '=', 'selection')]}}
            else:
                return {'domain': {'widget': [('id', '=', False)]}}
        return {'domain': {'widget': [('id', '=', False)]}}
