# -*- coding: utf-8 -*-

from odoo import models, fields, api


class xxtr(models.Model):
    _name = 'xxtr.xxtr'
    _description = 'xxtr.xxtr'

    name = fields.Char()
    value = fields.Integer()
    value2 = fields.Float(compute="_value_pc", store=True)
    description = fields.Text()

    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value2 = float(record.value) / 100

class XXWizard(models.TransientModel):


# 要点1: 使用瞬态模型
    _name = 'st.wizard'

    name = fields.Char('名字')
    age = fields.Char('年龄')
# // 要点2:这些字段在弹窗中由用户赋值
    @api.model
    def default_get(self, default_fields):
        """
        为向导赋默认值。
        """
        result = super(XXWizard, self).default_get(default_fields)

        result.update({
            'name': '你好',
        })
        return result

    # type: # 动作类型，默认为ir.actions.act_window
    # view_type: 跳转时打开的视图类型
    # view_mode: 列出允许使用的视图模式
    # context: 给目标视图传参数，如默认搜索之类的，如{‘search_default_group_assign’:1}
    # limit: 列表视图一页的记录数
    # target: 打开新视图的方式，current是在本视图打开，new是弹出一个窗口打开
    # auto_refresh：为1时在视图中添加一个刷新功能
    # auto_search：加载默认视图后，自动搜索
    # multi：视图中有个更多按钮，若multi设为True, 更多按钮显示在tree视图，否则显示在form视图
    # res_model：想打开视图的对应模块
    # res_id: 参数为id，加载指定id的视图，但只在view_type为form时生效，若没有这个参数则会新建一条记录
    # view_id: 参数是id，若一个模块有多于>1个视图时需要指定视图id，可根据视图名称去ir.ui.view模块搜索
    # views：是(view_id,view_type) 元组对列表，第一组是动作默认打开的视图
    # flags: 对视图面板进行一些设置，如{‘form’: {‘action_buttons’: True, ‘options’: {‘mode’: ‘edit’}}}即对form视图进行一些设置，action_buttons为True时调出编辑保存按钮，options’: {‘mode’: ‘edit’}时则打开时对默认状态为编辑状态

    def action_tw_base_price_quotation(self):
        value = self.name
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'xxtr.xxtr',
            # 'limit':1,
            'name':'xxtr window',
            'multi':True,
            'auto_refresh':1,
            # 'view_type': 'form',
            # 设置过滤条件search_default_+所需判断的字段名
            'context': {'search_default_name':value},
            'view_mode': 'tree,form',
            # 'views': [(True, "tree")],
            'target': 'main',
            'auto_search': True,
        }

