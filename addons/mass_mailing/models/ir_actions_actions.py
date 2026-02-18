from odoo import api, models
from odoo.tools.misc import frozendict


class IrActionsActions(models.Model):
    _inherit = 'ir.actions.actions'

    @api.model
    def _get_bindings(self, model_name):
        """
        Adds the "Send Email" toolbar action if _mailing_enabled is set on the requested model,
        provided the user has at least composer access.
        """
        bindings = super()._get_bindings(model_name)
        if getattr(self.env[model_name], '_mailing_enabled', False) and model_name not in self._get_send_email_binding_excluded_models():
            action = self.env.ref('mass_mailing.action_client_toolbar_mass_mailing', raise_if_not_found=False)
            if action:
                bindings_dict = dict(bindings)
                available_actions = bindings_dict.get('action', ())
                # needs an access check to see if the user has at least composer access (or maybe like, check that it has either mailing access or composer access?)
                new_binding_action = frozendict({
                    'id': action.id,
                    'name': action.sudo().name,  # sudo() necessary to access name & binding_view_types when user is unprivileged
                    'binding_view_types': action.sudo().binding_view_types,
                    'sequence': 4,
                })
                available_actions += (new_binding_action,)
                bindings_dict['action'] = tuple(sorted(available_actions, key=lambda vals: vals.get('sequence', 0)))
                bindings_dict = frozendict(bindings_dict)
                bindings = bindings_dict
        return bindings

    @api.model
    def _get_send_email_binding_excluded_models(self):
        return []
