# -*- coding: utf-8 -*-
import odoo.tests
import json

@odoo.tests.tagged('post_install', '-at_install')
class TestSelectRangeMulti(odoo.tests.TransactionCase):

    def setUp(self):
        super().setUp()
        self.SourceModel = self.env['test_search_panel.source_model']
        self.TargetModel = self.env['test_search_panel.filter_target_model']
        self.GroupByModel = self.env['test_search_panel.category_target_model']

    # Many2one

    def test_many2one_empty(self):
        result = self.SourceModel.search_panel_select_multi_range('tag_id')
        self.assertEqual(
            result,
            [],
        )

    def test_many2one(self):

        folders = self.GroupByModel.create([
            {'name': 'Folder 1', },
            {'name': 'Folder 2', },
        ])

        f1_id, f2_id = folders.ids

        tags = self.TargetModel.create([
            {'name': 'Tag 1', 'folder_id': f2_id,
                'color': 'Red', 'status': 'cool', },
            {'name': 'Tag 2', 'folder_id': f1_id, 'status': 'cool', },
            {'name': 'Tag 3', 'color': 'Green', 'status': 'cool', },
        ])

        t1_id, t2_id, t3_id = tags.ids

        records = self.SourceModel.create([
            {'name': 'Rec 1', 'tag_id': t1_id, },
            {'name': 'Rec 2', 'tag_id': t1_id, },
            {'name': 'Rec 3', 'tag_id': t2_id, },
            {'name': 'Rec 4', },
        ])

        r1_id, r2_id, _, _ = records.ids

        # counters
        result = self.SourceModel.search_panel_select_multi_range('tag_id')
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id, },
                {'__count': 1, 'display_name': 'Tag 2', 'id': t2_id, },
                {'__count': 0, 'display_name': 'Tag 3', 'id': t3_id, },
            ]
        )

        # counters and search domain
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_id',
            search_domain=[['id', 'in', [r1_id, r2_id]]],
        )
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id, },
                {'__count': 0, 'display_name': 'Tag 2', 'id': t2_id, },
                {'__count': 0, 'display_name': 'Tag 3', 'id': t3_id, },
            ],
        )

        # no counters
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_id',
            disable_counters=True,
        )
        self.assertEqual(
            result,
            [
                {'__count': 0, 'display_name': 'Tag 1', 'id': t1_id, },
                {'__count': 0, 'display_name': 'Tag 2', 'id': t2_id, },
                {'__count': 0, 'display_name': 'Tag 3', 'id': t3_id, },
            ],
        )

        # no counters and search domain
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_id',
            disable_counters=True,
            search_domain=[['id', 'in', [r1_id, r2_id]]],
        )
        self.assertEqual(
            result,
            [
                {'__count': 0, 'display_name': 'Tag 1', 'id': t1_id, },
                {'__count': 0, 'display_name': 'Tag 2', 'id': t2_id, },
                {'__count': 0, 'display_name': 'Tag 3', 'id': t3_id, },
            ]
        )

        # many2one group_by
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_id',
            group_by='folder_id'
        )
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id,
                    'group_id': f2_id, 'group_name': 'Folder 2', },
                {'__count': 1, 'display_name': 'Tag 2', 'id': t2_id,
                    'group_id': f1_id, 'group_name': 'Folder 1', },
                {'__count': 0, 'display_name': 'Tag 3', 'id': t3_id,
                    'group_id': False, 'group_name': 'Not Set', },
            ]
        )

        # selection group_by
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_id',
            group_by='status'
        )
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id,
                    'group_id': 'cool', 'group_name': 'Cool', },
                {'__count': 1, 'display_name': 'Tag 2', 'id': t2_id,
                    'group_id': 'cool', 'group_name': 'Cool', },
                {'__count': 0, 'display_name': 'Tag 3', 'id': t3_id,
                    'group_id': 'cool', 'group_name': 'Cool', },
            ]
        )

        # other group_by
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_id',
            group_by='color'
        )
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id,
                    'group_id': 'Red', 'group_name': 'Red', },
                {'__count': 1, 'display_name': 'Tag 2', 'id': t2_id,
                    'group_id': False, 'group_name': 'Not Set', },
                {'__count': 0, 'display_name': 'Tag 3', 'id': t3_id,
                    'group_id': 'Green', 'group_name': 'Green', },
            ]
        )

    # Many2many

    def test_many2many_empty(self):
        result = self.SourceModel.search_panel_select_multi_range('tag_ids')
        self.assertEqual(
            result,
            [],
        )

    def test_many2many(self):

        folders = self.GroupByModel.create([
            {'name': 'Folder 1', },
            {'name': 'Folder 2', },
        ])

        f1_id, f2_id = folders.ids

        tags = self.TargetModel.create([
            {'name': 'Tag 1', 'folder_id': f2_id,
                'color': 'Red', 'status': 'cool', },
            {'name': 'Tag 2', 'folder_id': f1_id, 'status': 'cool', },
            {'name': 'Tag 3', 'color': 'Green', 'status': 'cool', },
        ])

        t1_id, t2_id, t3_id = tags.ids

        records = self.SourceModel.create([
            {'name': 'Rec 1', 'tag_ids': [t1_id, t2_id, t3_id], },
            {'name': 'Rec 2', 'tag_ids': [t1_id], },
            {'name': 'Rec 3', 'tag_ids': [t2_id, t3_id], },
            {'name': 'Rec 4', },
        ])

        r1_id, r2_id, _, _ = records.ids

        # counters
        result = self.SourceModel.search_panel_select_multi_range('tag_ids')
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id, },
                {'__count': 2, 'display_name': 'Tag 2', 'id': t2_id, },
                {'__count': 2, 'display_name': 'Tag 3', 'id': t3_id, },
            ]
        )

        # counters and search domain
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_ids',
            search_domain=[['id', 'in', [r1_id, r2_id]]],
        )
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id, },
                {'__count': 1, 'display_name': 'Tag 2', 'id': t2_id, },
                {'__count': 1, 'display_name': 'Tag 3', 'id': t3_id, },
            ],
        )

        # no counters
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_ids',
            disable_counters=True,
        )
        self.assertEqual(
            result,
            [
                {'__count': 0, 'display_name': 'Tag 1', 'id': t1_id, },
                {'__count': 0, 'display_name': 'Tag 2', 'id': t2_id, },
                {'__count': 0, 'display_name': 'Tag 3', 'id': t3_id, },
            ],
        )

        # no counters and search domain
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_ids',
            disable_counters=True,
            search_domain=[['id', 'in', [r1_id, r2_id]]],
        )
        self.assertEqual(
            result,
            [
                {'__count': 0, 'display_name': 'Tag 1', 'id': t1_id, },
                {'__count': 0, 'display_name': 'Tag 2', 'id': t2_id, },
                {'__count': 0, 'display_name': 'Tag 3', 'id': t3_id, },
            ]
        )

        # many2one group_by
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_ids',
            group_by='folder_id'
        )
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id,
                    'group_id': f2_id, 'group_name': 'Folder 2', },
                {'__count': 2, 'display_name': 'Tag 2', 'id': t2_id,
                    'group_id': f1_id, 'group_name': 'Folder 1', },
                {'__count': 2, 'display_name': 'Tag 3', 'id': t3_id,
                    'group_id': False, 'group_name': 'Not Set', },
            ]
        )

        # selection group_by
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_ids',
            group_by='status'
        )
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id,
                    'group_id': 'cool', 'group_name': 'Cool', },
                {'__count': 2, 'display_name': 'Tag 2', 'id': t2_id,
                    'group_id': 'cool', 'group_name': 'Cool', },
                {'__count': 2, 'display_name': 'Tag 3', 'id': t3_id,
                    'group_id': 'cool', 'group_name': 'Cool', },
            ]
        )

        # other group_by
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_ids',
            group_by='color'
        )
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id,
                    'group_id': 'Red', 'group_name': 'Red', },
                {'__count': 2, 'display_name': 'Tag 2', 'id': t2_id,
                    'group_id': False, 'group_name': 'Not Set', },
                {'__count': 2, 'display_name': 'Tag 3', 'id': t3_id,
                    'group_id': 'Green', 'group_name': 'Green', },
            ]
        )

        # group_domain and many2one groupby
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_ids',
            group_by='folder_id',
            group_domain={
                json.dumps(f1_id): [('tag_ids', 'in', [t1_id]), ],
                json.dumps(f2_id): [('tag_ids', 'in', [t2_id]), ],
                json.dumps(False): [('tag_ids', 'in', [t1_id]), ('tag_ids', 'in', [t2_id]), ],
            }
        )
        self.assertEqual(
            result,
            [
                {'__count': 1, 'display_name': 'Tag 1', 'id': t1_id,
                    'group_id': f2_id, 'group_name': 'Folder 2', },
                {'__count': 1, 'display_name': 'Tag 2', 'id': t2_id,
                    'group_id': f1_id, 'group_name': 'Folder 1', },
                {'__count': 1, 'display_name': 'Tag 3', 'id': t3_id,
                    'group_id': False, 'group_name': 'Not Set', },
            ]
        )

        # group_domain and other group_by
        result = self.SourceModel.search_panel_select_multi_range(
            'tag_ids',
            group_by='color',
            group_domain={
                json.dumps(False): [('tag_ids', 'in', [t1_id]), ],
                json.dumps('Green'): [('tag_ids', 'in', [t1_id]), ],
            }
        )
        self.assertEqual(
            result,
            [
                {'__count': 2, 'display_name': 'Tag 1', 'id': t1_id,
                    'group_id': 'Red', 'group_name': 'Red', },
                {'__count': 1, 'display_name': 'Tag 2', 'id': t2_id,
                    'group_id': False, 'group_name': 'Not Set', },
                {'__count': 1, 'display_name': 'Tag 3', 'id': t3_id,
                    'group_id': 'Green', 'group_name': 'Green', },
            ]
        )

    # Selection case

    def test_selection_empty(self):
        result = self.SourceModel.search_panel_select_multi_range('state')
        self.assertEqual(
            result,
            [
                {'display_name': 'A', 'id': 'a', '__count': 0, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )

    def test_selection(self):
        records = self.SourceModel.create([
            {'name': 'Rec 1', 'state': 'a', },
            {'name': 'Rec 2', 'state': 'a', },
        ])

        r1_id, _ = records.ids

        # counters
        result = self.SourceModel.search_panel_select_multi_range('state')
        self.assertEqual(
            result,
            [
                {'display_name': 'A', 'id': 'a', '__count': 2, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )

        # no counters
        result = self.SourceModel.search_panel_select_multi_range(
            'state',
            disable_counters=True,
        )
        self.assertEqual(
            result,
            [
                {'display_name': 'A', 'id': 'a', '__count': 0, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )

        # counters and search domain
        result = self.SourceModel.search_panel_select_multi_range(
            'state',
            search_domain=[['id', '=', r1_id]],
        )
        self.assertEqual(
            result,
            [
                {'display_name': 'A', 'id': 'a', '__count': 1, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )

        # no counters and search domain
        result = self.SourceModel.search_panel_select_multi_range(
            'state',
            disable_counters=True,
            search_domain=[['id', '=', r1_id]],
        )
        self.assertEqual(
            result,
            [
                {'display_name': 'A', 'id': 'a', '__count': 0, },
                {'display_name': 'B', 'id': 'b', '__count': 0, },
            ]
        )
