# -*- coding: utf-8 -*-
# Copyright (c) 2018 gevent community
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Test environment setup.

This establishes the resources that are available for use,
which are tested with `support.is_resource_enabled`.

"""
from __future__ import absolute_import, division, print_function

# This file may be imported early, so it should take care not to import
# things it doesn't need, which means deferred imports.


def get_ALL_RESOURCES():
    "Return a fresh list of resource names."
    # RESOURCE_NAMES is the list of all known resources, including those that
    # shouldn't be enabled by default or when asking for "all" resources.
    # ALL_RESOURCES is the list of resources enabled by default or with "all" resources.

    try:
        # 3.6 and 3.7
        from test.libregrtest import ALL_RESOURCES
    except ImportError:
        # 2.7 through 3.5

        # Don't do this:
        ## from test.regrtest import ALL_RESOURCES

        # On Python 2.7 to 3.5, importing regrtest iterates
        # sys.modules and does modifications. That doesn't work well
        # when it's imported from another module at module scope.
        # Also, it makes some assumptions about module __file__ that
        # may not hold true (at least on 2.7), especially when six or
        # other module proxy objects are involved.
        # So we hardcode the list. This is from 2.7, which is a superset
        # of the defined resources through 3.5.

        ALL_RESOURCES = (
            'audio', 'curses', 'largefile', 'network', 'bsddb',
            'decimal', 'cpu', 'subprocess', 'urlfetch', 'gui',
            'xpickle'
        )

    return list(ALL_RESOURCES) + [
        # Do we test the stdlib monkey-patched?
        'gevent_monkey',
    ]


def parse_resources(resource_str=None):
    # str -> Sequence[str]

    # Parse it like libregrtest.cmdline documents:

    # -u is used to specify which special resource intensive tests to run,
    # such as those requiring large file support or network connectivity.
    # The argument is a comma-separated list of words indicating the
    # resources to test.  Currently only the following are defined:

    #     all -       Enable all special resources.
    #
    #     none -      Disable all special resources (this is the default).
    # <snip>
    #     network -   It is okay to run tests that use external network
    #                 resource, e.g. testing SSL support for sockets.
    # <snip>
    #
    #     subprocess  Run all tests for the subprocess module.
    # <snip>
    #
    # To enable all resources except one, use '-uall,-<resource>'.  For
    # example, to run all the tests except for the gui tests, give the
    # option '-uall,-gui'.

    # We make a change though: we default to 'all' resources, instead of
    # 'none'. Encountering either of those later in the string resets
    # it, for ease of working with appending to environment variables.

    if resource_str is None:
        import os
        resource_str = os.environ.get('GEVENTTEST_USE_RESOURCES')

    resources = get_ALL_RESOURCES()

    if not resource_str:
        return resources

    requested_resources = resource_str.split(',')

    for requested_resource in requested_resources:
        # empty strings are ignored; this can happen when working with
        # the environment variable if not already set:
        # ENV=$ENV,-network
        if not requested_resource:
            continue
        if requested_resource == 'all':
            resources = get_ALL_RESOURCES()
        elif requested_resource == 'none':
            resources = []
        elif requested_resource.startswith('-'):
            if requested_resource[1:] in resources:
                resources.remove(requested_resource[1:])
        else:
            # TODO: Produce a warning if it's an unknown resource?
            resources.append(requested_resource)

    return resources

def unparse_resources(resources):
    """
    Given a list of enabled resources, produce the correct environment variable
    setting to enable (only) that list.
    """
    # By default, we assume all resources are enabled, so explicitly
    # listing them here doesn't actually disable anything. To do that, we want to
    # list the ones that are disabled. This is usually shorter than starting with
    # 'none', and manually adding them back in one by one.
    #
    # 'none' must be special cased because an empty option string
    # means 'all'. Still, we're explicit about that.
    #
    # TODO: Make this produce the minimal output; sometimes 'none' and
    # adding would be shorter.

    all_resources = set(get_ALL_RESOURCES())
    enabled = set(resources)

    if enabled == all_resources:
        result = 'all'
    elif resources:
        explicitly_disabled = all_resources - enabled
        result = ''.join(sorted('-' + x for x in explicitly_disabled))
    else:
        result = 'none'
    return result


def setup_resources(resources=None):
    """
    Call either with a list of resources or a resource string.

    If ``None`` is given, get the resource string from the environment.
    """

    if isinstance(resources, str) or resources is None:
        resources = parse_resources(resources)

    from . import support
    support.use_resources = list(resources)
    support.gevent_has_setup_resources = True

    return resources

def ensure_setup_resources():
    # Call when you don't know if resources have been setup and you want to
    # get the environment variable if needed.
    # Returns an object with `is_resource_enabled`.
    from . import support
    if not support.gevent_has_setup_resources:
        setup_resources()

    return support

def exit_without_resource(resource):
    """
    Call this in standalone test modules that can't use unittest.SkipTest.

    Exits with a status of 0 if the resource isn't enabled.
    """

    if not ensure_setup_resources().is_resource_enabled(resource):
        print("Skipped: %r not enabled" % (resource,))
        import sys
        sys.exit(0)

def skip_without_resource(resource, reason=''):
    requires = 'Requires resource %r' % (resource,)
    if not reason:
        reason = requires
    else:
        reason = reason + ' (' + requires + ')'

    if not ensure_setup_resources().is_resource_enabled(resource):
        import unittest
        raise unittest.SkipTest(reason)

if __name__ == '__main__':
    print(setup_resources())
