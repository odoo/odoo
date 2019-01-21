# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


class TestUi(odoo.tests.TransactionCase):

    def _new_value(self, values):
        return self.env['product.attribute.value'].new(values)

    def test_color_contrast_redish(self):
        self.assertEquals(self._new_value({'name': 'red'}).contrast_compatiblity(), 'black')
        self.assertEquals(self._new_value({'name': 'red', 'html_color': 'red'}).contrast_compatiblity(), 'black')
        self.assertEquals(self._new_value({'name': 'red', 'html_color': '#ff0000'}).contrast_compatiblity(), 'black')
        self.assertEquals(self._new_value({'name': 'red', 'html_color': '#FF0000'}).contrast_compatiblity(), 'black')

        self.assertEquals(self._new_value({'name': 'tomato'}).contrast_compatiblity(), 'black')
        self.assertEquals(self._new_value({'name': 'tomato', 'html_color': 'TOMATO'}).contrast_compatiblity(), 'black')
        self.assertEquals(self._new_value({'name': 'tomato', 'html_color': '#ff6347'}).contrast_compatiblity(), 'black')
        self.assertEquals(self._new_value({'name': 'tomato', 'html_color': '#FF6347'}).contrast_compatiblity(), 'black')

        self.assertEquals(self._new_value({'name': 'darkred'}).contrast_compatiblity(), 'white')
        self.assertEquals(self._new_value({'name': 'darkred', 'html_color': 'darkred'}).contrast_compatiblity(), 'white')
        self.assertEquals(self._new_value({'name': 'darkred', 'html_color': '#8b0000'}).contrast_compatiblity(), 'white')

    def test_color_contrast_black(self):
        self.assertEquals(self._new_value({'name': 'black'}).contrast_compatiblity(), 'red')
        self.assertEquals(self._new_value({'name': 'black', 'html_color': 'black'}).contrast_compatiblity(), 'red')
        self.assertEquals(self._new_value({'name': 'black', 'html_color': '#000000'}).contrast_compatiblity(), 'red')

    def test_color_contrast_white(self):
        self.assertEquals(self._new_value({'name': 'white'}).contrast_compatiblity(), 'red')
        self.assertEquals(self._new_value({'name': 'white', 'html_color': 'White'}).contrast_compatiblity(), 'red')
        self.assertEquals(self._new_value({'name': 'white', 'html_color': '#ffffff'}).contrast_compatiblity(), 'red')
        self.assertEquals(self._new_value({'name': 'white', 'html_color': '#FFFFFF'}).contrast_compatiblity(), 'red')

    def test_color_contrast_blueish(self):
        self.assertEquals(self._new_value({'name': 'blue'}).contrast_compatiblity(), 'white')
        self.assertEquals(self._new_value({'name': 'blue', 'html_color': 'blue'}).contrast_compatiblity(), 'white')
        self.assertEquals(self._new_value({'name': 'blue', 'html_color': '#0000ff'}).contrast_compatiblity(), 'white')
        self.assertEquals(self._new_value({'name': 'blue', 'html_color': '#0000FF'}).contrast_compatiblity(), 'white')

        self.assertEquals(self._new_value({'name': 'lightcyan'}).contrast_compatiblity(), 'red')
        self.assertEquals(self._new_value({'name': 'lightcyan', 'html_color': 'lightcyan'}).contrast_compatiblity(),
                          'red')
        self.assertEquals(self._new_value({'name': 'lightcyan', 'html_color': '#e0ffff'}).contrast_compatiblity(),
                          'red')

    def test_color_contrast_other_values(self):
        self.assertEquals(self._new_value({'name': 'mycolor'}).contrast_compatiblity(), 'red')
        self.assertEquals(self._new_value({'name': 'odoopurple', 'html_color': 'odoopurple'}).contrast_compatiblity(),
                          'red')
        self.assertEquals(self._new_value({'name': 'white', 'html_color': '##ffffff'}).contrast_compatiblity(),
                          'red')
