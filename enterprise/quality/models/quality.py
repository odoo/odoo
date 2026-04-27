# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv.expression import OR


class TestType(models.Model):
    _name = "quality.point.test_type"
    _description = "Quality Control Test Type"

    # Used instead of selection field in order to hide a choice depending on the view.
    name = fields.Char('Name', required=True, translate=True)
    technical_name = fields.Char('Technical name', required=True)
    active = fields.Boolean('active', default=True)


class QualityPoint(models.Model):
    _name = "quality.point"
    _description = "Quality Control Point"
    _inherit = ['mail.thread']
    _order = "sequence, id"
    _check_company_auto = True

    def _get_default_team_id(self):
        company_id = self.company_id.id or self.env.context.get('default_company_id', self.env.company.id)
        return self.team_id._get_quality_team(self.env['quality.alert.team']._check_company_domain(company_id))

    def _get_default_test_type_id(self):
        domain = self._get_type_default_domain()
        return self.env['quality.point.test_type'].search(domain, limit=1).id

    name = fields.Char(
        'Reference', copy=False, default=lambda self: _('New'),
        required=True)
    sequence = fields.Integer('Sequence')
    title = fields.Char('Title')
    team_id = fields.Many2one(
        'quality.alert.team', 'Team', check_company=True,
        default=_get_default_team_id, required=True)
    product_ids = fields.Many2many(
        'product.product', string='Products',
        check_company=True,
        domain="[('type', '=', 'consu')]",
        help="Quality Point will apply to every selected Products.")
    product_category_ids = fields.Many2many(
        'product.category', string='Product Categories',
        help="Quality Point will apply to every Products in the selected Product Categories.")

    picking_type_ids = fields.Many2many(
        'stock.picking.type', string='Operation Types', required=True, check_company=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Responsible',
        domain=lambda self: [('groups_id', 'in', self.env.ref("quality.group_quality_user").id), ('share', '=', False)],
        check_company=True)
    active = fields.Boolean(default=True)
    check_count = fields.Integer(compute="_compute_check_count")
    check_ids = fields.One2many('quality.check', 'point_id')
    test_type_id = fields.Many2one('quality.point.test_type', 'Test Type', help="Defines the type of the quality control point.",
                                   required=True, default=_get_default_test_type_id, tracking=True)
    test_type = fields.Char(related='test_type_id.technical_name', readonly=True)
    note = fields.Html('Note')
    reason = fields.Html('Cause')

    def _compute_check_count(self):
        check_data = self.env['quality.check']._read_group([('point_id', 'in', self.ids)], ['point_id'], ['__count'])
        result = {point.id: count for point, count in check_data}
        for point in self:
            point.check_count = result.get(point.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' not in vals or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('quality.point') or _('New')
        return super().create(vals_list)

    def check_execute_now(self):
        # TDE FIXME: make true multi
        self.ensure_one()
        return True

    def _get_type_default_domain(self):
        return []


class QualityAlertTeam(models.Model):
    _name = "quality.alert.team"
    _description = "Quality Alert Team"
    _inherit = ['mail.alias.mixin', 'mail.thread']
    _order = "sequence, id"

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', index=True)
    sequence = fields.Integer('Sequence')
    check_count = fields.Integer('# Quality Checks', compute='_compute_check_count')
    alert_count = fields.Integer('# Quality Alerts', compute='_compute_alert_count')
    color = fields.Integer('Color', default=1)

    def _compute_check_count(self):
        check_data = self.env['quality.check']._read_group([('team_id', 'in', self.ids), ('quality_state', '=', 'none')], ['team_id'], ['__count'])
        check_result = {team.id: count for team, count in check_data}
        for team in self:
            team.check_count = check_result.get(team.id, 0)

    def _compute_alert_count(self):
        alert_data = self.env['quality.alert']._read_group([('team_id', 'in', self.ids), ('stage_id.done', '=', False)], ['team_id'], ['__count'])
        alert_result = {team.id: count for team, count in alert_data}
        for team in self:
            team.alert_count = alert_result.get(team.id, 0)

    @api.model
    def _get_quality_team(self, domain):
        team_id = self.env['quality.alert.team'].search(domain, limit=1).id
        if team_id:
            return team_id
        else:
            raise UserError(_("No quality team found for this company.\n"
                              "Please go to configuration and create one first."))

    def _alias_get_creation_values(self):
        values = super(QualityAlertTeam, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('quality.alert').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['team_id'] = self.id
            defaults['company_id'] = self.company_id.id
        return values


class QualityReason(models.Model):
    _name = "quality.reason"
    _description = "Root Cause for Quality Failure"

    name = fields.Char('Name', required=True, translate=True)


class QualityTag(models.Model):
    _name = "quality.tag"
    _description = "Quality Tag"

    name = fields.Char('Tag Name', required=True)
    color = fields.Integer('Color Index', help='Used in the kanban view')  # TDE: should be default value


class QualityAlertStage(models.Model):
    _name = "quality.alert.stage"
    _description = "Quality Alert Stage"
    _order = "sequence, id"
    _fold_name = 'folded'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence')
    folded = fields.Boolean('Folded')
    done = fields.Boolean('Alert Processed')
    team_ids = fields.Many2many('quality.alert.team', string='Teams')


class QualityCheck(models.Model):
    _name = "quality.check"
    _description = "Quality Check"
    _order = "point_id, id"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    name = fields.Char('Reference', copy=False)
    point_id = fields.Many2one(
        'quality.point', 'Control Point', check_company=True)
    title = fields.Char('Title', compute='_compute_title', store=True, precompute=True, readonly=False)
    quality_state = fields.Selection([
        ('none', 'To do'),
        ('pass', 'Passed'),
        ('fail', 'Failed')], string='Status', tracking=True,
        default='none', copy=False)
    control_date = fields.Datetime('Control Date', tracking=True, copy=False)
    product_id = fields.Many2one(
        'product.product', 'Product', check_company=True,
        domain="[('type', '=', 'consu')]")
    picking_id = fields.Many2one('stock.picking', 'Picking', check_company=True)
    partner_id = fields.Many2one(
        related='picking_id.partner_id', string='Partner')
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial',
        check_company=True,
        domain="[('product_id', '=', product_id)]")
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True)
    team_id = fields.Many2one(
        'quality.alert.team', 'Team', required=True, check_company=True)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True, index=True,
        default=lambda self: self.env.company)
    alert_ids = fields.One2many('quality.alert', 'check_id', string='Alerts')
    alert_count = fields.Integer('# Quality Alerts', compute="_compute_alert_count")
    note = fields.Html('Note')
    test_type_id = fields.Many2one(
        'quality.point.test_type', 'Test Type',
        required=True)
    test_type = fields.Char(related='test_type_id.technical_name')
    picture = fields.Binary('Picture', attachment=True)
    additional_note = fields.Text(
        'Additional Note', help="Additional remarks concerning this check.")

    def _compute_alert_count(self):
        alert_data = self.env['quality.alert']._read_group([('check_id', 'in', self.ids)], ['check_id'], ['__count'])
        alert_result = {check.id: count for check, count in alert_data}
        for check in self:
            check.alert_count = alert_result.get(check.id, 0)

    def _compute_title(self):
        for check in self:
            check.title = check.point_id.title

    @api.onchange('point_id')
    def _onchange_point_id(self):
        if self.point_id:
            self.team_id = self.point_id.team_id.id
            self.test_type_id = self.point_id.test_type_id.id

    def _is_pass_fail_applicable(self):
        """ Return true if do_fail and do_pass can be applied."""
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' not in vals or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('quality.check') or _('New')
            if 'point_id' in vals and not vals.get('test_type_id'):
                vals['test_type_id'] = self.env['quality.point'].browse(vals['point_id']).test_type_id.id
            if 'point_id' in vals and not vals.get('note'):
                vals['note'] = self.env['quality.point'].browse(vals['point_id']).note
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'quality_state' in vals and not vals.get('user_id') or not vals.get('control_date'):
            if vals.get('quality_state') == 'pass':
                self.do_pass()
            elif vals.get('quality_state') == 'fail':
                self.do_fail()
        return res

    def do_fail(self):
        self.write({
            'quality_state': 'fail',
            'user_id': self.env.user.id,
            'control_date': datetime.now()})

    def do_pass(self):
        self.write({'quality_state': 'pass',
                    'user_id': self.env.user.id,
                    'control_date': datetime.now()})


class QualityAlert(models.Model):
    _name = "quality.alert"
    _description = "Quality Alert"
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _check_company_auto = True

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        team_id = self.env.context.get('default_team_id')
        if not team_id and self.env.context.get('active_model') == 'quality.alert.team' and\
                self.env.context.get('active_id'):
            team_id = self.env['quality.alert.team'].browse(self.env.context.get('active_id')).exists().id
        domain = [('team_ids', '=', False)]
        if team_id:
            domain = OR([domain, [('team_ids', 'in', team_id)]])
        return self.env['quality.alert.stage'].search(domain, limit=1).id

    def _get_default_team_id(self):
        company_id = self.company_id.id or self.env.context.get('default_company_id', self.env.company.id)
        domain = ['|', ('company_id', '=', company_id), ('company_id', '=', False)]
        return self.team_id._get_quality_team(domain)

    name = fields.Char('Name', default=lambda self: _('New'), copy=False)
    description = fields.Html('Description')
    stage_id = fields.Many2one(
        'quality.alert.stage', 'Stage', ondelete='restrict',
        group_expand='_read_group_stage_ids',
        default=lambda self: self._get_default_stage_id(),
        domain="['|', ('team_ids', '=', False), ('team_ids', 'in', team_id)]", tracking=True)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True, index=True,
        default=lambda self: self.env.company)
    reason_id = fields.Many2one('quality.reason', 'Root Cause')
    tag_ids = fields.Many2many('quality.tag', string="Tags")
    date_assign = fields.Datetime('Date Assigned')
    date_close = fields.Datetime('Date Closed')
    picking_id = fields.Many2one('stock.picking', 'Picking', check_company=True)
    action_corrective = fields.Html('Corrective Action')
    action_preventive = fields.Html('Preventive Action')
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True, default=lambda self: self.env.user)
    team_id = fields.Many2one(
        'quality.alert.team', 'Team', required=True, check_company=True,
        default=lambda x: x._get_default_team_id())
    partner_id = fields.Many2one('res.partner', 'Vendor', check_company=True)
    check_id = fields.Many2one('quality.check', 'Check', check_company=True)
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product', check_company=True,
        domain="[('type', '=', 'consu')]")
    product_id = fields.Many2one(
        'product.product', 'Product Variant',
        domain="[('product_tmpl_id', '=', product_tmpl_id)]")
    lot_id = fields.Many2one(
        'stock.lot', 'Lot', check_company=True,
        domain="['|', ('product_id', '=', product_id), ('product_id.product_tmpl_id', '=', product_tmpl_id)]")
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')], string='Priority',
        index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' not in vals or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('quality.alert') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        res = super(QualityAlert, self).write(vals)
        if 'stage_id' in vals and self.stage_id.done:
            self.write({'date_close': fields.Datetime.now()})
        return res

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        self.product_id = self.product_tmpl_id.product_variant_ids.ids and self.product_tmpl_id.product_variant_ids.ids[0]

    @api.onchange('team_id')
    def onchange_team_id(self):
        if self.team_id:
            self.company_id = self.team_id.company_id or self.env.company

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """ Only shows the stage related to the current team.
        """
        team_id = self.env.context.get('default_team_id')
        domain = [('id', 'in', stages.ids)]
        if not team_id and self.env.context.get('active_model') == 'quality.alert.team' and\
                self.env.context.get('active_id'):
            team_id = self.env['quality.alert.team'].browse(self.env.context.get('active_id')).exists().id
        if team_id:
            domain = OR([domain, ['|', ('team_ids', '=', False), ('team_ids', 'in', team_id)]])
        elif not stages:
            # if enter here, means we won't get any team_id and stage_id to search
            # so search stage without team_ids instead
            domain = [('team_ids', '=', False)]
        stage_ids = stages.sudo()._search(domain, order=stages._order)
        return stages.browse(stage_ids)
