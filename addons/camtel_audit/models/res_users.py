# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.http import request


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _login(self, credential, user_agent_env):
        """Override login to track login events (Odoo 19+ API)."""
        # Extract login from credential dict
        login = credential.get('login')

        # Call parent method with new API
        auth_info = super()._login(credential, user_agent_env)

        if auth_info and auth_info.get('uid'):
            try:
                # Get IP address from request
                user_ip = None
                if request:
                    user_ip = request.httprequest.remote_addr

                # Log successful login
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='login',
                    description=f'User {login} logged in successfully',
                    user_id=auth_info['uid'],
                    severity='info',
                    success=True,
                    additional_data={
                        'login': login,
                        'user_agent': user_agent_env.get('user_agent') if user_agent_env else None,
                    }
                )
                self.env.cr.commit()  # Commit the log immediately
            except Exception as e:
                # Don't fail login if logging fails
                pass

        return auth_info

    @api.model
    def authenticate(self, credential, user_agent_env):
        """Override authenticate to track failed login attempts (Odoo 19+ API)."""
        # Extract login from credential dict
        login = credential.get('login')

        try:
            return super().authenticate(credential, user_agent_env)
        except Exception as e:
            # Log failed login attempt
            try:
                user_ip = None
                if request:
                    user_ip = request.httprequest.remote_addr

                # Create log with sudo and commit immediately
                self.env['camtel.audit.log'].sudo().create({
                    'event_type': 'login_failed',
                    'description': f'Failed login attempt for user: {login}',
                    'user_id': self.env.ref('base.public_user').id,  # Use public user for failed attempts
                    'user_ip': user_ip,
                    'severity': 'warning',
                    'success': False,
                    'error_message': str(e),
                })
                self.env.cr.commit()
            except:
                pass
            raise

    @api.model_create_multi
    def create(self, vals_list):
        """Track user creation."""
        users = super().create(vals_list)

        for user in users:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='user_create',
                    description=f'New user created: {user.name} ({user.login})',
                    model_name='res.users',
                    res_id=user.id,
                    resource_name=user.name,
                    severity='info',
                    success=True,
                    new_values={
                        'name': user.name,
                        'login': user.login,
                        'email': user.email,
                        'groups': user.group_ids.mapped('name'),
                    }
                )
            except:
                pass

        return users

    def write(self, vals):
        """Track user modifications."""
        # Store old values before update
        old_values_list = []
        for user in self:
            old_values = {
                'name': user.name,
                'login': user.login,
                'email': user.email,
                'active': user.active,
                'groups': user.group_ids.mapped('name'),
            }
            old_values_list.append((user, old_values))

        result = super().write(vals)

        # Log the changes
        for user, old_values in old_values_list:
            try:
                new_values = {}
                changed_fields = []

                # Check what changed
                if 'name' in vals:
                    new_values['name'] = user.name
                    changed_fields.append('name')
                if 'login' in vals:
                    new_values['login'] = user.login
                    changed_fields.append('login')
                if 'email' in vals:
                    new_values['email'] = user.email
                    changed_fields.append('email')
                if 'active' in vals:
                    new_values['active'] = user.active
                    changed_fields.append('active')
                if 'group_ids' in vals:
                    new_values['groups'] = user.group_ids.mapped('name')
                    changed_fields.append('groups')

                # Determine event type and severity
                event_type = 'user_modify'
                severity = 'info'
                description = f'User modified: {user.name}'

                if 'active' in vals and not vals['active']:
                    event_type = 'user_deactivate'
                    severity = 'warning'
                    description = f'User deactivated: {user.name}'
                elif 'group_ids' in vals:
                    event_type = 'group_modify'
                    severity = 'warning'
                    description = f'User groups modified for: {user.name}'

                if changed_fields:
                    self.env['camtel.audit.log'].sudo().create_log(
                        event_type=event_type,
                        description=description,
                        model_name='res.users',
                        res_id=user.id,
                        resource_name=user.name,
                        old_values=old_values,
                        new_values=new_values,
                        severity=severity,
                        success=True,
                        additional_data={'changed_fields': changed_fields}
                    )
            except:
                pass

        return result

    def unlink(self):
        """Track user deletion."""
        for user in self:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='user_deactivate',
                    description=f'User deleted: {user.name} ({user.login})',
                    model_name='res.users',
                    res_id=user.id,
                    resource_name=user.name,
                    severity='critical',
                    success=True,
                    old_values={
                        'name': user.name,
                        'login': user.login,
                        'email': user.email,
                    }
                )
            except:
                pass

        return super().unlink()
