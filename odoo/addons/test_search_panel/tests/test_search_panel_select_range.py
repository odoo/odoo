# -*- coding: utf-8 -*-
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestSelectRange(odoo.tests.TransactionCase):

    def setUp(self):
        super().setUp()
        self.SourceModel = self.env['test_search_panel.source_model']
        self.TargetModel = self.env['test_search_panel.category_target_model']
        self.TargetModelNoParentName = self.env['test_search_panel.category_target_model_no_parent_name']

    # Many2one

    def test_many2one_empty(self):
        result = self.SourceModel.search_panel_select_range('folder_id')
        self.assertEqual(
            result,
            {
                'parent_field': 'parent_name_id',
                'values': [],
            }
        )

    def test_many2one(self):
        parent_folders = self.TargetModel.create([
            {'name': 'Folder 1', },
            {'name': 'Folder 2', },
        ])

        f1_id, f2_id = parent_folders.ids

        children_folders = self.TargetModel.create([
            {'name': 'Folder 3', 'parent_name_id': f1_id, },
            {'name': 'Folder 4', 'parent_name_id': f2_id, },
        ])

        f3_id, f4_id = children_folders.ids

        records = self.SourceModel.create([
            {'name': 'Rec 1', 'folder_id': f1_id, },
            {'name': 'Rec 2', 'folder_id': f3_id, },
            {'name': 'Rec 3', 'folder_id': f4_id, },
            {'name': 'Rec 4', },
        ])

        r1_id, _, r3_id, _ = records.ids

        # counters
        result = self.SourceModel.search_panel_select_range('folder_id')
        self.assertEqual(
            result['values'],
            [
                {'__count': 2, 'display_name': 'Folder 1',
                    'id': f1_id, 'parent_name_id': False, },
                {'__count': 1, 'display_name': 'Folder 2',
                    'id': f2_id, 'parent_name_id': False, },
                {'__count': 1, 'display_name': 'Folder 3',
                    'id': f3_id, 'parent_name_id': f1_id, },
                {'__count': 1, 'display_name': 'Folder 4',
                    'id': f4_id, 'parent_name_id': f2_id, },
            ]
        )

        # counters and search domain
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            search_domain=[['id', 'in', [r1_id, r3_id]]],
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 1, 'display_name': 'Folder 1',
                    'id': f1_id, 'parent_name_id': False, },
                {'__count': 1, 'display_name': 'Folder 2',
                    'id': f2_id, 'parent_name_id': False, },
                {'__count': 0, 'display_name': 'Folder 3',
                    'id': f3_id, 'parent_name_id': f1_id, },
                {'__count': 1, 'display_name': 'Folder 4',
                    'id': f4_id, 'parent_name_id': f2_id, },
            ]
        )

        # no counters
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            disable_counters=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 0, 'display_name': 'Folder 1',
                    'id': f1_id, 'parent_name_id': False, },
                {'__count': 0, 'display_name': 'Folder 2',
                    'id': f2_id, 'parent_name_id': False, },
                {'__count': 0, 'display_name': 'Folder 3',
                    'id': f3_id, 'parent_name_id': f1_id, },
                {'__count': 0, 'display_name': 'Folder 4',
                    'id': f4_id, 'parent_name_id': f2_id, },
            ]
        )

        # no counters and search domain
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            disable_counters=True,
            search_domain=[['id', 'in', [r1_id, r3_id]]],
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 0, 'display_name': 'Folder 1',
                    'id': f1_id, 'parent_name_id': False, },
                {'__count': 0, 'display_name': 'Folder 2',
                    'id': f2_id, 'parent_name_id': False, },
                {'__count': 0, 'display_name': 'Folder 3',
                    'id': f3_id, 'parent_name_id': f1_id, },
                {'__count': 0, 'display_name': 'Folder 4',
                    'id': f4_id, 'parent_name_id': f2_id, },
            ]
        )

    def test_many2one_deep_hierarchy(self):
        folders_level_0 = self.TargetModel.create([
            {'name': 'Folder 1', },
            {'name': 'Folder 2', },
            {'name': 'Folder 3', },
        ])

        f1_id, f2_id, f3_id = folders_level_0.ids

        folders_level_1 = self.TargetModel.create([
            {'name': 'Folder 4', 'parent_name_id': f1_id, },
            {'name': 'Folder 5', 'parent_name_id': f2_id, },
            {'name': 'Folder 6', 'parent_name_id': f2_id, },
        ])

        f4_id, f5_id, f6_id = folders_level_1.ids

        folders_level_2 = self.TargetModel.create([
            {'name': 'Folder 7', 'parent_name_id': f4_id, },
            {'name': 'Folder 8', 'parent_name_id': f6_id, },
        ])

        f7_id, f8_id = folders_level_2.ids

        folders_level_3 = self.TargetModel.create([
            {'name': 'Folder 9', 'parent_name_id': f8_id, },
            {'name': 'Folder 10', 'parent_name_id': f8_id, },
        ])

        f9_id, f10_id = folders_level_3.ids

        self.SourceModel.create([
            {'name': 'Rec 1', 'folder_id': f1_id, },
            {'name': 'Rec 2', 'folder_id': f6_id, },
            {'name': 'Rec 3', 'folder_id': f7_id, },
            {'name': 'Rec 4', 'folder_id': f7_id, },
            {'name': 'Rec 5', 'folder_id': f9_id, },
            {'name': 'Rec 6', 'folder_id': f10_id, },
        ])

        # counters
        result = self.SourceModel.search_panel_select_range('folder_id')
        self.assertEqual(
            result['values'],
            [
                {'__count': 3, 'display_name': 'Folder 1',
                    'id': f1_id, 'parent_name_id': False, },
                {'__count': 1, 'display_name': 'Folder 10',
                    'id': f10_id, 'parent_name_id': f8_id, },
                {'__count': 3, 'display_name': 'Folder 2',
                    'id': f2_id, 'parent_name_id': False, },
                {'__count': 0, 'display_name': 'Folder 3',
                    'id': f3_id, 'parent_name_id': False, },
                {'__count': 2, 'display_name': 'Folder 4',
                    'id': f4_id, 'parent_name_id': f1_id, },
                {'__count': 0, 'display_name': 'Folder 5',
                    'id': f5_id, 'parent_name_id': f2_id, },
                {'__count': 3, 'display_name': 'Folder 6',
                    'id': f6_id, 'parent_name_id': f2_id, },
                {'__count': 2, 'display_name': 'Folder 7',
                    'id': f7_id, 'parent_name_id': f4_id, },
                {'__count': 2, 'display_name': 'Folder 8',
                    'id': f8_id, 'parent_name_id': f6_id, },
                {'__count': 1, 'display_name': 'Folder 9',
                    'id': f9_id, 'parent_name_id': f8_id, },
            ]
        )

    # Many2one no parent name

    def test_many2one_empty_no_parent_name(self):
        result = self.SourceModel.search_panel_select_range('categ_id')
        self.assertEqual(
            result,
            {
                'parent_field': False,
                'values': [],
            }
        )

    def test_many2one_no_parent_name(self):
        categories = self.TargetModelNoParentName.create([
            {'name': 'Cat 1'},
            {'name': 'Cat 2'},
            {'name': 'Cat 3'},
        ])

        c1_id, c2_id, c3_id = categories.ids

        records = self.SourceModel.create([
            {'name': 'Rec 1', 'categ_id': c1_id, },
            {'name': 'Rec 2', 'categ_id': c2_id, },
            {'name': 'Rec 3', 'categ_id': c2_id, },
            {'name': 'Rec 4', },
        ])

        r1_id, _, r3_id, _ = records.ids

        # counters
        result = self.SourceModel.search_panel_select_range('categ_id')
        self.assertEqual(
            result['values'],
            [
                {'__count': 0, 'display_name': 'Cat 3', 'id': c3_id, },
                {'__count': 2, 'display_name': 'Cat 2', 'id': c2_id, },
                {'__count': 1, 'display_name': 'Cat 1', 'id': c1_id, },
            ]
        )

        # counters and search domain
        result = self.SourceModel.search_panel_select_range(
            'categ_id',
            search_domain=[['id', 'in', [r1_id, r3_id]]],
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 0, 'display_name': 'Cat 3', 'id': c3_id, },
                {'__count': 1, 'display_name': 'Cat 2', 'id': c2_id, },
                {'__count': 1, 'display_name': 'Cat 1', 'id': c1_id, },
            ]
        )

        # no counters
        result = self.SourceModel.search_panel_select_range(
            'categ_id',
            disable_counters=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 0, 'display_name': 'Cat 3', 'id': c3_id, },
                {'__count': 0, 'display_name': 'Cat 2', 'id': c2_id, },
                {'__count': 0, 'display_name': 'Cat 1', 'id': c1_id, },
            ]
        )

        # no counters and search domain
        result = self.SourceModel.search_panel_select_range(
            'categ_id',
            disable_counters=True,
            search_domain=[['id', 'in', [r1_id, r3_id]]],
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 0, 'display_name': 'Cat 3', 'id': c3_id, },
                {'__count': 0, 'display_name': 'Cat 2', 'id': c2_id, },
                {'__count': 0, 'display_name': 'Cat 1', 'id': c1_id, },
            ]
        )

    # Selection case

    def test_selection_empty(self):
        result = self.SourceModel.search_panel_select_range('state')
        self.assertEqual(
            result,
            {
                'parent_field': False,
                'values': [
                    {'display_name': 'A', 'id': 'a', '__count': 0, },
                    {'display_name': 'B', 'id': 'b', '__count': 0, },
                ]
            }
        )

    def test_selection(self):
        records = self.SourceModel.create([
            {'name': 'Rec 1', 'state': 'a', },
            {'name': 'Rec 2', 'state': 'a', },
        ])

        r1_id, _ = records.ids

        # counters
        result = self.SourceModel.search_panel_select_range('state')
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'A', 'id': 'a', '__count': 2, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )

        # no counters
        result = self.SourceModel.search_panel_select_range(
            'state',
            disable_counters=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'A', 'id': 'a', '__count': 0, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )

        # counters and search domain
        result = self.SourceModel.search_panel_select_range(
            'state',
            search_domain=[['id', '=', r1_id]],
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'A', 'id': 'a', '__count': 1, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )

        # no counters and search domain
        result = self.SourceModel.search_panel_select_range(
            'state',
            disable_counters=True,
            search_domain=[['id', '=', r1_id]],
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'A', 'id': 'a', '__count': 0, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )
