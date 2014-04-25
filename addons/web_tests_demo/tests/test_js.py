# -*- coding: utf-8 -*-
from openerp.addons.web.tests.test_js import WebSuite

def load_tests(loader, standard_tests, _):
    standard_tests.addTest(WebSuite('web_tests_demo'))
    return standard_tests
