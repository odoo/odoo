# -*- coding: utf-8 -*-
import collections

import mock
import unittest2

from openerp.http import request as req

from . import common

from ..controllers import main


class Placeholder(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)


class LoadTest(common.MockRequestCase):
    def setUp(self):
        super(LoadTest, self).setUp()
        self.home = main.Home()

        # Have self.request.session.model() return a different mock object for
        # each model (but always the same mock for a given model name)
        models = collections.defaultdict(mock.Mock)
        model = req.session.model.side_effect = \
            lambda model_name: models[model_name]

        self.MockMenus = model('ir.ui.menu')
        # Mock the absence of custom menu
        model('res.users').read.return_value = []

    def tearDown(self):
        del self.MockMenus
        del self.home
        super(LoadTest, self).tearDown()

    def test_empty(self):
        self.MockMenus.search.return_value = []
        self.MockMenus.read.return_value = []

        root = self.home.load_menus()

        self.MockMenus.search.assert_called_with(
            [('parent_id', '=', False)], 0, False, False,
            req.context)

        self.assertEqual(root['all_menu_ids'], [])

        self.assertListEqual(
            root['children'],
            [])

    def test_applications_sort(self):
        self.MockMenus.search.return_value = [1, 2, 3]
        self.MockMenus.read.side_effect = lambda *args: [
            {'id': 1, 'sequence': 1, 'parent_id': False},
            {'id': 3, 'sequence': 2, 'parent_id': False},
            {'id': 2, 'sequence': 3, 'parent_id': False},
        ]

        root = self.home.load_menus()

        self.MockMenus.search.assert_called_with(
            [('id', 'child_of', [1, 2, 3])], 0, False, False,
            req.context)

        self.MockMenus.read.assert_called_with(
            [1, 2, 3], ['name', 'sequence', 'parent_id',
                        'action'],
            req.context)

        self.assertEqual(root['all_menu_ids'], [1, 2, 3])

        self.assertEqual(
            root['children'],
            [{
                'id': 1, 'sequence': 1,
                'parent_id': False, 'children': []
            }, {
                'id': 3, 'sequence': 2,
                'parent_id': False, 'children': []
            }, {
                'id': 2, 'sequence': 3,
                'parent_id': False, 'children': []
            }])

    def test_deep(self):
        self.MockMenus.search.side_effect = lambda domain, *args: (
            [1] if domain == [('parent_id', '=', False)] else [1, 2, 3, 4])

        root = {'id': 1, 'sequence': 1, 'parent_id': False}
        self.MockMenus.read.side_effect = lambda ids, *args: (
            [root] if ids == [1] else [
                {'id': 1, 'sequence': 1, 'parent_id': False},
                {'id': 2, 'sequence': 2, 'parent_id': [1, '']},
                {'id': 3, 'sequence': 1, 'parent_id': [2, '']},
                {'id': 4, 'sequence': 2, 'parent_id': [2, '']},
            ])

        root = self.home.load_menus()

        self.MockMenus.search.assert_called_with(
            [('id', 'child_of', [1])], 0, False, False,
            req.context)

        self.assertEqual(root['all_menu_ids'], [1, 2, 3, 4])

        self.assertEqual(
            root['children'],
            [{
                 'id': 1,
                 'sequence': 1,
                 'parent_id': False,
                 'children': [{
                     'id': 2,
                     'sequence': 2,
                     'parent_id': [1, ''],
                     'children': [{
                         'id': 3,
                         'sequence': 1,
                         'parent_id': [2, ''],
                         'children': []
                     }, {
                         'id': 4,
                         'sequence': 2,
                         'parent_id': [2, ''],
                         'children': []
                     }]
                 }]
            }]
        )


class ActionMungerTest(unittest2.TestCase):
    def test_actual_treeview(self):
        action = {
            "views": [[False, "tree"], [False, "form"],
                      [False, "calendar"]],
            "view_type": "tree",
            "view_id": False,
            "view_mode": "tree,form,calendar"
        }
        changed = action.copy()
        del action['view_type']
        main.fix_view_modes(changed)

        self.assertEqual(changed, action)

    def test_list_view(self):
        action = {
            "views": [[False, "tree"], [False, "form"],
                      [False, "calendar"]],
            "view_type": "form",
            "view_id": False,
            "view_mode": "tree,form,calendar"
        }
        main.fix_view_modes(action)

        self.assertEqual(action, {
            "views": [[False, "list"], [False, "form"],
                      [False, "calendar"]],
            "view_id": False,
            "view_mode": "list,form,calendar"
        })

    def test_redundant_views(self):
        action = {
            "views": [[False, "tree"], [False, "form"],
                      [False, "calendar"], [42, "tree"]],
            "view_type": "form",
            "view_id": False,
            "view_mode": "tree,form,calendar"
        }
        main.fix_view_modes(action)

        self.assertEqual(action, {
            "views": [[False, "list"], [False, "form"],
                      [False, "calendar"], [42, "list"]],
            "view_id": False,
            "view_mode": "list,form,calendar"
        })
