# -*- coding: utf-8 -*-

# Created on 2018-10-12
# author: 欧度智能，https://www.odooai.cn
# email: 300883@qq.com
# resource of odooai
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

# Odoo在线中文用户手册（长期更新）
# https://www.odooai.cn/documentation/user/10.0/zh_CN/index.html

# Odoo10离线中文用户手册下载
# https://www.odooai.cn/odoo10_user_manual_document_offline/
# Odoo10离线开发手册下载-含python教程，jquery参考，Jinja2模板，PostgresSQL参考（odoo开发必备）
# https://www.odooai.cn/odoo10_developer_document_offline/
# description:

from odoo import api, SUPERUSER_ID, _


def pre_init_hook(cr):
    try:
        # 更新企业版指向
        sql = "UPDATE ir_module_module SET website = '%s' WHERE license like '%s' and website <> ''" % ('https://www.odooai.cn', 'OEEL%')
        cr.execute(sql)
        cr.commit()
    except Exception as e:
        pass

def post_init_hook(cr, registry):
    # a = check_module_installed(cr, ['app_web_superbar','aaaaa'])
    pass
    # cr.execute("")

def uninstall_hook(cr, registry):
    """
    数据初始化，卸载时执行
    """
    pass

def check_module_installed(cr, modules):
    # modules 输入参数是个 list，如 ['base', 'sale']
    env = api.Environment(cr, SUPERUSER_ID, {})
    installed = False
    m = env['ir.module.module'].sudo().search([('name', 'in', modules), ('state', 'in', ['installed', 'to install', 'to upgrade'])])
    if len(m) == len(modules):
        installed = True
    return len(m)

