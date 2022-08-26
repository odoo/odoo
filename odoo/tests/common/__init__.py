# -*- coding: utf-8 -*-
"""
The module :mod:`odoo.tests.common` provides unittest test cases and a few
helpers and classes to write tests.

"""
import importlib
import logging
import re
import threading
from collections import defaultdict

from decorator import decorator

import odoo
from odoo.tools import single_email_re

_logger = logging.getLogger(__name__)

# The odoo library is supposed already configured.
ADDONS_PATH = odoo.tools.config['addons_path']
# Useless constant, tests are aware of the content of demo data
ADMIN_USER_ID = odoo.SUPERUSER_ID

from .utils import HOST, get_db_name
from .suite import OdooSuite
from .case import (
    BaseCase, SingleTransactionCase, TransactionCase, HttpCase, WsgiCase,
    SavepointCase, HttpSavepointCase,
)
from .form import Form

def is_testing():
    return getattr(threading.current_thread(), 'testing', False)

standalone_tests = defaultdict(list)

def standalone(*tags):
    """ Decorator for standalone test functions.  This is somewhat dedicated to
    tests that install, upgrade or uninstall some modules, which is currently
    forbidden in regular test cases.  The function is registered under the given
    ``tags`` and the corresponding Odoo module name.
    """
    def register(func):
        # register func by odoo module name
        if func.__module__.startswith('odoo.addons.'):
            module = func.__module__.split('.')[2]
            standalone_tests[module].append(func)
        # register func with aribitrary name, if any
        for tag in tags:
            standalone_tests[tag].append(func)
        standalone_tests['all'].append(func)
        return func

    return register

# For backwards-compatibility - get_db_name() should be used instead
DB = get_db_name()


def new_test_user(env, login='', groups='base.group_user', context=None, **kwargs):
    """ Helper function to create a new test user. It allows to quickly create
    users given its login and groups (being a comma separated list of xml ids).
    Kwargs are directly propagated to the create to further customize the
    created user.

    User creation uses a potentially customized environment using the context
    parameter allowing to specify a custom context. It can be used to force a
    specific behavior and/or simplify record creation. An example is to use
    mail-related context keys in mail tests to speedup record creation.

    Some specific fields are automatically filled to avoid issues

     * groups_id: it is filled using groups function parameter;
     * name: "login (groups)" by default as it is required;
     * email: it is either the login (if it is a valid email) or a generated
       string 'x.x@example.com' (x being the first login letter). This is due
       to email being required for most odoo operations;
    """
    if not login:
        raise ValueError('New users require at least a login')
    if not groups:
        raise ValueError('New users require at least user groups')
    if context is None:
        context = {}

    groups_id = [(6, 0, [env.ref(g.strip()).id for g in groups.split(',')])]
    create_values = dict(kwargs, login=login, groups_id=groups_id)
    # automatically generate a name as "Login (groups)" to ease user comprehension
    if not create_values.get('name'):
        create_values['name'] = '%s (%s)' % (login, groups)
    # automatically give a password equal to login
    if not create_values.get('password'):
        create_values['password'] = login + 'x' * (8 - len(login))
    # generate email if not given as most test require an email
    if 'email' not in create_values:
        if single_email_re.match(login):
            create_values['email'] = login
        else:
            create_values['email'] = '%s.%s@example.com' % (login[0], login[0])
    # ensure company_id + allowed company constraint works if not given at create
    if 'company_id' in create_values and 'company_ids' not in create_values:
        create_values['company_ids'] = [(4, create_values['company_id'])]

    return env['res.users'].with_context(**context).create(create_values)


class RecordCapturer:
    def __init__(self, model, domain):
        self._model = model
        self._domain = domain

    def __enter__(self):
        self._before = self._model.search(self._domain)
        self._after = None
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is None:
            self._after = self._model.search(self._domain) - self._before

    @property
    def records(self):
        if self._after is None:
            return self._model.search(self._domain) - self._before
        return self._after


def no_retry(arg):
    """Disable auto retry on decorated test method or test class"""
    arg._retry = False
    return arg


def users(*logins):
    """ Decorate a method to execute it once for each given user. """
    @decorator
    def wrapper(func, *args, **kwargs):
        self = args[0]
        old_uid = self.uid
        try:
            # retrieve users
            Users = self.env['res.users'].with_context(active_test=False)
            user_id = {
                user.login: user.id
                for user in Users.search([('login', 'in', list(logins))])
            }
            for login in logins:
                with self.subTest(login=login):
                    # switch user and execute func
                    self.uid = user_id[login]
                    func(*args, **kwargs)
                # Invalidate the cache between subtests, in order to not reuse
                # the former user's cache (`test_read_mail`, `test_write_mail`)
                self.env.invalidate_all()
        finally:
            self.uid = old_uid

    return wrapper


@decorator
def warmup(func, *args, **kwargs):
    """ Decorate a test method to run it twice: once for a warming up phase, and
        a second time for real.  The test attribute ``warm`` is set to ``False``
        during warm up, and ``True`` once the test is warmed up.  Note that the
        effects of the warmup phase are rolled back thanks to a savepoint.
    """
    self = args[0]
    self.env.flush_all()
    self.env.invalidate_all()
    # run once to warm up the caches
    self.warm = False
    self.cr.execute('SAVEPOINT test_warmup')
    func(*args, **kwargs)
    self.env.flush_all()
    # run once for real
    self.cr.execute('ROLLBACK TO SAVEPOINT test_warmup')
    self.env.invalidate_all()
    self.warm = True
    func(*args, **kwargs)


def can_import(module):
    """ Checks if <module> can be imported, returns ``True`` if it can be,
    ``False`` otherwise.

    To use with ``unittest.skipUnless`` for tests conditional on *optional*
    dependencies, which may or may be present but must still be tested if
    possible.
    """
    try:
        importlib.import_module(module)
    except ImportError:
        return False
    else:
        return True


def tagged(*tags):
    """
    A decorator to tag BaseCase objects.
    Tags are stored in a set that can be accessed from a 'test_tags' attribute.
    A tag prefixed by '-' will remove the tag e.g. to remove the 'standard' tag.
    By default, all Test classes from odoo.tests.common have a test_tags
    attribute that defaults to 'standard' and 'at_install'.
    When using class inheritance, the tags are NOT inherited.
    """
    def tags_decorator(obj):
        include = {t for t in tags if not t.startswith('-')}
        exclude = {t[1:] for t in tags if t.startswith('-')}
        obj.test_tags = (getattr(obj, 'test_tags', set()) | include) - exclude # todo remove getattr in master since we want to limmit tagged to BaseCase and always have +standard tag
        return obj
    return tags_decorator


class TagsSelector(object):
    """ Test selector based on tags. """
    filter_spec_re = re.compile(r'^([+-]?)(\*|\w*)(?:/(\w*))?(?::(\w*))?(?:\.(\w*))?$')  # [-][tag][/module][:class][.method]

    def __init__(self, spec):
        """ Parse the spec to determine tags to include and exclude. """
        filter_specs = {t.strip() for t in spec.split(',') if t.strip()}
        self.exclude = set()
        self.include = set()

        for filter_spec in filter_specs:
            match = self.filter_spec_re.match(filter_spec)
            if not match:
                _logger.error('Invalid tag %s', filter_spec)
                continue

            sign, tag, module, klass, method = match.groups()
            is_include = sign != '-'

            if not tag and is_include:
                # including /module:class.method implicitly requires 'standard'
                tag = 'standard'
            elif not tag or tag == '*':
                # '*' indicates all tests (instead of 'standard' tests only)
                tag = None
            test_filter = (tag, module, klass, method)

            if is_include:
                self.include.add(test_filter)
            else:
                self.exclude.add(test_filter)

        if self.exclude and not self.include:
            self.include.add(('standard', None, None, None))

    def check(self, test):
        """ Return whether ``arg`` matches the specification: it must have at
            least one tag in ``self.include`` and none in ``self.exclude`` for each tag category.
        """
        if not hasattr(test, 'test_tags'): # handle the case where the Test does not inherit from BaseCase and has no test_tags
            _logger.debug("Skipping test '%s' because no test_tag found.", test)
            return False

        test_module = getattr(test, 'test_module', None)
        test_class = getattr(test, 'test_class', None)
        test_tags = test.test_tags | {test_module}  # module as test_tags deprecated, keep for retrocompatibility,
        test_method = getattr(test, '_testMethodName', None)

        def _is_matching(test_filter):
            (tag, module, klass, method) = test_filter
            if tag and tag not in test_tags:
                return False
            elif module and module != test_module:
                return False
            elif klass and klass != test_class:
                return False
            elif method and test_method and method != test_method:
                return False
            return True

        if any(_is_matching(test_filter) for test_filter in self.exclude):
            return False

        if any(_is_matching(test_filter) for test_filter in self.include):
            return True

        return False
