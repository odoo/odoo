# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _
from odoo.exceptions import AccessError
from odoo.http import request, route
from odoo.addons.web.controllers.action import Action


class AccountAction(Action):

    @route()
    def load(self, action_id, context=None):
        action = super().load(action_id, context=context)
        if (
            action
            and action.get('xml_id') in ('account.action_move_journal_line', 'account.action_account_moves_all', 'account.action_account_moves_all_a')
            and not request.env.user.has_group('account.group_account_readonly')
        ):
            raise AccessError(_("You are not allowed to access the journal entries and items."))
        return action
