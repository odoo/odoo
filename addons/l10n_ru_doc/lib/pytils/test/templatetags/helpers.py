# -*- coding: utf-8 -*-
"""
Helpers for templatetags' unit tests in Django webframework
"""

from django.conf import settings
from django.utils.encoding import smart_str

encoding = 'utf-8'

settings.configure(
    TEMPLATE_DIRS=(),
    TEMPLATE_CONTEXT_PROCESSORS=(),
    TEMPLATE_LOADERS=(),
    INSTALLED_APPS=('pytils',),
    DEFAULT_CHARSET=encoding,
)

from django import template
from django.template import loader

import unittest




class TemplateTagTestCase(unittest.TestCase):
    """
    TestCase for testing template tags and filters
    """
    def check_template_tag(self, template_name, template_string, context, result_string):
        """
        Method validates output of template tag or filter
        
        @param template_name: name of template
        @type template_name: C{str}
        
        @param template_string: contents of template
        @type template_string: C{str} or C{unicode}

        @param context: rendering context
        @type context: C{dict}

        @param result_string: reference output
        @type result_string: C{str} or C{unicode}
        """
        
        def test_template_loader(template_name, template_dirs=None):
            return smart_str(template_string), template_name
        
        loader.template_source_loaders = [test_template_loader,]
        
        output = loader.get_template(template_name).render(template.Context(context))
        self.assertEquals(output, result_string)

