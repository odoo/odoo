# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models


class hiHdeActionButtos(models.Model):
    _name = 'hide.action.buttons'
    model_names = fields.Char(string="Model name")

    @api.model
    def check_if_group_view(self,*args, **kwargs):
        models_list=self.search([])
        lists=[]
        if models_list and ',' in models_list.model_names:
            lists=models_list.model_names.split(',')

        else:
            lists =[models_list.model_names]
        result={'group_hide_action_menu_button_view_list':False,'group_hide_action_menu_button_view_form':False,'models':lists}
        if self.env.user.has_group('hide_action_menu_buttons.group_hide_action_menu_button_view_list') :
            result['group_hide_action_menu_button_view_list']=True
        if self.env.user.has_group('hide_action_menu_buttons.group_hide_action_menu_button_view_form'):
            result['group_hide_action_menu_button_view_form']=True
        return  result
