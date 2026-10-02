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
from xlrd.xlsx import ET

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DynamicFields(models.Model):
    """Class DynamicFields to create fields dynamically to any model"""
    _name = 'dynamic.fields'
    _rec_name = 'field_description'
    _description = 'Custom Dynamic Fields'
    _inherit = 'ir.model.fields'

    @api.model
    def get_possible_field_types(self):
        """Return all available field types other than 'one2many' and
        'reference' fields."""
        field_list = sorted((key, key) for key in fields.MetaField.by_type)
        field_list.remove(('one2many', 'one2many'))
        field_list.remove(('reference', 'reference'))
        return field_list

    position_field_id = fields.Many2one('ir.model.fields',
                                        string='Field Name',
                                        help='Position Field Name',
                                        required=True,
                                        ondelete='cascade')
    position = fields.Selection([('before', 'Before'),
                                 ('after', 'After')], string='Position',
                                help='position of the newly created field',
                                required=True)
    model_id = fields.Many2one('ir.model', string='Model',
                               required=True,
                               index=True, ondelete='cascade',
                               help="The model this field belongs to")
    ref_model_id = fields.Many2one('ir.model', string='Model',
                                   index=True, help='Reference model of the '
                                                    'relational field')
    selection_field = fields.Char(string="Selection Options",
                                  help='Selection options for field')
    rel_field_id = fields.Many2one('ir.model.fields',
                                   string='Related Field', help='Related field')
    field_type = fields.Selection(selection='get_possible_field_types',
                                  string='Field Type',
                                  help='Field type of newly created field',
                                  required=True)
    ttype = fields.Selection(string="Field Type", related='field_type',
                             help='Field type')
    widget_id = fields.Many2one('dynamic.field.widgets',
                                string='Widget',
                                help='Widget of the newly selected field')
    groups = fields.Many2many('res.groups',
                              'employee_dynamic_fields_group_rel',
                              'field_id', 'group_id',
                              string='Groups', help='Groups')
    is_extra_features = fields.Boolean(string="Show Extra Properties",
                                       help='Show Extra Properties of newly '
                                            'field')
    created_from_id = fields.Many2one('ir.ui.view',
                                      help='Created form view id for the field',
                                      string='Dynamic created form view')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('form', 'Field Created'),
        ('tree', 'Added in Tree View'),
    ], string='Status', index=True, readonly=True, tracking=True,
        copy=False, default='draft',
        help='Record Status')

    form_view_id = fields.Many2one('ir.ui.view',
                                   string="Form View ID",
                                   help='Form View ID',
                                   required=True)
    form_view_inherit_id = fields.Char(string="Form View Inherit Id",
                                       help="Form View Inherit Id",
                                       related='form_view_id.xml_id')
    is_add_field_in_tree = fields.Boolean(string="Add Field to the Tree View",
                                          help="Add newly created Field to "
                                               "the Tree View")
    tree_view_id = fields.Many2one('ir.ui.view',
                                   string="Tree View ID", help='Tree View ID')
    tree_view_inherit_id = fields.Char(string="Tree View Inherit Id",
                                       help='Tree View Inherit Id',
                                       readonly=True,
                                       related='tree_view_id.xml_id')
    tree_field_position = fields.Selection([('before', 'Before'),
                                            ('after', 'After')],
                                           string='Position',
                                           help='Tree field position to the '
                                                'selected tree field')
    tree_field_ids = fields.Many2many('ir.model.fields',
                                      string='Tree View Fields',
                                      compute='_compute_tree_field_ids',
                                      help='Domain field for tree view fields')
    tree_view_field_id = fields.Many2one('ir.model.fields',
                                         string='Tree View Field',
                                         domain="[('id', 'in', "
                                                "tree_field_ids)]",
                                         help='Select a tree view field for '
                                              'position of newly created '
                                              'field in the tree view')
    is_tree_view_toggle = fields.Boolean(string='Visible in tree view',
                                         help='Enable to toggle view the newly '
                                              'created view in selected tree '
                                              'view')
    created_tree_view_id = fields.Many2one('ir.ui.view',
                                           help='Dynamic Created tree view id',
                                           string='Dynamic Tree view id')

    @api.depends('tree_view_id')
    def _compute_tree_field_ids(self):
        """Compute function to find the tree view fields of selected tree view
        in field tree_view_id"""
        for rec in self:
            if rec.tree_view_id:
                field_list = []
                if rec.tree_view_id.xml_id:
                    tree_fields = ET.fromstring(self.env.ref(
                        rec.tree_view_id.xml_id).arch).findall(".//field")
                    for field in tree_fields:
                        field_list.append(field.get('name'))
                inherit_id = rec.tree_view_id.inherit_id \
                    if rec.tree_view_id.inherit_id else False
                while inherit_id:
                    if inherit_id.xml_id:
                        tree_fields = ET.fromstring(self.env.ref(
                            inherit_id.xml_id).arch).findall(".//field")
                        for field in tree_fields:
                            field_list.append(field.get('name'))
                    inherit_id = inherit_id.inherit_id \
                        if inherit_id.inherit_id else False
                self.tree_field_ids = self.env['ir.model.fields'].search(
                    [('model_id', '=', self.model_id.id),
                     ('name', 'in', field_list)])
            else:
                rec.tree_field_ids = False

    def action_create_dynamic_fields(self):
        """Function create Dynamic field"""
        self.write({'status': 'form'})
        if self.field_type == 'monetary' and not self.env[
            'ir.model.fields'].sudo().search([('model', '=', self.model_id.id),
                                              ('name', '=', 'currency_id')]):
            self.env['ir.model.fields'].sudo().create({
                'name': 'x_currency_id',
                'field_description': 'Currency',
                'model_id': self.model_id.id,
                'ttype': 'many2one',
                'relation': 'res.currency',
                'is_dynamic_field': True
            })
        self.env['ir.model.fields'].sudo().create({
            'name': self.name,
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
            'is_dynamic_field': True
        })
        inherit_form_view_name = (str(
            self.form_view_id.name) + ".inherit.dynamic.custom." +
                                  str(self.field_description) + ".field")
        xml_id = self.form_view_id.xml_id
        inherit_id = self.env.ref(xml_id)
        arch_base = _('<?xml version="1.0"?>'
                      '<data>'
                      '<field name="%s" position="%s">'
                      '<field name="%s"/>'
                      '</field>'
                      '</data>') % (self.position_field_id.name,
                                    self.position, self.name)
        if self.widget_id:
            arch_base = _('<?xml version="1.0"?>'
                          '<data>'
                          '<field name="%s" position="%s">'
                          '<field name="%s" widget="%s"/>'
                          '</field>'
                          '</data>') % (self.position_field_id.name,
                                        self.position, self.name,
                                        self.widget_id.name)
        self.created_from_id = self.env['ir.ui.view'].sudo().create({
            'name': inherit_form_view_name,
            'type': 'form',
            'model': self.model_id.model,
            'mode': 'extension',
            'inherit_id': inherit_id.id,
            'arch_base': arch_base,
            'active': True
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_add_field_to_tree_view(self):
        """Function to add created dynamic field to selected tree view"""
        if self.is_add_field_in_tree:
            inherit_tree_view_name = str(
                self.tree_view_id.name) + ".inherit.dynamic.custom" + \
                                     str(self.field_description) + ".field"
            optional = "show" if self.is_tree_view_toggle else "hide"
            tree_view_arch_base = (_(f'''
                    <data>
                        <xpath expr="//field[@name='{self.tree_view_field_id.name}']" position="{self.tree_field_position}">
                            <field name="{self.name}" optional="{optional}"/>
                        </xpath>
                    </data>'''))
            self.created_tree_view_id = self.env['ir.ui.view'].sudo().create({
                'name': inherit_tree_view_name,
                'type': 'tree',
                'model': self.model_id.model,
                'mode': 'extension',
                'inherit_id': self.tree_view_id.id,
                'arch_base': tree_view_arch_base,
                'active': True})
            self.write({'status': 'tree'})
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            raise ValidationError(
                _('Error! Please select the boolean field Add Field to the '
                  'Tree View.'))

    @api.onchange('model_id', 'is_add_field_in_tree')
    def set_domain(self):
        """Return the fields that currently present in the form"""
        form_view_ids = self.model_id.view_ids.filtered(
            lambda x: x.type == 'form' and x.mode == 'primary')
        tree_view_ids = self.model_id.view_ids.filtered(
            lambda x: x.type == 'tree' and x.mode == 'primary')
        fields_domain = self.env['ir.model.fields'].sudo().search([
            ('model', '=', self.model_id.model)])
        field_list = []
        for rec in fields_domain:
            for field in rec:
                field_list.append(field.id)
        return {'domain': {
            'form_view_id': [('id', 'in', form_view_ids.ids)],
            'tree_view_id': [('id', 'in', tree_view_ids.ids)],
            'position_field_id': [('id', 'in', field_list)]
        }}

    @api.onchange('field_type')
    def onchange_field_type(self):
        """Function to determine domain for field widget"""
        if self.field_type:
            if self.field_type == 'binary':
                return {'domain': {'widget_id': [('name', '=', 'image')]}}
            elif self.field_type == 'many2many':
                return {'domain': {'widget_id': [
                    ('name', 'in', ['many2many_tags', 'binary'])]}}
            elif self.field_type == 'selection':
                return {'domain': {
                    'widget_id': [('name', 'in', ['radio', 'priority'])]}}
            elif self.field_type == 'float':
                return {'domain': {'widget_id': [('name', '=', 'monetary')]}}
            elif self.field_type == 'many2one':
                return {'domain': {'widget_id': [('name', '=', 'selection')]}}
            else:
                return {'domain': {'widget_id': [('id', '=', False)]}}
        return {'domain': {'widget_id': [('id', '=', False)]}}

    def unlink(self):
        """Unlink function to make the created tree view and from view to
        inactive"""
        if self.created_from_id:
            self.created_from_id.active = False
        if self.created_tree_view_id:
            self.created_tree_view_id.active = False
        res = super(DynamicFields, self).unlink()
        return res
