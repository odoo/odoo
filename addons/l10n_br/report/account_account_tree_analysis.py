# -*- coding: utf-8 -*-
# Copyright 2017 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import division, print_function, unicode_literals


from odoo import api, fields, models, _
from odoo.tools.sql import drop_view_if_exists


SQL_ACCOUNT_TREE_ANALYSIS_VIEW = '''
create or replace view account_account_tree_analysis_view as
select
    a1.id as parent_account_id,
    a1.id as child_account_id,
    1 as level
from
    account_account a1
    
union all

select
    a2.id as parent_account_id,
    a1.id as child_account_id,
    2 as level
from
    account_account a1
    join account_account a2 on a1.parent_id = a2.id

union all

select
    a3.id as parent_account_id,
    a1.id as child_account_id,
    3 as level
from
    account_account a1
    join account_account a2 on a1.parent_id = a2.id
    join account_account a3 on a2.parent_id = a3.id

union all

select
    a4.id as parent_account_id,
    a1.id as child_account_id,
    4 as level
from
    account_account a1
    join account_account a2 on a1.parent_id = a2.id
    join account_account a3 on a2.parent_id = a3.id
    join account_account a4 on a3.parent_id = a4.id

union all

select
    a5.id as parent_account_id,
    a1.id as child_account_id,
    5 as level
from
    account_account a1
    join account_account a2 on a1.parent_id = a2.id
    join account_account a3 on a2.parent_id = a3.id
    join account_account a4 on a3.parent_id = a4.id
    join account_account a5 on a4.parent_id = a5.id

union all

select
    a6.id as parent_account_id,
    a1.id as child_account_id,
    6 as level
from
    account_account a1
    join account_account a2 on a1.parent_id = a2.id
    join account_account a3 on a2.parent_id = a3.id
    join account_account a4 on a3.parent_id = a4.id
    join account_account a5 on a4.parent_id = a5.id
    join account_account a6 on a5.parent_id = a6.id

union all

select
    a7.id as parent_account_id,
    a1.id as child_account_id,
    7 as level
from
    account_account a1
    join account_account a2 on a1.parent_id = a2.id
    join account_account a3 on a2.parent_id = a3.id
    join account_account a4 on a3.parent_id = a4.id
    join account_account a5 on a4.parent_id = a5.id
    join account_account a6 on a5.parent_id = a6.id
    join account_account a7 on a6.parent_id = a7.id

union all

select
    a8.id as parent_account_id,
    a1.id as child_account_id,
    8 as level
from
    account_account a1
    join account_account a2 on a1.parent_id = a2.id
    join account_account a3 on a2.parent_id = a3.id
    join account_account a4 on a3.parent_id = a4.id
    join account_account a5 on a4.parent_id = a5.id
    join account_account a6 on a5.parent_id = a6.id
    join account_account a7 on a6.parent_id = a7.id
    join account_account a8 on a7.parent_id = a8.id

union all

select
    a9.id as parent_account_id,
    a1.id as child_account_id,
    9 as level
from
    account_account a1
    join account_account a2 on a1.parent_id = a2.id
    join account_account a3 on a2.parent_id = a3.id
    join account_account a4 on a3.parent_id = a4.id
    join account_account a5 on a4.parent_id = a5.id
    join account_account a6 on a5.parent_id = a6.id
    join account_account a7 on a6.parent_id = a7.id
    join account_account a8 on a7.parent_id = a8.id
    join account_account a9 on a8.parent_id = a9.id

union all

select
    a10.id as parent_account_id,
    a1.id as child_account_id,
    10 as level
from
    account_account a1
    join account_account a2 on a1.parent_id = a2.id
    join account_account a3 on a2.parent_id = a3.id
    join account_account a4 on a3.parent_id = a4.id
    join account_account a5 on a4.parent_id = a5.id
    join account_account a6 on a5.parent_id = a6.id
    join account_account a7 on a6.parent_id = a7.id
    join account_account a8 on a7.parent_id = a8.id
    join account_account a9 on a8.parent_id = a9.id
    join account_account a10 on a9.parent_id = a10.id;
'''

DROP_TABLE = '''
    DROP TABLE IF EXISTS account_account_tree_analysis
'''

SQL_SELECT_ACCOUNT_TREE_ANALYSIS = '''
select
  row_number() over() as id,
  child_account_id,
  parent_account_id,
  level

from
  account_account_tree_analysis_view

order by
  child_account_id,
  parent_account_id;
'''

SQL_ACCOUNT_TREE_ANALYSIS_TABLE = '''
create table account_account_tree_analysis as
''' + SQL_SELECT_ACCOUNT_TREE_ANALYSIS + '''

create index account_account_tree_analysis_child_account_id
  on account_account_tree_analysis
  (child_account_id);

create index account_account_tree_analysis_parent_account_id
  on account_account_tree_analysis
  (parent_account_id);

create index account_account_tree_analysis_level
  on account_account_tree_analysis
  (level);
'''


class AccountAccountTreeAnalysis(models.Model):
    _name = b'account.account.tree.analysis'
    _description = 'Account Account Tree Analysis'
    _auto = False

    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, 'account_account_tree_analysis_view')
        self._cr.execute(DROP_TABLE)
        self._cr.execute(SQL_ACCOUNT_TREE_ANALYSIS_VIEW)
        self._cr.execute(SQL_ACCOUNT_TREE_ANALYSIS_TABLE)

    parent_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Parent account',
        index=True,
    )
    child_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Child account',
        index=True,
    )
    level = fields.Integer(
        string='Level',
        index=True,
    )
