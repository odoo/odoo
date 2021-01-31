# -*- coding: utf-8 -*-
import logging

import odoo
from odoo import api
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError, UserError,AccessError
import logging

_logger = logging.getLogger(__name__)

@tagged('org_user_access')
class Test_org_access(TransactionCase):
    def test_hasnot_access(self):
        '''管理员为普通用户分配机构权限'''
        _logger.info("用户机构/主体权限测试开始。。。")
        #创建两个用户
        user1_name ="test_user1"
        user2_name ="test_user2"
        user1 =self._createAccountUser(user1_name)
        user2 =self._createAccountUser(user2_name)
        #创建一个机构
        org_name="test_org"
        org = self._createOrg(org_name)
        #为第一个用户赋予权限
        self._addUser2org(user1, org)
        #测试第一个用户可以查询该机构
        record1 = self.env['accountcore.org'].with_user(user1.id).search([('name','=',org_name)])
        self.assertEquals(len(record1), 1)
        #测试第二个用户查询该机构，会抛出错误
        with self.assertRaises(AccessError):
            record2 = self.env['accountcore.org'].with_user(user2.id).search([('name','=',org_name)])
            self.assertEquals(len(record2),0,)
            record1.with_user(user2.id).unlink()
            self.env['accountcore.org'].with_user(user2.id).create({'name':"test_create_org"})
            _logger.info("用户机构/主体权限测试结束。。。")
    def _createAccountUser(self ,user_name):
        user=self.env['res.users'].create({
            'name': user_name,
            'login': user_name,
            'groups_id': [(6, 0, [self.ref('accountcore.group_role_ac')])],
        })
        return user
    def _createOrg(self ,org_name):
        org =self.env['accountcore.org'].sudo().create({'name':org_name})
        return org
    def _addUser2org(self, user, org):
        org.write({'user_ids':[(4,user.id,0)]})