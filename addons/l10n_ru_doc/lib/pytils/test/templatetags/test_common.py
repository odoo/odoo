# -*- coding: utf-8 -*-
"""
Unit tests for pytils' templatetags common things
"""

import unittest

from pytils import templatetags as tt

class TemplateTagsCommonsTestCase(unittest.TestCase):
    
    def testInitDefaults(self):
        """
        Unit-tests for pytils.templatetags.init_defaults
        """
        self.assertEquals(tt.init_defaults(debug=False, show_value=False), ('', u''))
        self.assertEquals(tt.init_defaults(debug=False, show_value=True), ('%(value)s', u'%(value)s'))
        self.assertEquals(tt.init_defaults(debug=True, show_value=False), ('unknown: %(error)s', u'unknown: %(error)s'))
        self.assertEquals(tt.init_defaults(debug=True, show_value=True), ('unknown: %(error)s', u'unknown: %(error)s'))


if __name__ == '__main__':
    unittest.main()
