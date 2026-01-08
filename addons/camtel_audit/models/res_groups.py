# -*- coding: utf-8 -*-

from odoo import models, api


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.model_create_multi
    def create(self, vals_list):
        """Track group creation."""
        groups = super().create(vals_list)

        for group in groups:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='permission_modify',
                    description=f'New security group created: {group.name}',
                    model_name='res.groups',
                    res_id=group.id,
                    resource_name=group.name,
                    severity='warning',
                    success=True,
                    new_values={
                        'name': group.name,
                        'category': group.category_id.name if group.category_id else None,
                        'users': group.users.mapped('login'),
                    }
                )
            except:
                pass

        return groups

    def write(self, vals):
        """Track group modifications."""
        # Store old values
        old_values_list = []
        for group in self:
            old_vals = {}
            if 'name' in vals:
                old_vals['name'] = group.name
            if 'users' in vals:
                old_vals['users'] = group.users.mapped('login')
            if 'implied_ids' in vals:
                old_vals['implied_groups'] = group.implied_ids.mapped('name')
            if 'model_access' in vals:
                old_vals['model_access'] = group.model_access.mapped('name')

            if old_vals:
                old_values_list.append((group.id, group.name, old_vals))

        result = super().write(vals)

        # Log changes
        for group_id, group_name, old_vals in old_values_list:
            try:
                group = self.browse(group_id)
                new_vals = {}

                if 'name' in vals:
                    new_vals['name'] = group.name
                if 'users' in vals:
                    new_vals['users'] = group.users.mapped('login')
                if 'implied_ids' in vals:
                    new_vals['implied_groups'] = group.implied_ids.mapped('name')
                if 'model_access' in vals:
                    new_vals['model_access'] = group.model_access.mapped('name')

                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='permission_modify',
                    description=f'Security group modified: {group_name}',
                    model_name='res.groups',
                    res_id=group_id,
                    resource_name=group_name,
                    old_values=old_vals,
                    new_values=new_vals,
                    severity='warning',
                    success=True,
                )
            except:
                pass

        return result

    def unlink(self):
        """Track group deletion."""
        for group in self:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='permission_modify',
                    description=f'Security group deleted: {group.name}',
                    model_name='res.groups',
                    res_id=group.id,
                    resource_name=group.name,
                    severity='critical',
                    success=True,
                    old_values={
                        'name': group.name,
                        'users': group.users.mapped('login'),
                    }
                )
            except:
                pass

        return super().unlink()
