# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import collections
from ast import literal_eval
from collections import defaultdict
from lxml import etree
from random import randint

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG


class WorksheetTemplate(models.Model):
    _name = 'worksheet.template'
    _description = 'Worksheet Template'
    _order = 'sequence, name'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer()
    worksheet_count = fields.Integer(compute='_compute_worksheet_count', compute_sudo=True)
    model_id = fields.Many2one('ir.model', ondelete='cascade', readonly=True, domain=[('state', '=', 'manual')])
    action_id = fields.Many2one('ir.actions.act_window', readonly=True)
    company_ids = fields.Many2many('res.company', string='Companies', domain=lambda self: [('id', 'in', self.env.companies.ids)])
    report_view_id = fields.Many2one('ir.ui.view', domain=[('type', '=', 'qweb')], readonly=True)
    color = fields.Integer('Color', default=_get_default_color)
    active = fields.Boolean(default=True)
    res_model = fields.Char('Host Model', help="The model that is using this template")

    def _compute_worksheet_count(self):
        for record in self:
            record.worksheet_count = record.model_id and self.env[record.model_id.model].search_count([]) or 0

    @api.constrains('report_view_id', 'model_id')
    def _check_report_view_type(self):
        for worksheet_template in self:
            if worksheet_template.model_id and worksheet_template.report_view_id:
                if worksheet_template.report_view_id.type != 'qweb':
                    raise ValidationError(_('The template to print this worksheet template should be a QWeb template.'))

    @api.constrains('res_model')
    def _check_res_model_exists(self):
        res_models = self.mapped('res_model')
        ir_model_names = [res['model'] for res in self.env['ir.model'].sudo().search_read([('model', 'in', res_models)], ['model'])]
        if any(model_name not in ir_model_names for model_name in res_models):
            raise ValidationError(_('The host model name should be an existing model.'))

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        if not self.env.context.get('worksheet_no_generation'):
            for template in templates:
                template._generate_worksheet_model()
        return templates

    def write(self, vals):
        old_company_ids = self.company_ids
        res = super().write(vals)
        if 'company_ids' in vals and self.company_ids:
            update_company_ids = old_company_ids - self.company_ids
            template_dict = defaultdict(lambda: self.env['worksheet.template'])
            for template in self:
                template_dict[template.res_model] |= template
            for res_model, templates in template_dict.items():
                for model, name in self._get_models_to_check_dict()[res_model]:
                    records = self.env[model].search([('worksheet_template_id', 'in', templates.ids)])
                    for record in records:
                        if record.company_id not in record.worksheet_template_id.company_ids:
                            if update_company_ids:
                                company_names = ', '.join(update_company_ids.mapped('name'))
                                raise UserError(_("Unfortunately, you cannot unlink this worksheet template from %s because the template is still connected to tasks within the company.", company_names))
                            else:
                                company_names = ', '.join(record.worksheet_template_id.company_ids.mapped('name'))
                                raise UserError(_("You can't restrict this worksheet template to '%s' because it's still connected to tasks in '%s' (and potentially other companies). Please either unlink those tasks from this worksheet template, "
                                                  "move them to a project for the right company, or keep this worksheet template open to all companies.", company_names, record.company_id.name))
        return res

    def unlink(self):
        # When uninstalling module, let the ORM take care of everything. As the
        # xml ids are correctly generated, all data will be properly removed.
        if self.env.context.get(MODULE_UNINSTALL_FLAG):
            return super().unlink()

        # When manual deletion of worksheet, we need to handle explicitly the removal of depending data
        models_ids = self.mapped('model_id.id')
        self.env['ir.ui.view'].search([('model', 'in', self.mapped('model_id.model'))]).unlink()  # backend views (form, pivot, ...)
        self.mapped('report_view_id').unlink()  # qweb templates
        self.env['ir.model.access'].search([('model_id', 'in', models_ids)]).unlink()
        x_name_fields = self.env['ir.model.fields'].search([('model_id', 'in', models_ids), ('name', '=', 'x_name')])
        x_name_fields.write({'related': False})  # we need to manually remove relation to allow the deletion of fields
        self.env['ir.rule'].search([('model_id', 'in', models_ids)]).unlink()
        self.mapped('action_id').unlink()
        # context needed to avoid "manual" removal of related fields
        self.mapped('model_id').with_context(**{MODULE_UNINSTALL_FLAG: True}).unlink()

        return super(WorksheetTemplate, self.exists()).unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _("%s (copy)", self.name)

        # force no model
        default['model_id'] = False

        template = super(WorksheetTemplate, self.with_context(worksheet_no_generation=True)).copy(default)
        template._generate_worksheet_model()
        return template

    def _generate_worksheet_model(self):
        self.ensure_one()
        res_model = self.res_model.replace('.', '_')
        name = 'x_%s_worksheet_template_%d' % (res_model, self.id)

        # create access rights and rules
        if not hasattr(self, f'_get_{res_model}_manager_group'):
            raise NotImplementedError(f'Method _get_{res_model}_manager_group not implemented on {res_model}')
        if not hasattr(self, f'_get_{res_model}_user_group'):
            raise NotImplementedError(f'Method _get_{res_model}_user_group not implemented on {res_model}')
        if not hasattr(self, f'_get_{res_model}_access_all_groups'):
            raise NotImplementedError(f'Method _get_{res_model}_access_all_groups not implemented on {res_model}')

        # while creating model it will initialize the init_models method from create of ir.model
        # and there is related field of model_id in mail template so it's going to recursive loop while recompute so used flush
        self.env.flush_all()

        # Generate xml ids for some records: views, actions and models. This will let the ORM handle
        # the module uninstallation (removing all data belonging to the module using their xml ids).
        # NOTE: this is not needed for ir.model.fields, ir.model.access and ir.rule, as they are in
        # delete 'cascade' mode, so their database entries will removed (no need their xml id).
        module_name = getattr(self, f'_get_{res_model}_module_name')()
        xid_values = []
        model_counter = collections.Counter()
        def register_xids(records):
            for record in records:
                model_counter[record._name] += 1
                xid_values.append({
                    'name': "{}_{}_{}".format(
                        name,
                        record._name.replace('.', '_'),
                        model_counter[record._name],
                    ),
                    'module': module_name,
                    'model': record._name,
                    'res_id': record.id,
                    'noupdate': True,
                })
            return records

        # generate the ir.model (and so the SQL table)
        model = register_xids(self.env['ir.model'].sudo().create({
            'name': self.name,
            'model': name,
            'field_id': self._prepare_default_fields_values() + [
                (0, 0, {
                    'name': 'x_name',
                    'field_description': 'Name',
                    'ttype': 'char',
                    'related': 'x_%s_id.name' % res_model,
                }),
            ]
        }))

        self.env['ir.model.access'].sudo().create([{
            'name': name + '_manager_access',
            'model_id': model.id,
            'group_id': getattr(self, '_get_%s_manager_group' % res_model)().id,
            'perm_create': True,
            'perm_write': True,
            'perm_read': True,
            'perm_unlink': True,
        }, {
            'name': name + '_user_access',
            'model_id': model.id,
            'group_id': getattr(self, '_get_%s_user_group' % res_model)().id,
            'perm_create': True,
            'perm_write': True,
            'perm_read': True,
            'perm_unlink': True,
        }])
        self.env['ir.rule'].create([{
            'name': name + '_own',
            'model_id': model.id,
            'domain_force': "[('create_uid', '=', user.id)]",
            'groups': [(6, 0, [getattr(self, '_get_%s_user_group' % res_model)().id])]
        }, {
            'name': name + '_all',
            'model_id': model.id,
            'domain_force': [(1, '=', 1)],
            'groups': [(6, 0, getattr(self, '_get_%s_access_all_groups' % res_model)().ids)],
        }])

        # create the view to extend by 'studio' and add the user custom fields
        __, __, search_view = register_xids(self.env['ir.ui.view'].sudo().create([
            self._prepare_default_form_view_values(model),
            self._prepare_default_tree_view_values(model),
            self._prepare_default_search_view_values(model)
        ]))
        action = register_xids(self.env['ir.actions.act_window'].sudo().create({
            'name': 'Worksheets',
            'res_model': model.model,
            'search_view_id': search_view.id,
            'context': {
                'edit': False,
                'create': False,
                'delete': False,
                'duplicate': False,
            }
        }))

        self.env['ir.model.data'].sudo().create(xid_values)

        # link the worksheet template to its generated model and action
        self.write({
            'action_id': action.id,
            'model_id': model.id,
        })
        # this must be done after form view creation and filling the 'model_id' field
        self.sudo()._generate_qweb_report_template()

        # Add unique constraint on the x_model_id field since we want one worksheet per host record
        conname = '%s_x_%s_id_uniq' % (name, res_model)
        concode = 'unique(x_%s_id)' % (res_model)
        tools.add_constraint(self.env.cr, name, conname, concode)

    def _prepare_default_fields_values(self):
        """Prepare a list that contains the data to create the default fields for
        the model created from the template. Fields related to these fields
        shouldn't be put here, they should be created after the creation of these
        fields.
        """
        res_model_name = self.res_model.replace('.', '_')
        fields_func = getattr(self, '_default_%s_template_fields' % res_model_name, False)
        return [
            (0, 0, {
                'name': 'x_%s_id' % (res_model_name),
                'field_description': self.env[self.res_model]._description,
                'ttype': 'many2one',
                'relation': self.res_model,
                'required': True,
                'on_delete': 'cascade',
            }),
            (0, 0, {
                'name': 'x_comments',
                'ttype': 'html',
                'field_description': 'Comments',
            }),
        ] + (fields_func and fields_func() or [])

    def _prepare_default_form_view_values(self, model):
        """Create a default form view for the model created from the template.
        """
        res_model_name = self.res_model.replace('.', '_')
        form_arch_func = getattr(self, '_default_%s_worksheet_form_arch' % res_model_name, False)
        return {
            'type': 'form',
            'name': 'template_view_' + "_".join(self.name.split(' ')),
            'model': model.model,
            'arch': form_arch_func and form_arch_func() or """
                <form create="false" duplicate="false">
                    <sheet>
                        <h1 invisible="context.get('studio') or context.get('default_x_%s_id')">
                            <field name="x_%s_id"/>
                        </h1>
                        <group>
                            <field name="x_comments" placeholder="Add details about your intervention..."/>
                        </group>
                    </sheet>
                </form>
            """ % (res_model_name, res_model_name)
        }

    def _prepare_default_tree_view_values(self, model):
        """Create a default list view for the model created from the template."""
        res_model_name = self.res_model.replace('.', '_')
        tree_arch_func = getattr(self, f'_default_{res_model_name}_worksheet_tree_arch', False)
        return {
            'type': 'tree',
            'name': 'tree_view_' + self.name.replace(' ', '_'),
            'model': model.model,
            'arch': tree_arch_func and tree_arch_func() or """
                <tree>
                    <field name="create_date" widget="date"/>
                    <field name="x_name"/>
                </tree>
            """
        }

    def _prepare_default_search_view_values(self, model):
        """Create a default search view for the model created from the template."""
        res_model_name = self.res_model.replace('.', '_')
        search_arch_func = getattr(self, f'_default_{res_model_name}_worksheet_search_arch', False)
        return {
            'type': 'search',
            'name': 'search_view_' + self.name.replace(' ', '_'),
            'model': model.model,
            'arch': search_arch_func and search_arch_func() or """
                <search>
                    <field name="x_name"/>
                    <filter string="Created on" date="create_date" name="create_date"/>
                    <filter name="group_by_month" string="Created on" context="{'group_by': 'create_date:month'}"/>
                </search>
            """
        }

    @api.model
    def _get_models_to_check_dict(self):
        """To be override in the module using it. It returns a dictionary contains
        the model you want to check for multi-company in the write method.
        Key: res_model name, eg: "quality.check"
        Value: a list of (model name, model name to show), eg: [("quality.point", "Quality Point"), ("quality.check", "Quality Check")]
        """
        return {}

    def action_analysis_report(self):
        self.ensure_one()
        return {
            'name': _('Analysis'),
            'type': 'ir.actions.act_window',
            'view_mode': 'graph,pivot,list,form',
            'res_model': self.sudo().model_id.model,
            'context': "{'search_default_group_by_month': True}",
        }

    def action_view_worksheets(self):
        action = self.action_id.sudo().read()[0]
        # modify context to force no create/import button
        action['context'] = dict(literal_eval(action.get('context', '{}')), search_default_group_by_month=True)
        if self.worksheet_count == 1:
            action.update({
                'views': [(False, 'form')],
                'res_id': self.env[action['res_model']].search([], limit=1).id,
            })
        return action

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def get_x_model_form_action(self):
        action = self.action_id.read()[0]
        action.update({
            'views': [[False, "form"]],
            'context': {'default_x_%s_id' % self.res_model.replace('.', '_'): True},  # to hide model_id from view
        })
        return action

    def _get_qweb_arch_omitted_fields(self):
        return [
            'x_%s_id' % self.res_model.replace('.', '_'), 'x_name',  # redundant
        ]

    def _add_field_node_to_container(self, field_node, form_view_fields, container_col):
        field_name = field_node.attrib['name']
        invisible = field_node.get("invisible", "False")
        if invisible in ("True", "1"):
            return container_col

        new_container_col = container_col
        if field_name not in self._get_qweb_arch_omitted_fields():
            field_info = form_view_fields.get(field_name)
            widget = field_node.attrib.get('widget', False)
            is_signature = False
            # adapt the widget syntax
            if widget:
                if widget == 'signature':
                    is_signature = True
                    field_node.attrib.pop('widget')
                elif widget == "image":
                    # image widgets in qweb (only with t-out)
                    field_node.attrib['t-options-widget'] = "'image'"
            # basic form view -> qweb node transformation
            if field_info and field_info.get('type') != 'binary' or widget in ['image', 'signature']:
                # adapt the field node itself
                field_name = 'worksheet.' + field_node.attrib['name']
                field_node.attrib.pop('name')
                if is_signature:
                    field_node.tag = 'img'
                    field_node.attrib['style'] = 'width: 250px;'
                    field_node.attrib['t-att-src'] = 'image_data_uri(%s)' % field_name
                    field_node.attrib['t-if'] = field_name
                elif field_info.get('type') == 'boolean':
                    field_node.tag = 'i'
                    field_node.attrib[
                        't-att-class'] = "'col-lg-7 col-12 fa ' + ('fa-check-square' if %s else 'fa-square-o')" % field_name
                else:
                    field_node.tag = 'div'
                    field_node.attrib['t-att-class'] = "'col-7' if report_type == 'pdf' else 'col-lg-7 col-12'"
                    field_node.attrib['t-field'] = field_name
                # generate a description
                description = etree.Element('div', {'t-att-class': "('col-5' if report_type == 'pdf' else 'col-lg-5 col-12') + ' font-weight-bold'"})
                description.text = field_node.attrib.pop('string', field_info and field_info.get('string'))
                # insert all that in a container
                container = etree.Element('div', {'class': 'row mb-3', 'style': 'page-break-inside: avoid'})
                container.append(description)
                container.append(field_node)
                new_container_col.append(container)
        return new_container_col

    def _get_qweb_arch(self, ir_model, qweb_template_name, form_view_id=False):
        """ This function generates a qweb arch, from the form view of the given ir.model record.
            This is needed because the number and names of the fields aren't known in advance.
            :param ir_model: ir.model record
            :returns the arch of the template qweb (t-name included)
        """
        view_get_result = self.env[ir_model.model].get_view(form_view_id, 'form')
        form_view_arch = view_get_result['arch']
        node = etree.fromstring(form_view_arch)
        form_view_fields = set(el.get('name') for el in node.xpath('.//field[not(ancestor::field)]'))
        form_view_fields = {fname: field_info for fname, field_info in self.env[ir_model.model].fields_get().items() if fname in form_view_fields}

        qweb_arch = etree.Element("div")
        for row_node in node.xpath('//group[not(ancestor::group)]|//field[not(ancestor::group)]'):
            container_row = etree.Element('div')
            container_col = etree.Element('div')
            # pattern A: field is not in any element group --> field take full width
            if 'name' in row_node.attrib and row_node.attrib['name'] not in self._get_qweb_arch_omitted_fields() and row_node.attrib['name'] in form_view_fields:
                field_node = row_node
                new_container_col = self._add_field_node_to_container(field_node, form_view_fields, container_col)
                container_row.append(new_container_col)
                qweb_arch.append(container_row)
            else:
                # pattern B: whe have an element group inside an element group --> we split into 2 columns
                cols = row_node.xpath('./group')
                if len(cols) > 0:
                    container_row = etree.Element('div', {'class': 'row', 'style': 'page-break-inside: avoid'})
                    for col_node in cols:
                        container_col = etree.Element('div', {'class': 'col-6', 'style': 'page-break-inside: avoid'})
                        container_row.append(container_col)
                        for field_node in col_node.xpath('./field'):
                            new_container_col = self._add_field_node_to_container(field_node, form_view_fields, container_col)
                            container_row.append(new_container_col)
                    qweb_arch.append(container_row)
                # pattern C: whe have a field inside an element group --> field take full width
                else:
                    for field_node in row_node.xpath('./field'):
                        new_container_col = self._add_field_node_to_container(field_node, form_view_fields, container_col)
                        container_row.append(new_container_col)
                        qweb_arch.append(container_row)
        t_root = etree.Element('t', {'t-name': qweb_template_name})
        t_root.append(qweb_arch)
        return etree.tostring(t_root)

    def _generate_qweb_report_template(self, form_view_id=False):
        for worksheet_template in self:
            report_name = worksheet_template.model_id.model.replace('.', '_')
            new_arch = self._get_qweb_arch(worksheet_template.model_id, report_name, form_view_id)
            if worksheet_template.report_view_id:  # update existing one
                worksheet_template.report_view_id.write({'arch': new_arch})
            else:  # create the new one
                report_view = self.env['ir.ui.view'].create({
                    'type': 'qweb',
                    'model': False,  # template qweb for report
                    'inherit_id': False,
                    'mode': 'primary',
                    'arch': new_arch,
                    'name': report_name
                })
                self.env['ir.model.data'].create({
                    'name': 'report_custom_%s' % (report_name,),
                    'module': getattr(self, '_get_%s_module_name' % self.res_model.replace('.', '_'))(),
                    'res_id': report_view.id,
                    'model': 'ir.ui.view',
                    'noupdate': True,
                })
                # linking the new one
                worksheet_template.write({'report_view_id': report_view.id})
