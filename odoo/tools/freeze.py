# -*- coding: utf-8 -*-

# Minimalistic and odoo-specific version of https://github.com/spulec/freezegun
# For license information, see https://www.apache.org/licenses/LICENSE-2.0.txt
# Copyright 2012 Steve Pulec
#
# Modifications to the original code:
#   * remove python 2 compatibility layer
#   * restrict possible attributes to replace to a few names
#   * remove module attribute cache because of the previous point
#   * remove factories as "time moving" is not needed for Odoo (for now)
#   * create fake functions/classes during initialization
#   * cover only functions/methods used within Odoo
#   * simplification of some heuristics
#   * freeze_time only works as a class decorator for TestCase-based classes

import inspect
import functools
import sys
import datetime
import time


def _get_module_attributes(module):
    result = []
    for attribute_name in dir(module):
        try:
            attribute_value = getattr(module, attribute_name)
        except (ImportError, AttributeError, TypeError):
            continue
        else:
            result.append((attribute_name, attribute_value))
    return result


class freeze_time:

    """
    Monkey-patches a series of time functions and classes from the CPython stdlib

    The patched functions/classes are:
        * datetime.datetime
            * now
            * today
            * utcnow
        * datetime.date
            * today
        * time.time
        * time.strftime
    """

    def __init__(self, t):
        self.t = t
        self.applied = False

        # keep track of modified modules
        self.original_modules = set()
        self.to_revert = []

    def __call__(self, to_decorate):
        # work as a class & function decorator
        if inspect.isclass(to_decorate):
            assert (hasattr(to_decorate, 'setUpClass') and hasattr(to_decorate, 'tearDownClass')),\
                    "Only classes with a setUpClass and tearDownClass are supported."
            return self._decorate_class(to_decorate)
        return self._decorate_func(to_decorate)

    def _decorate_class(self, to_decorate):

        original_setUpClass = to_decorate.setUpClass
        original_tearDownClass = to_decorate.tearDownClass

        @classmethod
        def setUpClass(cls):
            self.apply()
            original_setUpClass()

        @classmethod
        def tearDownClass(cls):
            original_tearDownClass()
            self.revert()

        to_decorate.setUpClass = setUpClass
        to_decorate.tearDownClass = tearDownClass
        return to_decorate

    def _decorate_func(self, to_decorate):
        def wrapper(*args, **kwargs):
            with self:
                res = to_decorate(*args, **kwargs)
            return res
        # make the wrapper look like the wrapped function
        functools.update_wrapper(wrapper, to_decorate)
        return wrapper

    def _is_valid_mod(self, name, mod):
        return not (name is None or mod is None or name == __name__ or
                    getattr(mod, '__name__', None) in ('datetime', 'time'))

    def _prepare_patch(self):
        from odoo import fields

        # value with which to monkeypatch
        dt = fields.Datetime.to_datetime(self.t)
        d = dt.date()
        t = dt.timestamp()
        original_strftime = time.strftime

        def datetime_to_patched(t):
            return PatchedDatetime(
                        t.year,
                        t.month,
                        t.day,
                        t.hour,
                        t.minute,
                        t.second,
                        t.microsecond,
                        t.tzinfo,
                    )

        def date_to_patched(t):
            return PatchedDate(t.year, t.month, t.day)

        # patched definitions
        class PatchedDate(datetime.date):
            __slots__ = ()

            def __add__(self, other):
                res = super().__add__(other)
                if res is NotImplemented:
                    return res
                return date_to_patched(res)

            def __sub__(self, other):
                res = super().__sub__(other)
                if isinstance(res, datetime.date):
                    return date_to_patched(res)
                return res

            @classmethod
            def today(cls):
                return date_to_patched(d)

        PatchedDate.min = date_to_patched(d.min)
        PatchedDate.max = date_to_patched(d.max)

        class PatchedDatetime(datetime.datetime, PatchedDate):
            __slots__ = ()

            def __add__(self, other):
                res = super().__add__(other)
                if res is NotImplemented:
                    return res
                return datetime_to_patched(res)

            def __sub__(self, other):
                res = super().__sub__(other)
                if isinstance(res, datetime.datetime):
                    return datetime_to_patched(res)
                return res

            def astimezone(self, tz=None):
                return datetime_to_patched(super().astimezone(tz))

            def date(self):
                return date_to_patched(self)

            @classmethod
            def now(cls, tz=None):
                res = dt
                if tz:
                    res = tz.fromutc(dt.replace(tzinfo=tz))
                return datetime_to_patched(res)

            @classmethod
            def today(cls):
                return cls.now()

            @classmethod
            def utcnow(cls):
                return datetime_to_patched(dt)

        PatchedDatetime.min = datetime_to_patched(dt.min)
        PatchedDatetime.max = datetime_to_patched(dt.max)

        def patched_time():
            return t

        def patched_strftime(format, _t=None):
            if _t is None:
                return original_strftime(format, dt.timetuple())
            return original_strftime(format, _t)

        self.patch_pairs = (
            (datetime.datetime, PatchedDatetime),
            (datetime.date, PatchedDate),
            (time.time, patched_time),
            (time.strftime, patched_strftime),
        )

    def apply(self):
        assert not self.applied, "You cannot apply a frozen time twice!"
        # prepare patched classes and functions
        self._prepare_patch()
        # apply locally
        datetime.datetime = self.patch_pairs[0][1]
        datetime.date = self.patch_pairs[1][1]
        time.time = self.patch_pairs[2][1]
        time.strftime = self.patch_pairs[3][1]

        self.original_modules = set(sys.modules)

        # apply globally
        for mod_name, module in list(sys.modules.items()):
            if self._is_valid_mod(mod_name, module):
                attrs = _get_module_attributes(module)
                for attr_name, attr_val in attrs:
                    for og, patched in self.patch_pairs:
                        if attr_val is og:
                            setattr(module, attr_name, patched)
                            self.to_revert.append((module, attr_name, attr_val))
                            break

        self.applied = True

    def revert(self):
        assert self.applied, "You cannot revert a frozen time that has not been applied yet!"
        # revert locally
        datetime.datetime = self.patch_pairs[0][0]
        datetime.date = self.patch_pairs[1][0]
        time.time = self.patch_pairs[2][0]
        time.strftime = self.patch_pairs[3][0]

        # revert globally
        for mod, mod_attr, original_val in self.to_revert:
            setattr(mod, mod_attr, original_val)
        self.to_revert = []

        # It is possible that more modules were loaded after the call to `apply`, we must ensure
        # that these modules have been restored as well.
        new_to_revert = set(sys.modules) - self.original_modules
        self.original_modules = set()
        for mod_name in new_to_revert:
            module = sys.modules.get(mod_name, None)
            if self._is_valid_mod(mod_name, module):
                attrs = _get_module_attributes(module)
                for attr_name, attr_val in attrs:
                    for og, patched in self.patch_pairs:
                        if attr_val is patched and attr_name != patched.__name__:
                            setattr(module, attr_name, og)
                            break

        self.applied = False

    def __enter__(self):
        self.apply()

    def __exit__(self, *args):
        self.revert()
