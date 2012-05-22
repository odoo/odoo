# -*- coding: utf-8 -*-
import functools

import openerp
import common

class Fixtures(object):
    def __init__(self, *args):
        self.fixtures = args

    def __call__(self, fn):
        @functools.wraps(fn)
        def wrapper(case):
            for model, vars in self.fixtures:
                case.registry(model).create(
                    case.cr, common.ADMIN_USER_ID, vars, {})

            fn(case)
        return wrapper
def fixtures(*args):
    return Fixtures(*args)

def noid(d):
    """ Removes `id` key from a dict so we don't have to keep these things
    around when trying to match
    """
    if 'id' in d: del d['id']
    return d

class TestGetFilters(common.TransactionCase):
    USER_ID = 3
    USER = (3, u'Demo User')

    @fixtures(
        ('ir.filters', dict(name='a', user_id=USER_ID, model_id='ir.filters')),
        ('ir.filters', dict(name='b', user_id=USER_ID, model_id='ir.filters')),
        ('ir.filters', dict(name='c', user_id=USER_ID, model_id='ir.filters')),
        ('ir.filters', dict(name='d', user_id=USER_ID, model_id='ir.filters')),
    )
    def test_own_filters(self):
        filters = self.registry('ir.filters').get_filters(
            self.cr, self.USER_ID, 'ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=self.USER, domain='[]', context='{}'),
            dict(name='b', user_id=self.USER, domain='[]', context='{}'),
            dict(name='c', user_id=self.USER, domain='[]', context='{}'),
            dict(name='d', user_id=self.USER, domain='[]', context='{}'),
        ])

    @fixtures(
        ('ir.filters', dict(name='a', user_id=False, model_id='ir.filters')),
        ('ir.filters', dict(name='b', user_id=False, model_id='ir.filters')),
        ('ir.filters', dict(name='c', user_id=False, model_id='ir.filters')),
        ('ir.filters', dict(name='d', user_id=False, model_id='ir.filters')),
    )
    def test_global_filters(self):
        filters = self.registry('ir.filters').get_filters(
            self.cr, self.USER_ID, 'ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=False, domain='[]', context='{}'),
            dict(name='b', user_id=False, domain='[]', context='{}'),
            dict(name='c', user_id=False, domain='[]', context='{}'),
            dict(name='d', user_id=False, domain='[]', context='{}'),
        ])

    @fixtures(
        ('ir.filters', dict(name='a', user_id=False, model_id='ir.filters')),
        ('ir.filters', dict(name='b', user_id=common.ADMIN_USER_ID, model_id='ir.filters')),
        ('ir.filters', dict(name='c', user_id=USER_ID, model_id='ir.filters')),
        ('ir.filters', dict(name='d', user_id=common.ADMIN_USER_ID, model_id='ir.filters')),
    )
    def test_no_third_party_filters(self):
        filters = self.registry('ir.filters').get_filters(
            self.cr, self.USER_ID, 'ir.filters')

        self.assertItemsEqual(map(noid, filters), [
            dict(name='a', user_id=False, domain='[]', context='{}'),
            dict(name='c', user_id=self.USER, domain='[]', context='{}'),
        ])

