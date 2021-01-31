# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase,SingleTransactionCase, tagged
from ..models.ac_obj import ACTools
from odoo import  exceptions

#将科目名称按级次分解成逐级科目名称的列表
@tagged('ACTools_splitAccountName')
class Test_splitAccountName(TransactionCase):
    def test_have_space(self):
        '''不能包含空格'''
        accountName=" 1 1 2"
        a=ACTools.splitAccountName(accountName)
        for item in a:
            rl=item.find(" ")
            self.assertEqual(-1, rl,"不应含有空格")

    def test_many(self):
        '''分解多级科目'''
        a=ACTools.splitAccountName("1---2---3---4---5---6")
        self.assertEqual(a[0], '1',"多级科目分解错误")
        self.assertEqual(a[1], '1---2',"多级科目分解错误")
        self.assertEqual(a[2], "1---2---3","多级科目分解错误")
        self.assertEqual(a[3], "1---2---3---4","多级科目分解错误")
        self.assertEqual(a[4], "1---2---3---4---5","多级科目分解错误")
        self.assertEqual(a[5], "1---2---3---4---5---6","多级科目分解错误")
        self.assertEqual(len(a), 6,"多级科目分解后长度不对")
    
    def test_one(self):
        '''分解一级科目'''
        accountName="1213"
        a=ACTools.splitAccountName(accountName)
        self.assertEqual(len(a), 1,"一级科目分解后长度不对")
        self.assertEqual(a[0], accountName,"一级科目分解错误")

#比较科目后的核算项目类别,返回需要添加的类别
@tagged('ACTools_itemClassUpdata')
class Test_itemClassUpdata(TransactionCase):
    def test_return_list(self):
        '''返回列表'''
        _class_a=[]
        _class_b=[]
        rl = ACTools.itemClassUpdata(_class_a,_class_b)
        self.assertIsInstance(rl,list,"应该返回列表")
    def test_equal(self):
        '''相同'''
        _class_a=[['部门',True]]
        _class_b=[['部门',True]]
        rl = ACTools.itemClassUpdata(_class_a,_class_b)
        self.assertEqual(len(rl),0,"两个列表应该相同")
    
    def test_normal_1(self):
        "多一个"
        _class_a=[["部门",True],['员工',False],['费用',False]]
        _class_b=[["部门",True],['材料',False]]
        rl = ACTools.itemClassUpdata(_class_a,_class_b)
        self.assertListEqual(rl,[['材料',False]])
    
    def test_normal_2(self):
        "多两个"
        _class_a=[["部门",True],['员工',False],['费用',False]]
        _class_b=[["部门",True],['材料',False],['成本',False]]
        rl = ACTools.itemClassUpdata(_class_a,_class_b)
        self.assertListEqual(rl,[['材料',False],['成本',False]])
            
    def test_normal_3(self):
        "少一个"
        _class_a=[["部门",True],['员工',False],['费用',False]]
        _class_b=[["部门",True],['费用',False]]
        rl = ACTools.itemClassUpdata(_class_a,_class_b)
        self.assertListEqual(rl,[])

    def test_normal_4(self):
        "少了必选项目"
        _class_a=[["部门",True],['员工',False],['费用',False]]
        _class_b=[]
        with self.assertRaises(exceptions.UserError):
            rl = ACTools.itemClassUpdata(_class_a,_class_b)

    def test_normal_5(self):
        "少了必选项目"
        _class_a=[["部门",True],['员工',False],['费用',False]]
        _class_b=[['员工',False],['成本',False]]
        with self.assertRaises(exceptions.UserError):
            rl = ACTools.itemClassUpdata(_class_a,_class_b)

    def test_normal_6(self):
        "必选项目不同"
        _class_a=[["部门",True],['员工',False],['费用',False]]
        _class_b=[['员工',True],['成本',False]]
        with self.assertRaises(exceptions.UserError):
            rl = ACTools.itemClassUpdata(_class_a,_class_b)
    
    def test_normal_2(self):
        "原来没有"
        _class_a=[]
        _class_b=[["部门",True],['材料',False],['成本',False]]
        rl = ACTools.itemClassUpdata(_class_a,_class_b)
        self.assertListEqual(rl,[["部门",True],['材料',False],['成本',False]])



        