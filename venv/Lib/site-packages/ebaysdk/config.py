# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os

from ebaysdk import log
from ebaysdk.exception import ConnectionConfigError
from ebaysdk.utils import parse_yaml


class Config(object):
    """Config Class for all APIs connections

    >>> c = Config(domain='api.ebay.com')
    >>> c.set('fname', 'tim')
    >>> c.get('fname')
    'tim'
    >>> c.get('missingkey', 'defaultvalue')
    'defaultvalue'
    >>> c.set('number', 22)
    >>> c.get('number')
    22
    """

    def __init__(self, domain, connection_kwargs=dict(), config_file='ebay.yaml'):
        self.config_file = config_file
        self.domain = domain
        self.values = dict()
        self.config_file_used = []
        self.connection_kwargs = connection_kwargs

        self._populate_yaml_defaults()

    def _populate_yaml_defaults(self):
        "Returns a dictionary of YAML defaults."

        # check for absolute path
        if self.config_file and os.path.exists(self.config_file):
            self.config_file_used = self.config_file

            dataobj = parse_yaml(self.config_file)

            for k, val in dataobj.get(self.domain, {}).items():
                self.set(k, val)

            return self

        # check other directories
        dirs = ['.', os.path.expanduser('~'), '/etc']
        for mydir in dirs:
            myfile = "%s/%s" % (mydir, self.config_file)

            if os.path.exists(myfile):
                self.config_file_used = myfile

                dataobj = parse_yaml(myfile)

                for k, val in dataobj.get(self.domain, {}).items():
                    self.set(k, val)

                return self

        if self.config_file:
            raise ConnectionConfigError(
                'config file %s not found. Set config_file=None for use without YAML config.' % self.config_file)

    def file(self):
        return self.config_file_used

    def get(self, cKey, defaultValue=None):
        # log.debug('get: %s=%s' % (cKey, self.values.get(cKey, defaultValue)))
        return self.values.get(cKey, defaultValue)

    def set(self, cKey, defaultValue, force=False):

        if force:
            # log.debug('set (force): %s=%s' % (cKey, defaultValue))
            self.values.update({cKey: defaultValue})

        elif cKey in self.connection_kwargs and self.connection_kwargs[cKey] is not None:
            # log.debug('set: %s=%s' % (cKey, self.connection_kwargs[cKey]))
            self.values.update({cKey: self.connection_kwargs[cKey]})

        # otherwise, use yaml default and then fall back to
        # the default set in the __init__()
        else:
            if cKey not in self.values:
                # log.debug('set: %s=%s' % (cKey, defaultValue))
                self.values.update({cKey: defaultValue})
            else:
                pass
