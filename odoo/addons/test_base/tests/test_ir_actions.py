from odoo.tests import tagged, common


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestActionBindings(common.TransactionCase):

    def test_bindings(self):
        """ check the action bindings on models """
        Actions = self.env['ir.actions.actions']

        # first make sure there is no bound action
        self.env.ref('base.action_partner_merge').unlink()
        bindings = Actions.get_bindings('res.partner')
        self.assertFalse(bindings.get('action'))
        self.assertFalse(bindings.get('report'))

        # create action bindings, and check the returned bindings
        action1 = self.env.ref('base.action_attachment')
        action2 = self.env.ref('base.ir_default_menu_action')
        action3 = self.env['ir.actions.report'].search([('group_ids', '=', False)], limit=1)
        action1.binding_model_id = action2.binding_model_id \
                                 = action3.binding_model_id \
                                 = self.env['ir.model']._get('res.partner')

        bindings = Actions.get_bindings('res.partner')
        self.assertItemsEqual(
            bindings['action'],
            (action1 + action2).read(['name', 'binding_view_types']),
            "Wrong action bindings",
        )
        self.assertItemsEqual(
            bindings['report'],
            action3.read(['name', 'binding_view_types']),
            "Wrong action bindings",
        )

        # add a group on an action, and check that it is not returned
        group = self.env.ref('base.group_system')
        action2.group_ids += group
        self.env.user.group_ids -= group

        bindings = Actions.get_bindings('res.partner')
        self.assertItemsEqual(
            bindings['action'],
            action1.read(['name', 'binding_view_types']),
            "Wrong action bindings",
        )
        self.assertItemsEqual(
            bindings['report'],
            action3.read(['name', 'binding_view_types']),
            "Wrong action bindings",
        )
