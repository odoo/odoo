# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2009 Gábor Dukai
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name' : '中国会计科目表 - Accounting',
    'version' : '1.0',
    'category': 'Localization/Account Charts',
    'author' : 'openerp-china.org',
    'maintainer':'openerp-china.org',
    'website':'http://openerp-china.org',
    'url':'http://code.google.com/p/openerp-china/source/browse/#svn/trunk/l10n_cn',
    'description': """
添加中文省份数据
科目类型\会计科目表模板\增值税\辅助核算类别\管理会计凭证簿\财务会计凭证簿
============================================================
    """,
    'depends' : ['base','account'],
    'demo' : [],
    'data' : [
        'account_chart.xml',
        'l10n_chart_cn_wizard.xml',
        'base_data.xml',
    ],
    'license': 'GPL-3',
    'auto_install': False,
    'installable': True,
    'certificate': '00925445983542952285',
    'images': ['images/config_chart_l10n_cn.jpeg','images/l10n_cn_chart.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

