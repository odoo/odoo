# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.http import Controller, route, request
from odoo.tools.translate import _
import operator

OPERATORS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '%': operator.mod,
}


class View(Controller):

    @route('/web/view/edit_custom', type='jsonrpc', auth="user")
    def edit_custom(self, custom_id, arch):
        """
        Edit a custom view

        :param int custom_id: the id of the edited custom view
        :param str arch: the edited arch of the custom view
        :returns: dict with acknowledged operation (result set to True)
        """
        custom_view = request.env['ir.ui.view.custom'].sudo().browse(custom_id)
        if not custom_view.user_id == request.env.user:
            raise AccessError(_(
                "Custom view %(view)s does not belong to user %(user)s",
                view=custom_id,
                user=self.env.user.login,
            ))
        custom_view.write({'arch': arch})
        return {'result': True}

    @route('/web/view/save_multi', type='jsonrpc', auth="user")
    def save_multi(self, model, ids, changes, context=None):
        """
        Update multiple records with direct values or field operations.

        This method allows bulk updates on records of a given Odoo model.
        Changes can either be direct value assignments or arithmetic operations
        on numeric fields using a FieldOperator dict.

        Parameters:
            model (str): The technical name of the Odoo model (e.g., 'res.partner').
            ids (list[int]): List of record IDs to update.
            changes (dict): A dictionary of field updates.
                Each key is a field name. The value can be:
                    - a direct value to assign to the field
                    - or a dict with keys:
                        - 'operator' (str): One of '+', '-', '*', '/', '%'
                        - 'increment' (float|int): The value to apply using the operator
            context (dict, optional): Optional context dictionary to pass to the environment.

        Returns:
            dict: A dictionary with:
                - 'result': True if updates succeeded
                - 'updated': A mapping of record IDs to the list of updated fields
                - or 'error': An error message string in case of failure

        Example:
            save_multi(
                model='res.partner',
                ids=[1, 2],
                changes={
                    'credit_limit': {'operator': '+', 'increment': 100},
                    'comment': 'Important client'
                },
                context={'lang': 'en_US'}
            )

        Raises:
            Returns an error dictionary if invalid parameters are passed or if an exception occurs during update.
        """
        if not isinstance(model, str) or not isinstance(ids, list) or not all(isinstance(i, int) for i in ids) or not isinstance(changes, dict):
            return {'error': 'Invalid parameters'}

        Model = request.env[model].with_context(**(context or {}))
        records = Model.browse(ids)
        updated = {}

        for record in records:
            updates = {}

            for field, change in changes.items():
                if not hasattr(record, field):
                    continue

                current_val = record[field]

                if isinstance(change, dict) and 'operator' in change and 'increment' in change:
                    operator_symbol = change['operator']
                    increment = change['increment']

                    if operator_symbol not in OPERATORS:
                        continue

                    if isinstance(current_val, (int, float)):
                        try:
                            new_val = OPERATORS[operator_symbol](current_val, float(increment))
                            updates[field] = new_val
                        except (TypeError, ValueError, ZeroDivisionError) as e:
                            return {'error': str(e)}
                    else:
                        continue
                else:
                    updates[field] = change

            if updates:
                record.write(updates)
                updated[record.id] = list(updates.keys())

        return {'result': True, 'updated': updated}
