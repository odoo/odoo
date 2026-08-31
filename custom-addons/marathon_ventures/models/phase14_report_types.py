# -*- coding: utf-8 -*-
"""Phase 14 v4 - Report Types (Salesforce-style multi-model reports).

A Report Type is a reusable template that defines:
  - a BASE model (the primary rowset)
  - zero or more JOINED models, each reachable via a relational field

Users create Reports by picking a Report Type; the Report Builder then
exposes fields from EVERY model in the type, not just one, and the
runtime executes the appropriate joins / row expansions.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MvReportType(models.Model):
    _name = 'mv.report.type'
    _description = 'MV Report Type'
    _order = 'sequence, name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True,
                       default=lambda self: _('New Report Type'))
    description = fields.Text(
        help='Explain what this report type is for (helps other users '
             'pick the right one).'
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    base_model_id = fields.Many2one(
        'ir.model', string='Base Model', required=True, tracking=True,
        ondelete='cascade',  # ir.model comodel requires explicit ondelete
        domain="[('model', '=like', 'mv.%')]",
        help='The primary rowset. Every report row starts from an '
             'instance of this model.',
    )
    base_model_name = fields.Char(related='base_model_id.model',
                                   store=True, readonly=True)

    node_ids = fields.One2many(
        'mv.report.type.node', 'report_type_id',
        string='Joined Models', copy=True,
    )
    node_count = fields.Integer(compute='_compute_node_count',
                                string='# Joins')

    is_public = fields.Boolean(string='Available to All Users',
                               default=True, tracking=True)
    owner_id = fields.Many2one(
        'res.users', string='Owner', required=True,
        default=lambda self: self.env.user, tracking=True,
    )

    @api.depends('node_ids')
    def _compute_node_count(self):
        for rt in self:
            rt.node_count = len(rt.node_ids)

    _sql_constraints = [
        ('unique_name', 'unique(name)',
         'Report Type name must be unique.'),
    ]

    @api.model
    def get_or_create_default(self, model_id):
        """Fetch or auto-create a base-only Report Type for a model.

        Used by the migration hook to backfill report_type_id on
        legacy mv.report rows that only had model_id set.
        """
        Model = self.env['ir.model']
        model = Model.browse(model_id).exists()
        if not model:
            raise UserError(_('Invalid model id: %s') % model_id)
        # A default type has the given base and zero nodes.
        rt = self.search([
            ('base_model_id', '=', model_id),
            ('node_ids', '=', False),
        ], limit=1)
        if rt:
            return rt
        return self.sudo().create({
            'name': _('Basic: %s') % (model.name or model.model),
            'base_model_id': model_id,
            'is_public': True,
            'description': _('Auto-created default Report Type for %s. '
                             'Contains no joined models - only the base '
                             'model\'s own fields.') % model.model,
        })


class MvReportTypeNode(models.Model):
    _name = 'mv.report.type.node'
    _description = 'MV Report Type Node'
    _order = 'report_type_id, sequence, id'

    report_type_id = fields.Many2one(
        'mv.report.type', string='Report Type',
        required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)

    # For the v4 first cut, all nodes attach directly to the base model
    # (single-hop join). Nested joins (grandchildren) are a follow-up:
    # the schema below is designed to accommodate them via
    # parent_node_id, we just don't surface it in the UI yet.
    parent_node_id = fields.Many2one(
        'mv.report.type.node', string='Attached To',
        ondelete='cascade',
        help='Blank = attaches to the base model. Populated = attaches '
             'to another joined node (nested join).',
    )

    # This node's DEFINING relational field on the parent (base or
    # parent node). Its ttype must be many2one/one2many/many2many.
    field_id = fields.Many2one(
        'ir.model.fields', string='Relation Field',
        required=True, ondelete='cascade',
        domain="[('ttype', 'in', ('many2one', 'one2many', 'many2many'))]",
        help='The relational field that leads FROM the parent model '
             'TO this joined model.',
    )
    field_model_id = fields.Many2one(
        'ir.model', string='Field On Model',
        ondelete='cascade',  # ir.model comodel requires explicit ondelete
        compute='_compute_field_model', store=True, readonly=True,
        help='The model the field_id lives on (== parent\'s target).',
    )

    relation_kind = fields.Selection([
        ('many2one', 'Many-to-One'),
        ('one2many', 'One-to-Many'),
        ('many2many', 'Many-to-Many'),
    ], compute='_compute_relation_kind', store=True, readonly=True)

    target_model_id = fields.Many2one(
        'ir.model', string='Joined Model',
        ondelete='cascade',  # ir.model comodel requires explicit ondelete
        compute='_compute_target_model', store=True, readonly=True,
    )
    target_model_name = fields.Char(
        related='target_model_id.model', store=True, readonly=True,
    )
    target_model_display = fields.Char(
        related='target_model_id.name', store=True, readonly=True,
    )

    alias = fields.Char(
        string='Alias',
        help='Custom label shown in the Report Builder Fields panel. '
             'Blank = use the joined model\'s natural name.',
    )
    display_label = fields.Char(
        compute='_compute_display_label', store=True, readonly=True,
    )

    # Dotted path from the base model down to THIS node. E.g. for a
    # node "advertiser_id" on the base, path_prefix = "advertiser_id".
    # For a nested node "brand_ids" on the advertiser node,
    # path_prefix = "advertiser_id.brand_ids".
    path_prefix = fields.Char(
        compute='_compute_path_prefix', store=True, readonly=True,
        # Recursive: this compute reads parent_node_id.path_prefix
        # (same field on a related record). Without recursive=True
        # Odoo emits a warning about undeclared self-dependency.
        recursive=True,
    )

    @api.depends('field_id', 'field_id.ttype')
    def _compute_relation_kind(self):
        for n in self:
            n.relation_kind = n.field_id.ttype if n.field_id else False

    @api.depends('field_id', 'field_id.relation')
    def _compute_target_model(self):
        Model = self.env['ir.model']
        for n in self:
            rel = n.field_id.relation if n.field_id else False
            if not rel:
                n.target_model_id = False
                continue
            m = Model.search([('model', '=', rel)], limit=1)
            n.target_model_id = m.id if m else False

    @api.depends('parent_node_id', 'parent_node_id.target_model_id',
                 'report_type_id', 'report_type_id.base_model_id')
    def _compute_field_model(self):
        """The model on which this node's field_id lives.

        If parent_node_id is set, that's the parent node's target.
        Otherwise, this node attaches to the base model.
        """
        for n in self:
            if n.parent_node_id:
                n.field_model_id = n.parent_node_id.target_model_id
            else:
                n.field_model_id = n.report_type_id.base_model_id

    @api.depends('alias', 'target_model_display', 'target_model_name')
    def _compute_display_label(self):
        for n in self:
            n.display_label = (
                n.alias
                or n.target_model_display
                or n.target_model_name
                or ''
            )

    @api.depends('field_id', 'field_id.name',
                 'parent_node_id', 'parent_node_id.path_prefix')
    def _compute_path_prefix(self):
        for n in self:
            if not n.field_id:
                n.path_prefix = False
                continue
            fname = n.field_id.name
            if n.parent_node_id and n.parent_node_id.path_prefix:
                n.path_prefix = '%s.%s' % (n.parent_node_id.path_prefix, fname)
            else:
                n.path_prefix = fname

    @api.constrains('field_id', 'field_model_id')
    def _check_field_belongs_to_model(self):
        """A node's relation field must live on its parent's model."""
        for n in self:
            if not n.field_id or not n.field_model_id:
                continue
            if n.field_id.model_id != n.field_model_id:
                raise UserError(_(
                    "The relation field '%(field)s' doesn't belong to "
                    "the expected model '%(model)s'. "
                    "Pick a field that lives on that model."
                ) % {
                    'field': n.field_id.name,
                    'model': n.field_model_id.model,
                })
