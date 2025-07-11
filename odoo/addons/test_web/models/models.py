# -*- coding: utf-8 -*-
from odoo import fields, models


class Test_Search_PanelSource_Model(models.Model):
    _name = 'test_search_panel.source_model'
    _description = 'Source Model'

    name = fields.Char('Name', required=True)
    state = fields.Selection([('a', "A"), ('b', "B")])
    folder_id = fields.Many2one('test_search_panel.category_target_model')
    categ_id = fields.Many2one(
        'test_search_panel.category_target_model_no_parent_name')
    tag_ids = fields.Many2many(
        'test_search_panel.filter_target_model', 'rel_table', string="Tags")
    tag_id = fields.Many2one('test_search_panel.filter_target_model', string="Tag")


class Test_Search_PanelCategory_Target_Model(models.Model):
    _name = 'test_search_panel.category_target_model'
    _order = 'name'
    _description = 'Category target model'
    _parent_name = 'parent_name_id'

    name = fields.Char('Name', required=True)
    parent_name_id = fields.Many2one('test_search_panel.category_target_model')


class Test_Search_PanelCategory_Target_Model_No_Parent_Name(models.Model):
    _name = 'test_search_panel.category_target_model_no_parent_name'
    _order = 'id desc'
    _description = 'Category target model'

    name = fields.Char('Name', required=True)


class Test_Search_PanelFilter_Target_Model(models.Model):
    _name = 'test_search_panel.filter_target_model'
    _order = 'name'
    _description = 'Filter target model'

    name = fields.Char('Name', required=True)
    status = fields.Selection(
        [('cool', "Cool"), ('unknown', 'Unknown')])
    color = fields.Char()
    folder_id = fields.Many2one('test_search_panel.category_target_model')
