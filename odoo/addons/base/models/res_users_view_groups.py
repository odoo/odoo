from odoo import api, fields, models


#----------------------------------------------------------
# transient model for user view configuration
#----------------------------------------------------------


class ResGroups(models.Model):
    _inherit = 'res.groups'
    _order = 'category_id,sequence,name'

    sequence = fields.Integer(string='Sequence')
    visible = fields.Boolean(related='category_id.visible', readonly=True)
    color = fields.Integer(string='Color Index')


# pylint: disable=E0102
class ResUsers(models.Model):  # noqa: F811
    _inherit = 'res.users'

    view_disjoint_group_ids = fields.Many2many('res.groups', compute='_compute_view_implied_group_ids', string="Disjoint groups")
    view_all_disjoint_group_ids = fields.Many2many('res.groups', compute='_compute_view_implied_group_ids', string="All disjoint groups")
    view_visible_implied_group_ids = fields.Many2many('res.groups', compute='_compute_view_implied_group_ids', string="Groups added automatically")
    view_show_technical_groups = fields.Boolean(string="Show technical groups", store=False)

    @api.depends('group_ids', 'view_show_technical_groups')
    def _compute_view_implied_group_ids(self):
        self.view_disjoint_group_ids = False
        self.view_all_disjoint_group_ids = False
        self.view_visible_implied_group_ids = False

        group_definitions = self.env['res.groups']._get_group_definitions()

        for user in self:
            view_disjoint_group_ids = user.group_ids.disjoint_ids
            view_all_disjoint_group_ids = list(group_definitions.get_disjoint_ids(user.all_group_ids.ids))
            view_visible_implied_group_ids = user.group_ids.implied_ids.all_implied_ids
            if not user.view_show_technical_groups:
                view_visible_implied_group_ids = view_visible_implied_group_ids.filtered(lambda g: g.category_id.visible)

            user.view_disjoint_group_ids = view_disjoint_group_ids
            user.view_all_disjoint_group_ids = view_all_disjoint_group_ids
            user.view_visible_implied_group_ids = view_visible_implied_group_ids
