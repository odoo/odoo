# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.tests.common import TransactionCase, ADMIN_USER_ID

def noid(d):
    """ Removes values that are not relevant for the test comparisons """
    d.pop('id', None)
    d.pop('action_id', None)
    return d


class FiltersCase(TransactionCase):
    def build(self, model, *args):
        Model = self.env[model].sudo(ADMIN_USER_ID)
        for vals in args:
            Model.create(vals)


class TestGetFilters(FiltersCase):
    def setUp(self):
        super(TestGetFilters, self).setUp()
        self.USER_NG = self.env['res.users'].name_search('demo')[0]
        self.USER_ID = self.USER_NG[0]

    def test_own_filters(self):
        self.build(
            'ir.filters',
            dict(name='a', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='b', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='c', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='d', user_id=self.USER_ID, model_id='ir.filters'))

        filters = self.env['ir.filters'].sudo(self.USER_ID).get_filters('ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', is_default=False, user_id=self.USER_NG, domain='[]', context='{}', sort='[]'),
            dict(name='b', is_default=False, user_id=self.USER_NG, domain='[]', context='{}', sort='[]'),
            dict(name='c', is_default=False, user_id=self.USER_NG, domain='[]', context='{}', sort='[]'),
            dict(name='d', is_default=False, user_id=self.USER_NG, domain='[]', context='{}', sort='[]'),
        ])

    def test_global_filters(self):
        self.build(
            'ir.filters',
            dict(name='a', user_id=False, model_id='ir.filters'),
            dict(name='b', user_id=False, model_id='ir.filters'),
            dict(name='c', user_id=False, model_id='ir.filters'),
            dict(name='d', user_id=False, model_id='ir.filters'),
        )

        filters = self.env['ir.filters'].sudo(self.USER_ID).get_filters('ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', is_default=False, user_id=False, domain='[]', context='{}', sort='[]'),
            dict(name='b', is_default=False, user_id=False, domain='[]', context='{}', sort='[]'),
            dict(name='c', is_default=False, user_id=False, domain='[]', context='{}', sort='[]'),
            dict(name='d', is_default=False, user_id=False, domain='[]', context='{}', sort='[]'),
        ])

    def test_no_third_party_filters(self):
        self.build(
            'ir.filters',
            dict(name='a', user_id=False, model_id='ir.filters'),
            dict(name='b', user_id=ADMIN_USER_ID, model_id='ir.filters'),
            dict(name='c', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='d', user_id=ADMIN_USER_ID, model_id='ir.filters')  )

        filters = self.env['ir.filters'].sudo(self.USER_ID).get_filters('ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', is_default=False, user_id=False, domain='[]', context='{}', sort='[]'),
            dict(name='c', is_default=False, user_id=self.USER_NG, domain='[]', context='{}', sort='[]'),
        ])


class TestOwnDefaults(FiltersCase):
    def setUp(self):
        super(TestOwnDefaults, self).setUp()
        self.USER_NG = self.env['res.users'].name_search('demo')[0]
        self.USER_ID = self.USER_NG[0]                 

    def test_new_no_filter(self):
        """
        When creating a @is_default filter with no existing filter, that new
        filter gets the default flag
        """
        Filters = self.env['ir.filters'].sudo(self.USER_ID)
        Filters.create_or_replace({
            'name': 'a',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=self.USER_NG, is_default=True,
                 domain='[]', context='{}', sort='[]')
        ])

    def test_new_filter_not_default(self):
        """
        When creating a @is_default filter with existing non-default filters,
        the new filter gets the flag
        """
        self.build(
            'ir.filters',
            dict(name='a', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='b', user_id=self.USER_ID, model_id='ir.filters'),
        )

        Filters = self.env['ir.filters'].sudo(self.USER_ID)
        Filters.create_or_replace({
            'name': 'c',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=self.USER_NG, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='b', user_id=self.USER_NG, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='c', user_id=self.USER_NG, is_default=True, domain='[]', context='{}', sort='[]'),
        ])

    def test_new_filter_existing_default(self):
        """
        When creating a @is_default filter where an existing filter is already
        @is_default, the flag should be *moved* from the old to the new filter
        """
        self.build(
            'ir.filters',
            dict(name='a', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='b', is_default=True, user_id=self.USER_ID, model_id='ir.filters'),
        )

        Filters = self.env['ir.filters'].sudo(self.USER_ID)
        Filters.create_or_replace({
            'name': 'c',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=self.USER_NG, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='b', user_id=self.USER_NG, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='c', user_id=self.USER_NG, is_default=True, domain='[]', context='{}', sort='[]'),
        ])

    def test_update_filter_set_default(self):
        """
        When updating an existing filter to @is_default, if an other filter
        already has the flag the flag should be moved
        """
        self.build(
            'ir.filters',
            dict(name='a', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='b', is_default=True, user_id=self.USER_ID, model_id='ir.filters'),
        )

        Filters = self.env['ir.filters'].sudo(self.USER_ID)
        Filters.create_or_replace({
            'name': 'a',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=self.USER_NG, is_default=True, domain='[]', context='{}', sort='[]'),
            dict(name='b', user_id=self.USER_NG, is_default=False, domain='[]', context='{}', sort='[]'),
        ])


class TestGlobalDefaults(FiltersCase):
    def setUp(self):
        super(TestGlobalDefaults, self).setUp()
        self.USER_NG = self.env['res.users'].name_search('demo')[0]
        self.USER_ID = self.USER_NG[0]

    def test_new_filter_not_default(self):
        """
        When creating a @is_default filter with existing non-default filters,
        the new filter gets the flag
        """
        self.build(
            'ir.filters',
            dict(name='a', user_id=False, model_id='ir.filters'),
            dict(name='b', user_id=False, model_id='ir.filters'),
        )

        Filters = self.env['ir.filters'].sudo(self.USER_ID)
        Filters.create_or_replace({
            'name': 'c',
            'model_id': 'ir.filters',
            'user_id': False,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=False, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='b', user_id=False, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='c', user_id=False, is_default=True, domain='[]', context='{}', sort='[]'),
        ])

    def test_new_filter_existing_default(self):
        """
        When creating a @is_default filter where an existing filter is already
        @is_default, an error should be generated
        """
        self.build(
            'ir.filters',
            dict(name='a', user_id=False, model_id='ir.filters'),
            dict(name='b', is_default=True, user_id=False, model_id='ir.filters'),
        )

        Filters = self.env['ir.filters'].sudo(self.USER_ID)
        with self.assertRaises(exceptions.Warning):
            Filters.create_or_replace({
                'name': 'c',
                'model_id': 'ir.filters',
                'user_id': False,
                'is_default': True,
            })

    def test_update_filter_set_default(self):
        """
        When updating an existing filter to @is_default, if an other filter
        already has the flag an error should be generated
        """
        self.build(
            'ir.filters',
            dict(name='a', user_id=False, model_id='ir.filters'),
            dict(name='b', is_default=True, user_id=False, model_id='ir.filters'),
        )

        Filters = self.env['ir.filters'].sudo(self.USER_ID)
        with self.assertRaises(exceptions.Warning):
            Filters.create_or_replace({
                'name': 'a',
                'model_id': 'ir.filters',
                'user_id': False,
                'is_default': True,
            })

    def test_update_default_filter(self):
        """
        Replacing the current default global filter should not generate any error
        """
        self.build(
            'ir.filters',
            dict(name='a', user_id=False, model_id='ir.filters'),
            dict(name='b', is_default=True, user_id=False, model_id='ir.filters'),
        )

        Filters = self.env['ir.filters'].sudo(self.USER_ID)
        context_value = "{'some_key': True}"
        Filters.create_or_replace({
            'name': 'b',
            'model_id': 'ir.filters',
            'user_id': False,
            'context': context_value,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=False, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='b', user_id=False, is_default=True, domain='[]', context=context_value, sort='[]'),
        ])


class TestReadGroup(TransactionCase):
    """Test function read_group with groupby on a many2one field to a model
    (in test, "user_id" to "res.users") which is ordered by an inherited not stored field (in
    test, "name" inherited from "res.partners").
    """
    def test_read_group_1(self):
        Users = self.env['res.users']
        self.assertEqual(Users._order, "name, login", "Model res.users must be ordered by name, login")
        self.assertFalse(Users._fields['name'].store, "Field name is not stored in res.users")

        Filters = self.env['ir.filters']
        filter_a = Filters.create(dict(name="Filter_A", model_id="ir.filters"))
        filter_b = Filters.create(dict(name="Filter_B", model_id="ir.filters"))
        filter_b.write(dict(user_id=False))

        res = Filters.read_group([], ['name', 'user_id'], ['user_id'])
        self.assertTrue(any(val['user_id'] == False for val in res), "At least one group must contain val['user_id'] == False.")
