# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import logging

from odoo import exceptions
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests.common import TransactionCase, ADMIN_USER_ID, tagged

_logger = logging.getLogger(__name__)

def noid(seq):
    """ Removes values that are not relevant for the test comparisons """
    for d in seq:
        d.pop('id', None)
        d.pop('action_id', None)
    return seq


class FiltersCase(TransactionCaseWithUserDemo):
    def setUp(self):
        super(FiltersCase, self).setUp()
        self.USER_NG = self.env['res.users'].name_search('demo')[0]
        self.USER_ID = self.USER_NG[0]

    def build(self, model, *args):
        Model = self.env[model].with_user(ADMIN_USER_ID)
        for vals in args:
            Model.create(vals)


class TestGetFilters(FiltersCase):

    def test_own_filters(self):
        self.build(
            'ir.filters',
            dict(name='a', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='b', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='c', user_id=self.USER_ID, model_id='ir.filters'),
            dict(name='d', user_id=self.USER_ID, model_id='ir.filters'))

        filters = self.env['ir.filters'].with_user(self.USER_ID).get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
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

        filters = self.env['ir.filters'].with_user(self.USER_ID).get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
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

        filters = self.env['ir.filters'].with_user(self.USER_ID).get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
            dict(name='a', is_default=False, user_id=False, domain='[]', context='{}', sort='[]'),
            dict(name='c', is_default=False, user_id=self.USER_NG, domain='[]', context='{}', sort='[]'),
        ])


class TestOwnDefaults(FiltersCase):

    def test_new_no_filter(self):
        """
        When creating a @is_default filter with no existing filter, that new
        filter gets the default flag
        """
        Filters = self.env['ir.filters'].with_user(self.USER_ID)
        Filters.create_or_replace({
            'name': 'a',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
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

        Filters = self.env['ir.filters'].with_user(self.USER_ID)
        Filters.create_or_replace({
            'name': 'c',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
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

        Filters = self.env['ir.filters'].with_user(self.USER_ID)
        Filters.create_or_replace({
            'name': 'c',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
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

        Filters = self.env['ir.filters'].with_user(self.USER_ID)
        Filters.create_or_replace({
            'name': 'a',
            'model_id': 'ir.filters',
            'user_id': self.USER_ID,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
            dict(name='a', user_id=self.USER_NG, is_default=True, domain='[]', context='{}', sort='[]'),
            dict(name='b', user_id=self.USER_NG, is_default=False, domain='[]', context='{}', sort='[]'),
        ])


class TestGlobalDefaults(FiltersCase):

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

        Filters = self.env['ir.filters'].with_user(self.USER_ID)
        Filters.create_or_replace({
            'name': 'c',
            'model_id': 'ir.filters',
            'user_id': False,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
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

        Filters = self.env['ir.filters'].with_user(self.USER_ID)
        with self.assertRaises(exceptions.UserError):
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

        Filters = self.env['ir.filters'].with_user(self.USER_ID)
        with self.assertRaises(exceptions.UserError):
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

        Filters = self.env['ir.filters'].with_user(self.USER_ID)
        context_value = "{'some_key': True}"
        Filters.create_or_replace({
            'name': 'b',
            'model_id': 'ir.filters',
            'user_id': False,
            'context': context_value,
            'is_default': True,
        })
        filters = Filters.get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
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


@tagged('post_install', '-at_install', 'migration')
class TestAllFilters(TransactionCase):
    def check_filter(self, name, model, domain, fields, groupby, order, context):
        if groupby:
            try:
                self.env[model].with_context(context).read_group(domain, fields, groupby, orderby=order)
            except ValueError as e:
                raise self.failureException("Test filter '%s' failed: %s" % (name, e)) from None
            except KeyError as e:
                raise self.failureException("Test filter '%s' failed: field or aggregate %s does not exist"% (name, e)) from None
        elif domain:
            try:
                self.env[model].with_context(context).search(domain, order=order)
            except ValueError as e:
                raise self.failureException("Test filter '%s' failed: %s" % (name, e)) from None
        else:
            _logger.info("No domain or group by in filter %s with model %s and context %s", name, model, context)

    def test_filters(self):
        for filter_ in self.env['ir.filters'].search([]):
            with self.subTest(name=filter_.name):
                context = ast.literal_eval(filter_.context)
                groupby = context.get('group_by')
                self.check_filter(
                    name=filter_.name,
                    model=filter_.model_id,
                    domain=filter_._get_eval_domain(),
                    fields=[field.split(':')[0] for field in (groupby or [])],
                    groupby=groupby,
                    order=ast.literal_eval(filter_.sort),
                    context=context,
                )
