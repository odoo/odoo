from odoo import models, fields, api


class RestrictUserMenu(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Ensure the menu is not restricted after removing from the list
        """
        self.clear_caches()
        return super(RestrictUserMenu, self).create(vals_list)

    def write(self, vals):
        """
        Ensure the menu is not restricted after removing from the list
        """
        res = super(RestrictUserMenu, self).write(vals)
        for record in self:
            # Update restrict_user_ids based on hide_menu_ids changes
            for menu in record.restrict_menu_ids:
                if menu not in record.restrict_menu_ids:
                    menu.write({
                        'restrict_user_ids': [(3, record.id)]  # Replace with (3, record.id) for deletion
                    })
                else:
                    menu.write({
                        'restrict_user_ids': [(4, record.id)]
                    })
        self.clear_caches()
        return res

    def _get_is_admin(self):
        """
        Restrict the specific menu tab for the Admin user form.
        """
        for rec in self:
            rec.is_admin = False
            if rec.id == self.env.ref('base.user_admin').id:
                rec.is_admin = True

    restrict_menu_ids = fields.Many2many('ir.ui.menu', string="Menu", store=True,
                                     help='Select menu items that need to be hidden for this user')
    is_admin = fields.Boolean(compute=_get_is_admin, string="Admin")



class RestrictMenu(models.Model):
    _inherit = 'ir.ui.menu'

    restrict_user_ids = fields.Many2many('res.users')
    root_id = fields.Many2one('ir.ui.menu', string="Application", compute='_compute_root_id', store=True)

    @api.depends('parent_id')
    def _compute_root_id(self):
        """
        Computes root element for every record and stores in root_id field.
        """
        for record in self:
            current_record = record
            while current_record.parent_id:
                current_record = current_record.parent_id
            record.root_id = current_record.id
        return True