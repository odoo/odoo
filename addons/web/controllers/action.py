# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import _
from odoo.exceptions import AccessError, MissingError
from odoo.http import Controller, request, route
from .utils import clean_action
from werkzeug.exceptions import BadRequest


class Action(Controller):

    @route('/web/action/load', type='json', auth='user')
    def load(self, action_id, context=None):
        if context:
            request.update_context(**context)
        Actions = request.env['ir.actions.actions']
        try:
            action_id = int(action_id)
        except ValueError:
            try:
                if '.' in action_id:
                    action = request.env.ref(action_id)
                    assert action._name.startswith('ir.actions.')
                else:
                    action = Actions.sudo().search([('path', '=', action_id)], limit=1)
                    assert action
                action_id = action.id
            except Exception as exc:
                raise MissingError(_("The action %r does not exist.", action_id)) from exc

        base_action = Actions.browse([action_id]).sudo().read(['type'])
        if base_action:
            action_type = base_action[0]['type']
            if action_type == 'ir.actions.report':
                request.update_context(bin_size=True)
            if action_type == 'ir.actions.server':
                action = request.env["ir.actions.server"].browse([action_id])
                result = action.run()
                parent_path = action.sudo().path
                if parent_path:
                    result['path'] = parent_path
                return clean_action(result, env=action.env) if result else {'type': 'ir.actions.act_window_close'}
            result = request.env[action_type].sudo().browse([action_id]).read()
            return clean_action(result[0], env=request.env) if result else False

    @route('/web/action/load_breadcrumbs', type='json', auth='user', readonly=True)
    def load_breadcrumbs(self, actions):
        display_names = []
        for idx, action in enumerate(actions):
            record_id = action.get('resId')
            try:
                if action.get('action'):
                    act = self.load(action.get('action'))
                    if act['type'] == 'ir.actions.server':
                        if act['path']:
                            act = request.env['ir.actions.server'].browse(act['id']).run()
                        else:
                            display_names.append({'error': 'A server action must have a path to be restored'})
                            continue
                    if not act.get('display_name'):
                        act['display_name'] = act['name']
                    # client actions don't have multi-record views, so we can't go further to the next controller
                    if act['type'] == 'ir.actions.client' and idx + 1 < len(actions) and action.get('action') == actions[idx + 1].get('action'):
                        continue
                    if record_id:
                        # some actions may not have a res_model (e.g. a client action)
                        if act['res_model']:
                            display_names.append(request.env[act['res_model']].browse(record_id).display_name)
                        else:
                            display_names.append(act['display_name'])
                    else:
                        if act['res_model'] and act['type'] != 'ir.actions.client':
                            request.env[act['res_model']].check_access_rights('read')
                            # action shouldn't be available on its own if it doesn't have multi-record views
                            name = act['display_name'] if any(view[1] != 'form' and view[1] != 'search' for view in act['views']) else None
                        else:
                            name = act['display_name']
                        display_names.append(name)
                elif action.get('model'):
                    Model = request.env[action.get('model')]
                    if record_id:
                        display_names.append(Model.browse(record_id).display_name)
                    else:
                        # This case cannot be produced by the web client
                        raise BadRequest('Actions with a model should also have a resId')
                else:
                    raise BadRequest('Actions should have either an action (id or path) or a model')
            except (MissingError, AccessError) as exc:
                display_names.append({'error': str(exc)})
        return display_names
