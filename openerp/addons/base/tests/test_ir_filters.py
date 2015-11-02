# -*- coding: utf-8 -*-
import functools

from openerp import exceptions
from openerp.tests import common

def noid(d):
    """ Removes values that are not relevant for the test comparisons """
    d.pop('id', None)
    d.pop('action_id', None)
    return d

class FiltersCase(common.TransactionCase):
    def build(self, model, *args):
        Model = self.registry(model)
        for vars in args:
            Model.create(self.cr, common.ADMIN_USER_ID, vars, {})

class TestGetFilters(FiltersCase):
    def setUp(self):
        super(TestGetFilters, self).setUp()
        self.USER = self.registry('res.users').name_search(self.cr, self.uid, 'demo')[0]
        self.USER_ID = self.USER[0]

    def test_own_filters(self):
        self.build(
            'ir.filters',
            dict(name='a', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='b', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='c', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='d', user_id=self.USER_ID, model_id='ir.filters'))

        filters = self.registry('ir.filters').get_filters(
            self.cr, self.USER_ID, 'ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', is_default=False, user_id=self.USER, domain='[]', context='{}', sort='[]'),
            dict(name='b', is_default=False, user_id=self.USER, domain='[]', context='{}', sort='[]'),
            dict(name='c', is_default=False, user_id=self.USER, domain='[]', context='{}', sort='[]'),
            dict(name='d', is_default=False, user_id=self.USER, domain='[]', context='{}', sort='[]'),
        ])

    def test_global_filters(self):
        self.build(
            'ir.filters',
            dict(name='a', user_id=False, model_id='ir.filters'),
            dict(name='b', user_id=False, model_id='ir.filters'),
            dict(name='c', user_id=False, model_id='ir.filters'),
            dict(name='d', user_id=False, model_id='ir.filters'),
        )

        filters = self.registry('ir.filters').get_filters(
            self.cr, self.USER_ID, 'ir.filters')

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
            dict(name='b', user_id=common.ADMIN_USER_ID, model_id='ir.filters'),
            dict(name='c', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='d', user_id=common.ADMIN_USER_ID, model_id='ir.filters')  )

        filters = self.registry('ir.filters').get_filters(
            self.cr, self.USER_ID, 'ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', is_default=False, user_id=False, domain='[]', context='{}', sort='[]'),
            dict(name='c', is_default=False, user_id=self.USER, domain='[]', context='{}', sort='[]'),
        ])

class TestOwnDefaults(FiltersCase):
    def setUp(self):
        super(TestOwnDefaults, self).setUp()
        self.USER = self.registry('res.users').name_search(self.cr, self.uid, 'demo')[0]
        self.USER_ID = self.USER[0]                 

    def test_new_no_filter(self):
        """
        When creating a @is_default filter with no existing filter, that new
        filter gets the default flag
        """
        Filters = self.registry('ir.filters')
        Filters.create_or_replace(self.cr, self.USER_ID, {
            'name': 'a',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters(self.cr, self.USER_ID, 'ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=self.USER, is_default=True,
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

        Filters = self.registry('ir.filters')
        Filters.create_or_replace(self.cr, self.USER_ID, {
            'name': 'c',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters(self.cr, self.USER_ID, 'ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=self.USER, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='b', user_id=self.USER, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='c', user_id=self.USER, is_default=True, domain='[]', context='{}', sort='[]'),
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

        Filters = self.registry('ir.filters')
        Filters.create_or_replace(self.cr, self.USER_ID, {
            'name': 'c',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters(self.cr, self.USER_ID, 'ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=self.USER, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='b', user_id=self.USER, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='c', user_id=self.USER, is_default=True, domain='[]', context='{}', sort='[]'),
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

        Filters = self.registry('ir.filters')
        Filters.create_or_replace(self.cr, self.USER_ID, {
            'name': 'a',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters(self.cr, self.USER_ID, 'ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=self.USER, is_default=True, domain='[]', context='{}', sort='[]'),
            dict(name='b', user_id=self.USER, is_default=False, domain='[]', context='{}', sort='[]'),
        ])

class TestGlobalDefaults(FiltersCase):
    def setUp(self):
        super(TestGlobalDefaults, self).setUp()
        self.USER = self.registry('res.users').name_search(self.cr, self.uid, 'demo')[0]
        self.USER_ID = self.USER[0]

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

        Filters = self.registry('ir.filters')
        Filters.create_or_replace(self.cr, self.USER_ID, {
            'name': 'c',
            'model_id': 'ir.filters',
            'user_id': False,
            'is_default': True,
        })
        filters = Filters.get_filters(self.cr, self.USER_ID, 'ir.filters')

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

        Filters = self.registry('ir.filters')
        with self.assertRaises(exceptions.Warning):
            Filters.create_or_replace(self.cr, self.USER_ID, {
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

        Filters = self.registry('ir.filters')

        with self.assertRaises(exceptions.Warning):
            Filters.create_or_replace(self.cr, self.USER_ID, {
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

        Filters = self.registry('ir.filters')
        context_value = "{'some_key': True}"
        Filters.create_or_replace(self.cr, self.USER_ID, {
            'name': 'b',
            'model_id': 'ir.filters',
            'user_id': False,
            'context': context_value,
            'is_default': True,
        })
        filters = Filters.get_filters(self.cr, self.USER_ID, 'ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=False, is_default=False, domain='[]', context='{}', sort='[]'),
            dict(name='b', user_id=False, is_default=True, domain='[]', context=context_value, sort='[]'),
        ])

from openerp.tests.common import TransactionCase

class TestReadGroup(TransactionCase):
    """Test function read_group with groupby on a many2one field to a model
    (in test, "user_id" to "res.users") which is ordered by an inherited not stored field (in
    test, "name" inherited from "res.partners").
    """

    def setUp(self):
        super(TestReadGroup, self).setUp()
        self.ir_filters_model = self.env['ir.filters']
        self.res_partner_model = self.env['res.partner']
        self.res_users_model = self.env['res.users']

    def test_read_group_1(self):
        self.assertEqual(self.res_users_model._order, "name, login", "Model res.users must be ordered by name, login")
        self.assertFalse(self.res_users_model._fields['name'].store, "Field name is not stored in res.users")

        filter_a = self.ir_filters_model.create(dict(name="Filter_A", model_id="ir.filters"))
        filter_b = self.ir_filters_model.create(dict(name="Filter_B", model_id="ir.filters"))
        filter_b.write(dict(user_id=False))
        res = self.ir_filters_model.read_group([], ['name', 'user_id'], ['user_id'])
        self.assertTrue(any(val['user_id'] == False for val in res), "At least one group must contain val['user_id'] == False.")
