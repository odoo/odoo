# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import UserError


class Category(models.Model):
    _name = 'nursery.plant.category'
    _inherit = ['rating.parent.mixin', 'mail.alias.mixin']
    _description = 'Plant Category'
    _order = 'sequence asc, name'

    name = fields.Char('Name', required=True, translate=True)
    internal = fields.Boolean('Internal', help='Orders belonging to this category should not be shared')
    sequence = fields.Integer('Sequence', default=1)
    order_user_id = fields.Many2one('res.users', 'Order Responsible')
    description = fields.Text('Description')
    image = fields.Image('Image')
    plant_ids = fields.One2many('nursery.plant', 'category_id', 'Plants')
    plant_count = fields.Integer('# Plants', compute='_compute_plant_count')
    order_ids = fields.One2many('nursery.order', 'category_id', 'Orders')
    order_count = fields.Integer('# Orders', compute='_compute_order_count')

    @api.depends('plant_ids')
    def _compute_plant_count(self):
        rg_data = dict(
            (item['category_id'][0], item['category_id_count'])
            for item in self.env['nursery.plant'].read_group([('category_id', 'in', self.ids)], ['category_id'], ['category_id'])
        )
        for category in self:
            category.plant_count = rg_data.get(category.id, 0)

    @api.depends('order_ids')
    def _compute_order_count(self):
        rg_data = dict(
            (item['category_id'][0], item['category_id_count'])
            for item in self.env['nursery.order'].read_group([('category_id', 'in', self.ids)], ['category_id'], ['category_id'])
        )
        for category in self:
            category.order_count = rg_data.get(category.id, 0)

    def _alias_get_creation_values(self):
        values = super(Category, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('nursery.order').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['category_id'] = self.id
        return values

    def action_view_plants(self):
        action = self.env.ref('plant_nursery.nursery_plant_action_category').read()[0]
        return action

    def action_view_orders(self):
        action = self.env.ref('plant_nursery.nursery_order_action_category').read()[0]
        return action

    def action_view_ratings(self):
        action = self.env.ref('plant_nursery.rating_rating_action_nursery_category').read()[0]
        action['domain'] = [('parent_res_id', 'in', self.ids), ('parent_res_model', '=', 'nursery.plant.category')]
        return action


class Tag(models.Model):
    _name = 'nursery.plant.tag'
    _description = 'Plant Tag'
    _order = 'name'

    name = fields.Char('Name', required=True)
    color = fields.Integer('Color Index', default=10)


class Event(models.Model):
    _name = 'nursery.plant.event'
    _description = 'Plant Event'
    _order = 'date_to DESC'

    plant_id = fields.Many2one(
        'nursery.plant', string='Plant',
        ondelete='cascade', required=True)
    event_type = fields.Selection([
        ('sow', 'Sow'), ('plant_out', 'Plant Out'),
        ('harvest', 'Harvest')],
        string='Event Type', required=True)
    date_from = fields.Date('Event Begin', index=True)
    date_to = fields.Date('Event End', index=True)
    color = fields.Integer('Color Index', default=10)
    description = fields.Text(string='Description')

    def name_get(self):
        return [
            (event.id, '%s %s' % (event.event_type, event.plant_id.display_name))
            for event in self]


class Plants(models.Model):
    _name = 'nursery.plant'
    _description = 'Nursery Plant'
    _inherit = ['mail.thread', 'mail.activity.mixin',
                'website.seo.metadata', 'website.published.multi.mixin']
    #'documents.mixin',
    # description
    name = fields.Char("Plant Name", required=True, tracking=1)
    description_short = fields.Html('Short description')
    description = fields.Html('Description')
    description_short = fields.Html('Short description')
    category_id = fields.Many2one('nursery.plant.category', string='Category')
    tag_ids = fields.Many2many('nursery.plant.tag', string='Tags')
    image = fields.Binary('Image', attachment=True)
    # sales
    price = fields.Float(tracking=2)
    user_id = fields.Many2one(
        'res.users', string='Responsible', index=True, required=True,
        default=lambda self: self.env.user)
    company_id = fields.Many2one(
        'res.company', string='Company', related='user_id.company_id',
        readonly=True, store=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='company_id.currency_id',
        readonly=True, required=True)
    internal = fields.Boolean('Internal')
    # care informations
    description_care = fields.Html('Care instructions')
    description_preservation = fields.Html('Preservation instructions')
    ground = fields.Selection(selection=[
        ('any', 'Any'), ('filtering', 'Filtering Soil'),
        ('heathland', 'Heathland'), ('loam', 'Loam')],
        string='Ground Type', default='any')
    # sewing informations
    exposure = fields.Selection(selection=[
        ('sun', 'Sun'),
        ('bright', 'Bright'),
        ('half', 'Half Shade'),
        ('shade', 'Shade')], string='Exposure', default='bright')
    grouping_ids = fields.Many2many(
        'nursery.plant', 'nursery_plant_grouping_rel', 'plant_id', 'plant_other_id',
        string='Plants to group')
    event_ids = fields.One2many('nursery.plant.event', 'plant_id', 'Events')
    event_next_id = fields.Many2one(
        'nursery.plant.event', 'Next Event',
        compute='_compute_event_next_id', store=True)
    event_next_from = fields.Date(related='event_next_id.date_from')
    event_next_to = fields.Date(related='event_next_id.date_to')
    event_next_color = fields.Integer(related='event_next_id.color')
    # order informations
    order_line_ids = fields.One2many("nursery.order.line", "plant_id", string="Orders")
    order_count = fields.Integer(compute='_compute_order_count',
                                 string="Total sold")
    number_in_stock = fields.Integer()

    @api.depends('order_line_ids')
    def _compute_order_count(self):
        rg_data = dict(
            (item['plant_id'][0], item['plant_id_count'])
            for item in self.env['nursery.order.line'].read_group([('plant_id', 'in', self.ids)], ['plant_id'], ['plant_id'])
        )
        for plant in self:
            plant.order_count = rg_data.get(plant.id, 0)

    @api.depends('event_ids.date_to')
    def _compute_event_next_id(self):
        next_events = self.env['nursery.plant.event'].search([
            ('plant_id', 'in', self.ids),
            ('date_to', '>=', fields.Date.today())
        ], order='date_to ASC, id DESC')
        plant_event = dict.fromkeys(self.ids, False)
        for event in next_events:
            if not plant_event.get(event.plant_id.id):
                plant_event[event.plant_id.id] = event
        for plant in self:
            plant.event_next_id = plant_event.get(plant.id, False)

    def _compute_can_publish(self):
        super(Plants, self)._compute_can_publish()
        for plant in self:
            plant.can_publish = self.env.user.has_group('website.group_website_publisher')

    def _compute_website_url(self):
        super(Plants, self)._compute_website_url()
        for plant in self:
            if plant.id:
                plant.website_url = '/plants/plant/%s' % slug(plant)

    @api.constrains('number_in_stock')
    def _check_available_in_stock(self):
        for plant in self:
            if plant.number_in_stock < 0:
                raise UserError(_('Stock cannot be negative.'))

    def action_view_orders(self):
        return {
            'name': _('%s Orders') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'nursery.order',
            'view_mode': 'kanban,tree,form',
            'domain': [('line_ids.plant_id', 'in', self.ids)],
        }

    def _get_document_folder(self):
        return self.env.ref('plant_nursery.documents_plant_folder')

    def _get_document_tags(self):
        return self.env.ref('plant_nursery.documents_plant_facet_tech')

    def _get_document_owner(self):
        return self.user_id

    def _track_subtype(self, init_values):
        if 'price' in init_values:
            return self.env.ref('plant_nursery.plant_price')
        return super(Plants, self)._track_subtype(init_values)

    def _track_template(self, changes):
        res = super(Plants, self)._track_template(changes)
        if 'price' in changes:
            res['price'] = (self.env.ref('plant_nursery.mail_template_plant_price_updated'), {'composition_mode': 'comment'})
        return res
