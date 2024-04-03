# -*- coding: utf-8 -*-
"""
internal gevent utilities, not for external use.
"""

# Be very careful not to import anything that would cause issues with
# monkey-patching.

from __future__ import print_function, absolute_import, division

from gevent._compat import iteritems


class _NONE(object):
    """
    A special object you must never pass to any gevent API.
    Used as a marker object for keyword arguments that cannot have the
    builtin None (because that might be a valid value).
    """
    __slots__ = ()

    def __repr__(self):
        return '<default value>'

_NONE = _NONE()

WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__qualname__', '__doc__',
                       '__annotations__')
WRAPPER_UPDATES = ('__dict__',)
def update_wrapper(wrapper,
                   wrapped,
                   assigned=WRAPPER_ASSIGNMENTS,
                   updated=WRAPPER_UPDATES):
    """
    Based on code from the standard library ``functools``, but
    doesn't perform any of the troublesome imports.

    functools imports RLock from _thread for purposes of the
    ``lru_cache``, making it problematic to use from gevent.

    The other imports are somewhat heavy: abc, collections, types.
    """
    for attr in assigned:
        try:
            value = getattr(wrapped, attr)
        except AttributeError:
            pass
        else:
            setattr(wrapper, attr, value)
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
    # Issue #17482: set __wrapped__ last so we don't inadvertently copy it
    # from the wrapped function when updating __dict__
    wrapper.__wrapped__ = wrapped
    # Return the wrapper so this can be used as a decorator via partial()
    return wrapper


def copy_globals(source,
                 globs,
                 only_names=None,
                 ignore_missing_names=False,
                 names_to_ignore=(),
                 dunder_names_to_keep=('__implements__', '__all__', '__imports__'),
                 cleanup_globs=True):
    """
    Copy attributes defined in ``source.__dict__`` to the dictionary
    in globs (which should be the caller's :func:`globals`).

    Names that start with ``__`` are ignored (unless they are in
    *dunder_names_to_keep*). Anything found in *names_to_ignore* is
    also ignored.

    If *only_names* is given, only those attributes will be
    considered. In this case, *ignore_missing_names* says whether or
    not to raise an :exc:`AttributeError` if one of those names can't
    be found.

    If *cleanup_globs* has a true value, then common things imported but
    not used at runtime are removed, including this function.

    Returns a list of the names copied; this should be assigned to ``__imports__``.
    """
    if only_names:
        if ignore_missing_names:
            items = ((k, getattr(source, k, _NONE)) for k in only_names)
        else:
            items = ((k, getattr(source, k)) for k in only_names)
    else:
        items = iteritems(source.__dict__)

    copied = []
    for key, value in items:
        if value is _NONE:
            continue
        if key in names_to_ignore:
            continue
        if key.startswith("__") and key not in dunder_names_to_keep:
            continue
        globs[key] = value
        copied.append(key)

    if cleanup_globs:
        if 'copy_globals' in globs:
            del globs['copy_globals']

    return copied

def import_c_accel(globs, cname):
    """
    Import the C-accelerator for the *cname*
    and copy its globals.

    The *cname* should be hardcoded to match the expected
    C accelerator module.

    Unless PURE_PYTHON is set (in the environment or automatically
    on PyPy), then the C-accelerator is required.
    """
    if not cname.startswith('gevent._gevent_c'):
        # Old module code that hasn't been updated yet.
        cname = cname.replace('gevent._',
                              'gevent._gevent_c')

    name = globs.get('__name__')

    if not name or name == cname:
        # Do nothing if we're being exec'd as a file (no name)
        # or we're running from the C extension
        return


    from gevent._compat import PURE_PYTHON
    if PURE_PYTHON:
        return

    import importlib
    import warnings
    with warnings.catch_warnings():
        # Python 3.7 likes to produce
        # "ImportWarning: can't resolve
        #   package from __spec__ or __package__, falling back on
        #   __name__ and __path__"
        # when we load cython compiled files. This is probably a bug in
        # Cython, but it doesn't seem to have any consequences, it's
        # just annoying to see and can mess up our unittests.
        warnings.simplefilter('ignore', ImportWarning)
        mod = importlib.import_module(cname)

    # By adopting the entire __dict__, we get a more accurate
    # __file__ and module repr, plus we don't leak any imported
    # things we no longer need.
    globs.clear()
    globs.update(mod.__dict__)

    if 'import_c_accel' in globs:
        del globs['import_c_accel']


class Lazy(object):
    """
    A non-data descriptor used just like @property. The
    difference is the function value is assigned to the instance
    dict the first time it is accessed and then the function is never
    called again.

    Contrast with `readproperty`.
    """
    def __init__(self, func):
        self.data = (func, func.__name__)
        update_wrapper(self, func)

    def __get__(self, inst, class_):
        if inst is None:
            return self

        func, name = self.data
        value = func(inst)
        inst.__dict__[name] = value
        return value

class readproperty(object):
    """
    A non-data descriptor similar to :class:`property`.

    The difference is that the property can be assigned to directly,
    without invoking a setter function. When the property is assigned
    to, it is cached in the instance and the function is not called on
    that instance again.

    Contrast with `Lazy`, which caches the result of the function in the
    instance the first time it is called and never calls the function on that
    instance again.
    """

    def __init__(self, func):
        self.func = func
        update_wrapper(self, func)

    def __get__(self, inst, class_):
        if inst is None:
            return self

        return self.func(inst)

class LazyOnClass(object):
    """
    Similar to `Lazy`, but stores the value in the class.

    This is useful when the getter is expensive and conceptually
    a shared class value, but we don't want import-time side-effects
    such as expensive imports because it may not always be used.

    Probably doesn't mix well with inheritance?
    """

    @classmethod
    def lazy(cls, cls_dict, func):
        "Put a LazyOnClass object in *cls_dict* with the same name as *func*"
        cls_dict[func.__name__] = cls(func)

    def __init__(self, func, name=None):
        self.name = name or func.__name__
        self.func = func

    def __get__(self, inst, klass):
        if inst is None: # pragma: no cover
            return self

        val = self.func(inst)
        setattr(klass, self.name, val)
        return val


def gmctime():
    """
    Returns the current time as a string in RFC3339 format.
    """
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


###
# Release automation.
#
# Most of this is to integrate zest.releaser with towncrier. There is
# a plugin package that can do the same:
# https://github.com/collective/zestreleaser.towncrier
###

def prereleaser_middle(data): # pragma: no cover
    """
    zest.releaser prerelease middle hook for gevent.

    The prerelease step:

        asks you for a version number
        updates the setup.py or version.txt and the
        CHANGES/HISTORY/CHANGELOG file (with either
        this new version
        number and offers to commit those changes to git

    The middle hook:

        All data dictionary items are available and some questions
        (like new version number) have been asked.
        No filesystem changes have been made yet.

    It is our job to finish up the filesystem changes needed, including:

    - Calling towncrier to handle CHANGES.rst
    - Add the version number to ``versionadded``, ``versionchanged`` and
      ``deprecated`` directives in Python source.
    """
    if data['name'] != 'gevent':
        # We are specified in ``setup.cfg``, not ``setup.py``, so we do not
        # come into play for other projects, only this one. We shouldn't
        # need this check, but there it is.
        return

    import re
    import os
    import subprocess
    from gevent.testing import modules

    new_version = data['new_version']

    # Generate CHANGES.rst, remove old news entries.
    subprocess.check_call([
        'towncrier',
        'build',
        '--version', data['new_version'],
        '--yes'
    ])

    data['update_history'] = False # Because towncrier already did.

    # But unstage it; we want it to show in the diff zest.releaser will do
    subprocess.check_call([
        'git',
        'restore',
        '--staged',
        'CHANGES.rst',
    ])

    # Put the version number in source files.
    regex = re.compile(b'.. (versionchanged|versionadded|deprecated):: NEXT')
    if not isinstance(new_version, bytes):
        new_version_bytes = new_version.encode('ascii')
    else:
        new_version_bytes = new_version
    new_version_bytes = new_version.encode('ascii')
    replacement = br'.. \1:: %s' % (new_version_bytes,)
    # TODO: This should also look in the docs/ directory at
    # *.rst
    for path, _ in modules.walk_modules(
            # Start here
            basedir=os.path.join(data['reporoot'], 'src', 'gevent'),
            # Include sub-dirs
            recursive=True,
            # Include tests
            include_tests=True,
            # and other things usually excluded
            excluded_modules=(),
            # Don't return build binaries
            include_so=False,
            # Don't try to import things; we want all files.
            check_optional=False,
    ):
        with open(path, 'rb') as f:
            contents = f.read()
        new_contents, count = regex.subn(replacement, contents)
        if count:
            print("Replaced version NEXT in", path)
            with open(path, 'wb') as f:
                f.write(new_contents)

def postreleaser_before(data): # pragma: no cover
    """
    Prevents zest.releaser from modifying the CHANGES.rst to add the
    'no changes yet' section; towncrier is in charge of CHANGES.rst.

    Needs zest.releaser 6.15.0.
    """
    if data['name'] != 'gevent':
        # We are specified in ``setup.cfg``, not ``setup.py``, so we do not
        # come into play for other projects, only this one. We shouldn't
        # need this check, but there it is.
        return

    data['update_history'] = False
