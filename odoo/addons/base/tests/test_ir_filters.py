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
        d.pop('embedded_action_id', None)
        d.pop('embedded_parent_res_id', None)
    return seq

class FiltersCase(TransactionCaseWithUserDemo):
    def setUp(self):
        super(FiltersCase, self).setUp()
        self.USER_NG = self.env['res.users'].name_search('demo')[0]
        self.USER_ID = self.USER_NG[0]

    def build(self, model, *args):
        Model = self.env[model].with_user(ADMIN_USER_ID)
        Model.create(args)


class TestGetFilters(FiltersCase):

    def test_own_filters(self):
        self.build(
            'ir.filters',
            dict(name='a', user_ids=[self.USER_ID], model_id='ir.filters'),
            dict(name='b', user_ids=[self.USER_ID], model_id='ir.filters'),
            dict(name='c', user_ids=[self.USER_ID], model_id='ir.filters'),
            dict(name='d', user_ids=[self.USER_ID], model_id='ir.filters'))

        filters = self.env['ir.filters'].with_user(self.USER_ID).get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
            dict(name='a', is_default=False, user_ids=[self.USER_NG[0]], domain='[]', context='{}', sort='[]'),
            dict(name='b', is_default=False, user_ids=[self.USER_NG[0]], domain='[]', context='{}', sort='[]'),
            dict(name='c', is_default=False, user_ids=[self.USER_NG[0]], domain='[]', context='{}', sort='[]'),
            dict(name='d', is_default=False, user_ids=[self.USER_NG[0]], domain='[]', context='{}', sort='[]'),
        ])

    def test_global_filters(self):
        self.build(
            'ir.filters',
            dict(name='a', user_ids=[], model_id='ir.filters'),
            dict(name='b', user_ids=[], model_id='ir.filters'),
            dict(name='c', user_ids=[], model_id='ir.filters'),
            dict(name='d', user_ids=[], model_id='ir.filters'),
        )

        filters = self.env['ir.filters'].with_user(self.USER_ID).get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
            dict(name='a', is_default=False, user_ids=[], domain='[]', context='{}', sort='[]'),
            dict(name='b', is_default=False, user_ids=[], domain='[]', context='{}', sort='[]'),
            dict(name='c', is_default=False, user_ids=[], domain='[]', context='{}', sort='[]'),
            dict(name='d', is_default=False, user_ids=[], domain='[]', context='{}', sort='[]'),
        ])

    def test_no_third_party_filters(self):
        self.build(
            'ir.filters',
            dict(name='a', user_ids=[], model_id='ir.filters'),
            dict(name='b', user_ids=[ADMIN_USER_ID], model_id='ir.filters'),
            dict(name='c', user_ids=[self.USER_ID], model_id='ir.filters'),
            dict(name='d', user_ids=[ADMIN_USER_ID], model_id='ir.filters'))

        filters = self.env['ir.filters'].with_user(self.USER_ID).get_filters('ir.filters')

        self.assertItemsEqual(noid(filters), [
            dict(name='a', is_default=False, user_ids=[], domain='[]', context='{}', sort='[]'),
            dict(name='c', is_default=False, user_ids=[self.USER_NG[0]], domain='[]', context='{}', sort='[]'),
        ])


@tagged('post_install', '-at_install', 'migration')
class TestAllFilters(TransactionCase):
    def check_filter(self, name, model, domain, aggregates, groupby, order, context):
        if groupby:
            try:
                Model = self.env[model].with_context(context)
                groupby = [groupby] if isinstance(groupby, str) else groupby
                groupby = [
                    f"{group_spec}:month" if (
                        ":" not in group_spec and
                        group_spec in Model._fields and
                        Model._fields[group_spec].type in ('date, datetime')
                    ) else group_spec
                    for group_spec in groupby
                ]
                Model.formatted_read_group(domain, groupby, aggregates, order=order)
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
                    aggregates=['__count'],
                    groupby=groupby,
                    order=','.join(ast.literal_eval(filter_.sort)),
                    context=context,
                )


class TestEmbeddedFilters(FiltersCase):

    def setUp(self):
        super(FiltersCase, self).setUp()
        self.USER_NG = self.env['res.users'].name_search('demo')[0]
        self.USER_ID = self.USER_NG[0]
        self.parent_action = self.env['ir.actions.act_window'].create({
            'name': 'ParentAction',
            'res_model': 'res.partner',
        })
        self.action_1 = self.env['ir.actions.act_window'].create({
            'name': 'Action1',
            'res_model': 'res.partner',
        })
        self.embedded_action_1 = self.env['ir.embedded.actions'].create({
            'name': 'EmbeddedAction1',
            'parent_res_model': 'res.partner',
            'parent_action_id': self.parent_action.id,
            'action_id': self.action_1.id,
        })
        self.embedded_action_2 = self.env['ir.embedded.actions'].create({
            'name': 'EmbeddedAction2',
            'parent_res_model': 'res.partner',
            'parent_action_id': self.parent_action.id,
            'action_id': self.action_1.id,
        })

    def test_global_filters_with_embedded_action(self):
        Filters = self.env['ir.filters'].with_user(self.USER_ID)
        Filters.create_filter({
            'name': 'a',
            'model_id': 'ir.filters',
            'user_ids': [],
            'is_default': True,
            'embedded_action_id': self.embedded_action_1.id,
            'embedded_parent_res_id': 1
        })
        Filters.create_filter({
            'name': 'b',
            'model_id': 'ir.filters',
            'user_ids': [self.USER_ID],
            'is_default': False,
            'embedded_action_id': self.embedded_action_2.id,
            'embedded_parent_res_id': 1
        })

        # If embedded_action_id and embedded_parent_res_id are set, should return the corresponding filter
        filters = self.env['ir.filters'].with_user(self.USER_ID).get_filters('ir.filters', embedded_action_id=self.embedded_action_1.id, embedded_parent_res_id=1)
        self.assertItemsEqual(noid(filters), [dict(name='a', is_default=True, user_ids=[], domain='[]', context='{}', sort='[]')])

        # Check that the filter is correctly linked to one embedded_parent_res_id and is not returned if another one is set
        filters = self.env['ir.filters'].with_user(self.USER_ID).get_filters('ir.filters', embedded_action_id=self.embedded_action_1.id, embedded_parent_res_id=2)
        self.assertItemsEqual(noid(filters), [])

        # Check that a shared filter can be fetched with another user
        filters = self.env['ir.filters'].with_user(ADMIN_USER_ID).get_filters('ir.filters', embedded_action_id=self.embedded_action_1.id, embedded_parent_res_id=1)
        self.assertItemsEqual(noid(filters), [dict(name='a', is_default=True, user_ids=[], domain='[]', context='{}', sort='[]')])

        # If embedded_action_id and embedded_parent_res_id are not set, should return no filters
        filters = self.env['ir.filters'].with_user(self.USER_ID).get_filters('ir.filters')
        self.assertItemsEqual(noid(filters), [])

    def test_global_filters_with_no_embedded_action(self):
        Filters = self.env['ir.filters'].with_user(self.USER_ID)
        filter_a = Filters.create_filter({
            'name': 'a',
            'model_id': 'ir.filters',
            'user_ids': [],
            'is_default': True,
            'embedded_action_id': False,
            'embedded_parent_res_id': 0,
        })
        filter_b = Filters.create_filter({
            'name': 'b',
            'model_id': 'ir.filters',
            'user_ids': [self.USER_ID],
            'is_default': True,
            'embedded_action_id': False,
            'embedded_parent_res_id': 1,
        })
        self.assertFalse(filter_a.embedded_action_id)
        self.assertFalse(filter_a.embedded_parent_res_id)
        self.assertFalse(filter_b.embedded_action_id)
        self.assertFalse(filter_b.embedded_parent_res_id)
