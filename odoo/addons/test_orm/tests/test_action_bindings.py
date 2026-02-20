from odoo.tests import tagged, common


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestBindingViewFilters(common.TransactionCase):
    def test_act_window(self):
        A = self.env['tab.a']

        form_act = A.get_views([(False, 'form')], {'toolbar': True})['views']['form']['toolbar']['action']
        self.assertEqual(
            [a['name'] for a in form_act],
            ['Action 1', 'Action 2', 'Action 3'],
            "forms should have all actions")

        list_act = A.get_views([(False, 'list')], {'toolbar': True})['views']['list']['toolbar']['action']
        self.assertEqual(
            [a['name'] for a in list_act],
            ['Action 1', 'Action 3'],
            "lists should not have the form-only action")

        kanban_act = A.get_views([(False, 'kanban')], {'toolbar': True})['views']['kanban']['toolbar']['action']
        self.assertEqual(
            [a['name'] for a in kanban_act],
            ['Action 1'],
            "kanban should only have the universal action")

    def test_act_record(self):
        B = self.env['tab.b']

        form_act = B.get_views([(False, 'form')], {'toolbar': True})['views']['form']['toolbar']['action']
        self.assertEqual(
            [a['name'] for a in form_act],
            ['Record 1', 'Record 2', 'Record 3'],
            "forms should have all actions")

        list_act = B.get_views([(False, 'list')], {'toolbar': True})['views']['list']['toolbar']['action']
        self.assertEqual(
            [a['name'] for a in list_act],
            ['Record 1', 'Record 3'],
            "lists should not have the form-only action")

        kanban_act = B.get_views([(False, 'kanban')], {'toolbar': True})['views']['kanban']['toolbar']['action']
        self.assertEqual(
            [a['name'] for a in kanban_act],
            ['Record 1'],
            "kanban should only have the universal action")
