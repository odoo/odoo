# -*- coding: utf-8 -*-
import unittest2

class URLCase(unittest2.TestCase):
    """
    URLCase moved out of test_requests, otherwise discovery attempts to
    instantiate and run it
    """
    def __init__(self, user, url, source, result):
        super(URLCase, self).__init__()
        self.user = user
        self.url = url
        self.source = source
        self.result = result

    @property
    def username(self):
        return self.user or "Anonymous Coward"

    def __str__(self):
        if self.source:
            return "%s (from %s, as %s)" % (self.url, self.source, self.username)
        return "%s (as %s)" % (self.url, self.username)

    __repr__ = __str__

    def shortDescription(self):
        return ""

    def runTest(self):
        code = self.result.getcode()
        self.assertIn(
            code, xrange(200, 300),
            "Fetching %s as %s returned an error response (%d)" % (
                self.url, self.username, code))
