from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestAccountMoveLineGetViews(TransactionCase):

    def setUp(self):
        super().setUp()
        model = self.env['ir.model']._get('account.move.line')
        self.env['ir.actions.server'].create({
            'name': '__test_bound_action',
            'model_id': model.id,
            'state': 'code',
            'code': '',
            'binding_model_id': model.id,
            'binding_view_types': 'list',
        })

    def test_missing_analytic_view_hides_actions(self):
        view = self.env['ir.ui.view'].search([('name', '=', 'account.move.line.list.missing.analytic')], limit=1)
        res = self.env['account.move.line'].get_views([(view.id, 'list')], {'toolbar': True})
        self.assertEqual(res['views']['list']['toolbar']['action'], [])

    def test_regular_list_view_keeps_actions(self):
        regular = self.env.ref('account.view_move_line_tree')
        res = self.env['account.move.line'].get_views([(regular.id, 'list')], {'toolbar': True})
        self.assertTrue(res['views']['list']['toolbar']['action'])
