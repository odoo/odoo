# -*- coding: utf-8 -*-
import mock
import unittest2
import base.controllers.main
import openerpweb.openerpweb

class Placeholder(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

class LoadTest(unittest2.TestCase):
    def setUp(self):
        self.menu = base.controllers.main.Menu()
        self.menus_mock = mock.Mock()
        self.request = Placeholder(
            session=openerpweb.openerpweb.OpenERPSession(
                model_factory=lambda _session, _name: self.menus_mock))

    def tearDown(self):
        del self.request
        del self.menus_mock
        del self.menu

    def test_empty(self):
        self.menus_mock.search = mock.Mock(return_value=[])
        self.menus_mock.read = mock.Mock(return_value=[])

        root = self.menu.do_load(self.request)

        self.menus_mock.search.assert_called_with([])
        self.menus_mock.read.assert_called_with(
            [], ['name', 'sequence', 'parent_id'])

        self.assertListEqual(
            root['children'],
            [])

    def test_applications_sort(self):
        self.menus_mock.search = mock.Mock(return_value=[1, 2, 3])
        self.menus_mock.read = mock.Mock(return_value=[
            {'id': 2, 'sequence': 3, 'parent_id': False},
            {'id': 3, 'sequence': 2, 'parent_id': False},
            {'id': 1, 'sequence': 1, 'parent_id': False},
        ])

        root = self.menu.do_load(self.request)

        self.menus_mock.read.assert_called_with(
            [1, 2, 3], ['name', 'sequence', 'parent_id'])

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
        self.menus_mock.search = mock.Mock(return_value=[1, 2, 3, 4])
        self.menus_mock.read = mock.Mock(return_value=[
            {'id': 1, 'sequence': 1, 'parent_id': False},
            {'id': 2, 'sequence': 2, 'parent_id': [1, '']},
            {'id': 3, 'sequence': 1, 'parent_id': [2, '']},
            {'id': 4, 'sequence': 2, 'parent_id': [2, '']},
        ])

        root = self.menu.do_load(self.request)

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
    def setUp(self):
        self.menu = base.controllers.main.Menu()
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
        self.menu.fix_view_modes(changed)

        self.assertEqual(changed, action)

    def test_list_view(self):
        action = {
            "views": [[False, "tree"], [False, "form"],
                      [False, "calendar"]],
            "view_type": "form",
            "view_id": False,
            "view_mode": "tree,form,calendar"
        }
        self.menu.fix_view_modes(action)

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
        self.menu.fix_view_modes(action)

        self.assertEqual(action, {
            "views": [[False, "list"], [False, "form"],
                      [False, "calendar"], [42, "list"]],
            "view_id": False,
            "view_mode": "list,form,calendar"
        })
