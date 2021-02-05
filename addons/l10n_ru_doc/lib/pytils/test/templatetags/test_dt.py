# -*- coding: utf-8 -*-
"""
Unit tests for pytils' dt templatetags for Django web framework
"""

import datetime
from pytils.test.templatetags import helpers

class DtDefaultTestCase(helpers.TemplateTagTestCase):
    
    def setUp(self):
        self.date = datetime.datetime(2007, 1, 26, 15, 50)
        self.date_before = datetime.datetime.now() - datetime.timedelta(1, 2000)
    
    def testLoad(self):
        self.check_template_tag('load_tag', u'{% load pytils_dt %}', {}, u'')
    
    def testRuStrftimeFilter(self):
        self.check_template_tag('ru_strftime_filter',
            u'{% load pytils_dt %}{{ val|ru_strftime:"%d %B %Y, %A" }}',
            {'val': self.date},
            u'26 января 2007, пятница')
    
    def testRuStrftimeInflectedFilter(self):
        self.check_template_tag('ru_strftime_inflected_filter',
            u'{% load pytils_dt %}{{ val|ru_strftime_inflected:"в %A, %d %B %Y" }}',
            {'val': self.date},
            u'в пятницу, 26 января 2007')
    
    def testRuStrftimePrepositionFilter(self):
        self.check_template_tag('ru_strftime_preposition_filter',
            u'{% load pytils_dt %}{{ val|ru_strftime_preposition:"%A, %d %B %Y" }}',
            {'val': self.date},
            u'в\xa0пятницу, 26 января 2007')
    
    def testDistanceFilter(self):
        self.check_template_tag('distance_filter',
            u'{% load pytils_dt %}{{ val|distance_of_time }}',
            {'val': self.date_before},
            u'вчера')
        
        self.check_template_tag('distance_filter',
            u'{% load pytils_dt %}{{ val|distance_of_time:3 }}',
            {'val': self.date_before},
            u'1 день 0 часов 33 минуты назад')
    
    # без отладки, если ошибка -- по умолчанию пустая строка
    def testRuStrftimeError(self):
        self.check_template_tag('ru_strftime_error',
            u'{% load pytils_dt %}{{ val|ru_strftime:"%d %B %Y" }}',
            {'val': 1},
            u'')

if __name__ == '__main__':
    import unittest
    unittest.main()
