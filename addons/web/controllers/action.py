# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import _
from odoo.exceptions import UserError, MissingError, AccessError
from odoo.http import Controller, request, route
from .utils import clean_action
from werkzeug.exceptions import BadRequest


class MissingActionError(UserError):
    """Missing Action.

    .. admonition:: Example

        When you try to read on a non existing record.
    """


class Action(Controller):

    @route('/web/action/load', type='json', auth='user', readonly=True)
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
                raise MissingActionError(_("The action “%s” does not exist.", action_id)) from exc

        base_action = Actions.browse([action_id]).sudo().read(['type'])
        if not base_action:
            raise MissingActionError(_("The action “%s” does not exist", action_id))
        action_type = base_action[0]['type']
        if action_type == 'ir.actions.report':
            request.update_context(bin_size=True)
        if action_type == 'ir.actions.act_window':
            result = request.env[action_type].sudo().browse([action_id])._get_action_dict()
            return clean_action(result, env=request.env) if result else False
        result = request.env[action_type].sudo().browse([action_id]).read()
        return clean_action(result[0], env=request.env) if result else False

    @route('/web/action/run', type='json', auth="user")
    def run(self, action_id, context=None):
        if context:
            request.update_context(**context)
        action = request.env['ir.actions.server'].browse([action_id])
        result = action.run()
        return clean_action(result, env=action.env) if result else False

    @route('/web/action/load_breadcrumbs', type='json', auth='user', readonly=True)
    def load_breadcrumbs(self, actions):
        results = []
        for idx, action in enumerate(actions):
            record_id = action.get('resId')
            try:
                if action.get('action'):
                    act = self.load(action.get('action'))
                    if act['type'] == 'ir.actions.server':
                        if act['path']:
                            act = request.env['ir.actions.server'].browse(act['id']).run()
                        else:
                            results.append({'error': 'A server action must have a path to be restored'})
                            continue
                    if not act.get('display_name'):
                        act['display_name'] = act['name']
                    # client actions don't have multi-record views, so we can't go further to the next controller
                    if act['type'] == 'ir.actions.client' and idx + 1 < len(actions) and action.get('action') == actions[idx + 1].get('action'):
                        continue
                    if record_id:
                        # some actions may not have a res_model (e.g. a client action)
                        if record_id == 'new':
                            results.append({'display_name': _("New"), 'view_typpe': 'form'})
                        elif act['res_model']:
                            results.append({'display_name': request.env[act['res_model']].browse(record_id).display_name, 'view_type': 'form'})
                        else:
                            # If an action don't have a res_model, we don't put the view_type, is probably a clien action
                            results.append({'display_name': act['display_name']})
                    else:
                        res = {}
                        if act['res_model'] and act['type'] != 'ir.actions.client':
                            request.env[act['res_model']].check_access_rights('read')
                            # action shouldn't be available on its own if it doesn't have multi-record views
                            name = act['display_name'] if any(view[1] != 'form' and view[1] != 'search' for view in act['views']) else None
                        else:
                            name = act['display_name']
                        res['display_name'] = name
                        if act.get('views'):
                            res['view_type'] = act['views'][0][1]
                        results.append(res)
                elif action.get('model'):
                    Model = request.env[action.get('model')]
                    if record_id:
                        results.append({'display_name': Model.browse(record_id).display_name, 'view_type': 'form'})
                    else:
                        # This case cannot be produced by the web client
                        raise BadRequest('Actions with a model should also have a resId')
                else:
                    raise BadRequest('Actions should have either an action (id or path) or a model')
            except (MissingActionError, MissingError, AccessError) as exc:
                results.append({'error': str(exc)})
        return results
