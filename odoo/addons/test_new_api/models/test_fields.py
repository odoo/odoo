from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ModelAdvancedComputes(models.Model):
    _name = 'test_new_api.model_advanced_computes'
    _description = 'model with advanced computes'
    _pre_compute = True

    name1 = fields.Char('First Name')
    name2 = fields.Char('Last Name')
    title = fields.Char('Job Function')

    # Two fields computed in same compute method
    upper_name_1 = fields.Char(compute="_compute_uppers", store=True, pre_compute=True)
    upper_name_2 = fields.Char(compute="_compute_uppers", store=True, pre_compute=True)

    # pre-compute False basic field
    full_upper_name = fields.Char(compute="_compute_full_upper", pre_compute=False, store=True)

    # Field depending on post_computed fields
    create_month = fields.Integer(compute="_compute_create_month", store=True)

    # VFE TODO one related field?

    # pre_compute False relational field
    duplicates = fields.Many2many(
        comodel_name='test_new_api.model_advanced_computes',
        relation='test_new_api_advanced_computes_rel', column1="rec1", column2="rec2",
        compute="_compute_duplicates", pre_compute=False, store=True)

    # Pre-computations on x2m precompute records
    child_ids = fields.One2many("test_new_api.x2m_computes", "parent_id")
    related_ids = fields.Many2many("test_new_api.x2m_computes", relation="advanced_computes_m2m_rel")

    children_value = fields.Float(compute="_compute_children_value", store=True, required=True, pre_compute=True)
    related_value = fields.Float(compute="_compute_related_value", store=True, required=True, pre_compute=True)

    @api.depends('name1', 'name2')
    def _compute_uppers(self):
        for rec in self:
            if rec.id or not rec.env.context.get('creation', False):
                raise ValidationError("Should be computed before record creation")
            rec.upper_name_1 = rec.name1.title()
            rec.upper_name_2 = rec.name2.title()

    @api.depends('create_date')
    def _compute_create_month(self):
        for rec in self:
            if not rec.id or not rec.env.context.get('creation', False):
                raise ValidationError("Should be computed after record creation")
            rec.create_month = rec.create_date and rec.create_date.month

    @api.depends('upper_name_1', 'upper_name_2')
    def _compute_full_upper(self):
        for rec in self:
            if not rec.id or not rec.env.context.get('creation', False):
                raise ValidationError("Should be computed after creation because specified as pre_compute=False")
            rec.full_upper_name = rec.upper_name_1 + " " + rec.upper_name_2

    @api.depends('upper_name_1', 'upper_name_2')
    def _compute_duplicates(self):
        for rec in self:
            if not rec.id or not rec.env.context.get('creation', False):
                raise ValidationError("Shouldn't be computed before record creation")
            rec.duplicates = rec.search([
                ('upper_name_1', '=', rec.upper_name_1),
                ('upper_name_2', '=', rec.upper_name_2),
                ('id', '!=', rec.id),
            ])

    @api.depends('child_ids')
    def _compute_children_value(self):
        for rec in self:
            if rec.id or not rec.env.context.get('creation', False):
                raise ValidationError("Should be computed before record creation")
            rec.children_value = sum(rec.child_ids.mapped('value'))

    @api.depends('related_ids')
    def _compute_related_value(self):
        for rec in self:
            if rec.id or not rec.env.context.get('creation', False):
                raise ValidationError("Should be computed before record creation")
            rec.related_value = sum(rec.related_ids.mapped('value'))


class ModelAdvancedComputesX2M(models.Model):
    _name = 'test_new_api.x2m_computes'
    _description = 'model with advanced computes'
    _pre_compute = True

    info = fields.Char('Info', default="blabla")

    display_info = fields.Char(compute="_compute_display_info", store=True, required=True)

    parent_id = fields.Many2one("test_new_api.model_advanced_computes")

    value = fields.Float("", default=5.0)

    @api.depends('parent_id')
    def _compute_display_info(self):
        # if len(self) == 1 and not self.parent_id:
        #     raise ValidationError("x2m_precomputes should be computed in batch")
        for rec in self:
            if rec.id or not rec.env.context.get('creation', False):
                raise ValidationError("Should be computed before record creation")
            rec.display_info = (rec.parent_id.title or "") + "\n" + rec.info.title()

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         # Only true because we create all records of this model through x2m on the other model
    #         assert 'display_info' in vals, "display_info should have been pre-computed"
    #     return super().create(vals_list)


class DummyModel(models.Model):
    _name = 'test_new_api.dummy'
    _description = 'basic model with two fields (with & without defaults)'

    default = fields.Char(default="default")
    basic = fields.Char()
