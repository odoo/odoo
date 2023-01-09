# -*- coding: utf-8 -*-
import odoo.tests

SEARCH_PANEL_ERROR = {'error_msg': "Too many items to display.", }


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

        # counters, expand, and hierarchization
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            enable_counters=True,
            expand=True,
        )
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

        # counters, expand, hierarchization, and search domain
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            enable_counters=True,
            expand=True,
            search_domain=[['id', 'in', [r1_id, r3_id]]],  # impact expected
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

        # counters, expand, hierarchization, and reached limit
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            enable_counters=True,
            expand=True,
            limit=2,
        )
        self.assertEqual(result, SEARCH_PANEL_ERROR, )

        # counters, expand, hierarchization, and unreached limit
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            enable_counters=True,
            expand=True,
            limit=200,
        )
        self.assertEqual(
            result,
            {
                'parent_field': 'parent_name_id',
                'values': [
                    {'__count': 2, 'display_name': 'Folder 1',
                        'id': f1_id, 'parent_name_id': False, },
                    {'__count': 1, 'display_name': 'Folder 2',
                        'id': f2_id, 'parent_name_id': False, },
                    {'__count': 1, 'display_name': 'Folder 3',
                        'id': f3_id, 'parent_name_id': f1_id, },
                    {'__count': 1, 'display_name': 'Folder 4',
                        'id': f4_id, 'parent_name_id': f2_id, },
                ],
            }
        )

        # counters, expand, and no hierarchization
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            enable_counters=True,
            expand=True,
            hierarchize=False,
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 1, 'display_name': 'Folder 1', 'id': f1_id, },
                {'__count': 0, 'display_name': 'Folder 2', 'id': f2_id, },
                {'__count': 1, 'display_name': 'Folder 3', 'id': f3_id, },
                {'__count': 1, 'display_name': 'Folder 4', 'id': f4_id, },
            ]
        )
        self.assertEqual(
            result['parent_field'],
            False
        )

        # no counters, expand, and hierarchization
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            expand=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Folder 1',
                    'id': f1_id, 'parent_name_id': False, },
                {'display_name': 'Folder 2',
                    'id': f2_id, 'parent_name_id': False, },
                {'display_name': 'Folder 3',
                    'id': f3_id, 'parent_name_id': f1_id, },
                {'display_name': 'Folder 4',
                    'id': f4_id, 'parent_name_id': f2_id, },
            ]
        )

        # no counters, expand, hierarchization, and search domain
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            expand=True,
            search_domain=[['id', 'in', [r1_id, r3_id]]],  # no impact expected
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Folder 1',
                    'id': f1_id, 'parent_name_id': False, },
                {'display_name': 'Folder 2',
                    'id': f2_id, 'parent_name_id': False, },
                {'display_name': 'Folder 3',
                    'id': f3_id, 'parent_name_id': f1_id, },
                {'display_name': 'Folder 4',
                    'id': f4_id, 'parent_name_id': f2_id, },
            ]
        )

        # no counters, expand, and no hierarchization
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            expand=True,
            hierarchize=False,
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Folder 1',
                    'id': f1_id, },
                {'display_name': 'Folder 2',
                    'id': f2_id, },
                {'display_name': 'Folder 3',
                    'id': f3_id, },
                {'display_name': 'Folder 4',
                    'id': f4_id, },
            ]
        )

        # counters, no expand, and hierarchization
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            enable_counters=True,
        )
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
        self.assertEqual(
            result['parent_field'],
            'parent_name_id'
        )

        # counters, no expand, and no hierarchization
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            enable_counters=True,
            hierarchize=False,
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 1, 'display_name': 'Folder 1', 'id': f1_id, },
                {'__count': 1, 'display_name': 'Folder 3', 'id': f3_id, },
                {'__count': 1, 'display_name': 'Folder 4', 'id': f4_id, },
            ]
        )
        self.assertEqual(
            result['parent_field'],
            False
        )

        # counters, no expand, no hierarchization, and category_domain
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            enable_counters=True,
            hierarchize=False,
            category_domain=[['id', 'in', [r1_id, r3_id]]],  # impact expected
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 1, 'display_name': 'Folder 1', 'id': f1_id, },
                {'__count': 0, 'display_name': 'Folder 3', 'id': f3_id, },
                {'__count': 1, 'display_name': 'Folder 4', 'id': f4_id, },
            ]
        )
        self.assertEqual(
            result['parent_field'],
            False
        )

        # counters, no expand, no hierarchization, and limit
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            enable_counters=True,
            hierarchize=False,
            limit=2,
        )
        self.assertEqual(result, SEARCH_PANEL_ERROR, )

        # no counters, no expand, and hierarchization
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            hierarchize=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Folder 1',
                    'id': f1_id, 'parent_name_id': False, },
                {'display_name': 'Folder 2',
                    'id': f2_id, 'parent_name_id': False, },
                {'display_name': 'Folder 3',
                    'id': f3_id, 'parent_name_id': f1_id, },
                {'display_name': 'Folder 4',
                    'id': f4_id, 'parent_name_id': f2_id, },
            ]
        )
        self.assertEqual(
            result['parent_field'],
            'parent_name_id'
        )

        # no counters, no expand, and hierarchization
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            search_domain=[(0, '=', 1)],
        )
        self.assertEqual(
            result,
            {'parent_field': 'parent_name_id', 'values': [], } # should not be a SEARCH_PANEL_ERROR
        )

        # no counters, no expand, and no hierarchization
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            hierarchize=False,
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Folder 1', 'id': f1_id, },
                {'display_name': 'Folder 3', 'id': f3_id, },
                {'display_name': 'Folder 4', 'id': f4_id, },
            ]
        )
        self.assertEqual(
            result['parent_field'],
            False
        )

        # no counters, no expand, no hierarchization, and category_domain
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            hierarchize=False,
            category_domain=[['id', 'in', [r1_id, r3_id]]],  # no impact expected

        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Folder 1', 'id': f1_id, },
                {'display_name': 'Folder 3', 'id': f3_id, },
                {'display_name': 'Folder 4', 'id': f4_id, },
            ]
        )
        self.assertEqual(
            result['parent_field'],
            False
        )

        # no counters, no expand, no hierarchization, and comodel_domain
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            hierarchize=False,
            comodel_domain=[['id', 'in', [f1_id, f4_id]]]
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Folder 1', 'id': f1_id, },
                {'display_name': 'Folder 4', 'id': f4_id, },
            ]
        )
        self.assertEqual(
            result['parent_field'],
            False
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

        """
        The folder tree is like this (the numbers are the local counts)

                f1_id (1)       f2_id (0)           f3_id (0)
                    |          /         \
                f4_id (0)  f5_id (0)  f6_id (1)
                    |                     |
                f7_id (2)             f8_id (0)
                                     /         \
                                f9_id (1)  f10_id (1)
        """

        # counters, expand, and hierarchization
        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            enable_counters=True,
            expand=True,
        )
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

        # no counters, no expand, hierarchization, and comodel_domain

        # We add a folder with a single record in it and declare it out of
        # comodel_domain. That folder should not appear in the final values.
        extra_folder_level_0 = self.TargetModel.create([
            {'name': 'Folder 11', 'parent_name_id': False, },
        ])

        f11_id = extra_folder_level_0.id

        self.SourceModel.create([
            {'name': 'Rec 7', 'folder_id': f11_id, },
        ])

        result = self.SourceModel.search_panel_select_range(
            'folder_id',
            comodel_domain=[('id', 'not in', [f8_id, f11_id])
                            ],  # impact expected
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Folder 1', 'id': f1_id, 'parent_name_id': False, },
                {'display_name': 'Folder 2', 'id': f2_id, 'parent_name_id': False, },
                {'display_name': 'Folder 4', 'id': f4_id, 'parent_name_id': f1_id, },
                {'display_name': 'Folder 6', 'id': f6_id, 'parent_name_id': f2_id, },
                {'display_name': 'Folder 7', 'id': f7_id, 'parent_name_id': f4_id, },
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

        # counters and expand
        result = self.SourceModel.search_panel_select_range(
            'categ_id',
            enable_counters=True,
            expand=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 0, 'display_name': 'Cat 3', 'id': c3_id, },
                {'__count': 2, 'display_name': 'Cat 2', 'id': c2_id, },
                {'__count': 1, 'display_name': 'Cat 1', 'id': c1_id, },
            ]
        )

        # counters, expand, and search domain
        result = self.SourceModel.search_panel_select_range(
            'categ_id',
            enable_counters=True,
            expand=True,
            search_domain=[['id', 'in', [r1_id, r3_id]]],  # impact expected
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 0, 'display_name': 'Cat 3', 'id': c3_id, },
                {'__count': 1, 'display_name': 'Cat 2', 'id': c2_id, },
                {'__count': 1, 'display_name': 'Cat 1', 'id': c1_id, },
            ]
        )

        # no counters and expand
        result = self.SourceModel.search_panel_select_range(
            'categ_id',
            expand=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Cat 3', 'id': c3_id, },
                {'display_name': 'Cat 2', 'id': c2_id, },
                {'display_name': 'Cat 1', 'id': c1_id, },
            ]
        )

        # no counters, expand, and search domain
        result = self.SourceModel.search_panel_select_range(
            'categ_id',
            expand=True,
            search_domain=[['id', 'in', [r1_id, r3_id]]],  # no impact expected
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Cat 3', 'id': c3_id, },
                {'display_name': 'Cat 2', 'id': c2_id, },
                {'display_name': 'Cat 1', 'id': c1_id, },
            ]
        )

        # counters and no expand
        result = self.SourceModel.search_panel_select_range(
            'categ_id',
            enable_counters=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 2, 'display_name': 'Cat 2', 'id': c2_id, },
                {'__count': 1, 'display_name': 'Cat 1', 'id': c1_id, },
            ]
        )
        self.assertEqual(
            result['parent_field'],
            False
        )

        # no counters and no expand
        result = self.SourceModel.search_panel_select_range(
            'categ_id',
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'Cat 2', 'id': c2_id, },
                {'display_name': 'Cat 1', 'id': c1_id, },
            ]
        )
        self.assertEqual(
            result['parent_field'],
            False
        )

    # Selection case

    def test_selection_empty(self):
        result = self.SourceModel.search_panel_select_range(
            'state',
            expand=True,
        )
        self.assertEqual(
            result,
            {
                'parent_field': False,
                'values': [
                    {'display_name': 'A', 'id': 'a', },
                    {'display_name': 'B', 'id': 'b', },
                ]
            }
        )

    def test_selection(self):
        records = self.SourceModel.create([
            {'name': 'Rec 1', 'state': 'a', },
            {'name': 'Rec 2', 'state': 'a', },
        ])

        r1_id, _ = records.ids

        # counters and expand
        result = self.SourceModel.search_panel_select_range(
            'state',
            enable_counters=True,
            expand=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'A', 'id': 'a', '__count': 2, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )

        # counters, expand, and search domain
        result = self.SourceModel.search_panel_select_range(
            'state',
            enable_counters=True,
            expand=True,
            search_domain=[['id', '=', r1_id]],  # impact expected
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'A', 'id': 'a', '__count': 1, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )

        # no counters and expand
        result = self.SourceModel.search_panel_select_range(
            'state',
            expand=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'A', 'id': 'a', },
                {'display_name': 'B', 'id': 'b', },
            ]
        )

        # no counters, expand, and search domain
        result = self.SourceModel.search_panel_select_range(
            'state',
            expand=True,
            search_domain=[['id', '=', r1_id]],  # no impact expected
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'A', 'id': 'a', },
                {'display_name': 'B', 'id': 'b', },
            ]
        )

        # counters and no expand
        result = self.SourceModel.search_panel_select_range(
            'state',
            enable_counters=True,
        )
        self.assertEqual(
            result['values'],
            [
                {'__count': 2, 'display_name': 'A', 'id': 'a', },
            ]
        )

        # no counters and no expand
        result = self.SourceModel.search_panel_select_range(
            'state',
        )
        self.assertEqual(
            result['values'],
            [
                {'display_name': 'A', 'id': 'a', },
            ]
        )
