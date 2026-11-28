# -*- coding: utf-8 -*-

from odoo import models, api


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @api.model_create_multi
    def create(self, vals_list):
        """Track access rights creation."""
        accesses = super().create(vals_list)

        for access in accesses:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='access_rights_modify',
                    description=f'Access rights created: {access.name} for model {access.model_id.model}',
                    model_name='ir.model.access',
                    res_id=access.id,
                    resource_name=access.name,
                    severity='warning',
                    success=True,
                    new_values={
                        'name': access.name,
                        'model': access.model_id.model,
                        'group': access.group_id.name if access.group_id else 'All Users',
                        'perm_read': access.perm_read,
                        'perm_write': access.perm_write,
                        'perm_create': access.perm_create,
                        'perm_unlink': access.perm_unlink,
                    }
                )
            except:
                pass

        return accesses

    def write(self, vals):
        """Track access rights modifications."""
        # Store old values
        old_values_list = []
        tracked_fields = ['perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'group_id', 'active']

        if any(field in vals for field in tracked_fields):
            for access in self:
                old_vals = {
                    'model': access.model_id.model,
                    'group': access.group_id.name if access.group_id else 'All Users',
                    'perm_read': access.perm_read,
                    'perm_write': access.perm_write,
                    'perm_create': access.perm_create,
                    'perm_unlink': access.perm_unlink,
                    'active': access.active,
                }
                old_values_list.append((access.id, access.name, old_vals))

        result = super().write(vals)

        # Log changes
        for access_id, access_name, old_vals in old_values_list:
            try:
                access = self.browse(access_id)
                new_vals = {
                    'model': access.model_id.model,
                    'group': access.group_id.name if access.group_id else 'All Users',
                    'perm_read': access.perm_read,
                    'perm_write': access.perm_write,
                    'perm_create': access.perm_create,
                    'perm_unlink': access.perm_unlink,
                    'active': access.active,
                }

                # Determine severity based on what changed
                severity = 'warning'
                if not vals.get('active', True):
                    severity = 'critical'  # Disabling access is critical

                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='access_rights_modify',
                    description=f'Access rights modified: {access_name} for model {access.model_id.model}',
                    model_name='ir.model.access',
                    res_id=access_id,
                    resource_name=access_name,
                    old_values=old_vals,
                    new_values=new_vals,
                    severity=severity,
                    success=True,
                )
            except:
                pass

        return result

    def unlink(self):
        """Track access rights deletion."""
        for access in self:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='access_rights_modify',
                    description=f'Access rights deleted: {access.name} for model {access.model_id.model}',
                    model_name='ir.model.access',
                    res_id=access.id,
                    resource_name=access.name,
                    severity='critical',
                    success=True,
                    old_values={
                        'name': access.name,
                        'model': access.model_id.model,
                        'group': access.group_id.name if access.group_id else 'All Users',
                        'perm_read': access.perm_read,
                        'perm_write': access.perm_write,
                        'perm_create': access.perm_create,
                        'perm_unlink': access.perm_unlink,
                    }
                )
            except:
                pass

        return super().unlink()


class IrRule(models.Model):
    """Track record rules (row-level security) modifications."""
    _inherit = 'ir.rule'

    @api.model_create_multi
    def create(self, vals_list):
        """Track record rule creation."""
        rules = super().create(vals_list)

        for rule in rules:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='permission_modify',
                    description=f'Record rule created: {rule.name} for model {rule.model_id.model}',
                    model_name='ir.rule',
                    res_id=rule.id,
                    resource_name=rule.name,
                    severity='warning',
                    success=True,
                    new_values={
                        'name': rule.name,
                        'model': rule.model_id.model,
                        'groups': rule.groups.mapped('name'),
                        'domain_force': rule.domain_force,
                        'perm_read': rule.perm_read,
                        'perm_write': rule.perm_write,
                        'perm_create': rule.perm_create,
                        'perm_unlink': rule.perm_unlink,
                    }
                )
            except:
                pass

        return rules

    def write(self, vals):
        """Track record rule modifications."""
        old_values_list = []
        tracked_fields = ['domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active']

        if any(field in vals for field in tracked_fields):
            for rule in self:
                old_vals = {
                    'model': rule.model_id.model,
                    'groups': rule.groups.mapped('name'),
                    'domain_force': rule.domain_force,
                    'perm_read': rule.perm_read,
                    'perm_write': rule.perm_write,
                    'perm_create': rule.perm_create,
                    'perm_unlink': rule.perm_unlink,
                    'active': rule.active,
                }
                old_values_list.append((rule.id, rule.name, old_vals))

        result = super().write(vals)

        for rule_id, rule_name, old_vals in old_values_list:
            try:
                rule = self.browse(rule_id)
                new_vals = {
                    'model': rule.model_id.model,
                    'groups': rule.groups.mapped('name'),
                    'domain_force': rule.domain_force,
                    'perm_read': rule.perm_read,
                    'perm_write': rule.perm_write,
                    'perm_create': rule.perm_create,
                    'perm_unlink': rule.perm_unlink,
                    'active': rule.active,
                }

                severity = 'warning'
                if not vals.get('active', True):
                    severity = 'critical'

                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='permission_modify',
                    description=f'Record rule modified: {rule_name} for model {rule.model_id.model}',
                    model_name='ir.rule',
                    res_id=rule_id,
                    resource_name=rule_name,
                    old_values=old_vals,
                    new_values=new_vals,
                    severity=severity,
                    success=True,
                )
            except:
                pass

        return result

    def unlink(self):
        """Track record rule deletion."""
        for rule in self:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='permission_modify',
                    description=f'Record rule deleted: {rule.name} for model {rule.model_id.model}',
                    model_name='ir.rule',
                    res_id=rule.id,
                    resource_name=rule.name,
                    severity='critical',
                    success=True,
                    old_values={
                        'name': rule.name,
                        'model': rule.model_id.model,
                        'groups': rule.groups.mapped('name'),
                        'domain_force': rule.domain_force,
                    }
                )
            except:
                pass

        return super().unlink()
