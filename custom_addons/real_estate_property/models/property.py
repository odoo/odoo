from email.policy import default

from odoo import fields,models,api
from odoo.exceptions import ValidationError
from datetime import timedelta


class Property(models.Model):
    _name = "property"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Real Estate Property"

    ref = fields.Char(default='New', readonly=True)
    active = fields.Boolean('Active', default=True)
    name = fields.Char('Property Name', required=True, translate=True)
    description = fields.Text('Description')
    postcode = fields.Char('Postcode', required=True, tracking=1)
    date_availability = fields.Date('Available From', tracking=1)
    expected_selling_date = fields.Date('Expected Selling Date', tracking=1)
    is_late = fields.Boolean('Is Late?', tracking=1)
    expected_price = fields.Float('Expected Price', digits=(0,4))
    selling_price = fields.Float('Selling Price',tracking=1)
    diff = fields.Float('price difference', compute='_compute_price_difference', store=True)
    bedrooms = fields.Integer('Number of Bedrooms')
    living_area = fields.Integer('Living Area (sqm)')
    facades = fields.Integer('Number of Facades')
    garage = fields.Boolean('Garage', groups="real_estate_property.property_manager_group")
    garden = fields.Boolean('Garden')
    garden_area = fields.Integer('Garden Area (sqm)')
    garden_orientation = fields.Selection(
        [
            ('north', 'North'),
            ('south', 'South'),
            ('east', 'East'),
            ('west', 'West')
        ]
    )
    owner_id = fields.Many2one('owner', string='Owner')
    tag_ids = fields.Many2many('tag', string='Tags')
    owner_address = fields.Text(related='owner_id.address', string='Owner Address')
    owner_phone = fields.Char(related='owner_id.phone', string='Owner Phone')
    line_ids = fields.One2many('property.line', 'property_id', string='Property Lines')
    create_time = fields.Datetime('Created On', default=fields.Datetime.now())
    next_time = fields.Datetime(compute='_compute_next_time', string='Next Activity Time', store=True)

    state = fields.Selection([
        ('new', 'New'),
        ('offer_received', 'Offer Received'),
        ('offer_accepted', 'Offer Accepted'),
        ('sold', 'Sold'),
        ('closed', 'Closed'),
        ('canceled', 'Canceled')
    ], default='new', string='Status')

    @api.depends('expected_price', 'selling_price', 'owner_id.phone')
    def _compute_price_difference(self):
        for rec in self:
            print("inside compute method")
            rec.diff = rec.expected_price - rec.selling_price


    _unique_name_postcode = models.Constraint(
        'UNIQUE(postcode)',
        'The postcode must be unique for each property.'
    )

    @api.depends('create_time')
    def _compute_next_time(self):
        for rec in self:
            if rec.create_time:
                rec.next_time = rec.create_time + timedelta(hours=6)
            else:
                rec.next_time = False



    @api.constrains('bedrooms')
    def _check_field_bedrooms(self):
       for rec in self:
           if rec.bedrooms == 0:
                raise ValidationError("The number of bedrooms cannot be zero.")



    def action_new(self):
        for rec in self:
            rec.create_history_record(rec.state,'new')
            rec.state = 'new'


    def action_offer_received(self):
        for rec in self:
            rec.create_history_record(rec.state, 'offer_received')
            rec.state = 'offer_received'


    def action_open_related_owner(self):
        action = self.env['ir.actions.actions']._for_xml_id('real_estate_property.owner_action')
        view_id = self.env.ref('real_estate_property.owner_view_form').id
        action['res_id'] = self.owner_id.id
        action['views'] = [[view_id, 'form']]
        return action

    def action_offer_accepted(self):
        for rec in self:
            rec.create_history_record(rec.state, 'offer_accepted')
            rec.state = 'offer_accepted'


    def action_closed(self):
        for rec in self:
            rec.create_history_record(rec.state, 'closed')
            rec.state = 'closed'


    def action_open_change_state_wizard(self):
        action = self.env['ir.actions.actions']._for_xml_id('real_estate_property.change_state_wizard_action')
        action['context'] = {
            'default_property_id': self.id,
        }
        return action



    def check_expected_selling_date(self):
        property_ids = self.search([])
        for rec in property_ids:
            if rec.expected_selling_date and rec.expected_selling_date < fields.Date.today():
                rec.is_late = True
            else:
                rec.is_late = False


    def action(self):
        # [('name','=','Property1')]
        print(self.env['property'].search([('name','!=','property4')]))



    @api.model_create_multi
    def create(self,vals):
        res = super(Property, self).create(vals)
        if res.ref == 'New':
            sequence = self.env['ir.sequence'].next_by_code('property.sequence') or 'New'
            res.ref = sequence
        return res

    def create_history_record(self,old_state,new_state,reason=""):
        for rec in self:
            rec.env['property.history'].create({
                'user_id': self.env.uid,
                'property_id': rec.id,
                'old_state': old_state,
                'new_state': new_state,
                'reason': reason or '',
                'line_ids': [(0, 0, {'description': line.description, 'area': line.area}) for line in rec.line_ids]
            })


    @api.model
    def _search(self,domain,offset=0,limit=None,order=None,**kwargs):
        res = super(Property,self)._search(domain,offset=offset,limit=limit,order=order,**kwargs)
        # print("Printing from custom search method")
        return res


    def write(self,vals):
        res = super(Property,self).write(vals)
        # print("Printing from custom write method")
        return res

    def unlink(self):
        res = super(Property,self).unlink()
        print("Printing from custom unlink method")
        return res

class PropertyLine(models.Model):
    _name = "property.line"
    _description = "Property Line"

    area = fields.Float()
    description = fields.Char()
    property_id = fields.Many2one('property', string='Property')