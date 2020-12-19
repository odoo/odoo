# -*- coding: utf-8 -*-
from odoo import models, fields


class LibraryBook(models.Model):
    _name = 'library.book'
    #模块名称
    _description = 'Library Book'
    #模块描述
    """
    Char：字符型，使用size参数定义字符串长度。
    Text：文本型，无长度限制。
    Boolean：布尔型（True，False）
    Interger：整型
    Float：浮点型，使用digits参数定义整数部分和小数部分位数。如digits=(10,6)
    Datetime：日期时间型
    Date：日期型
    Binary：二进制型
    selection：下拉框字段。
    
    """
    name = fields.Char('Title', required=True)
    #如果ruquired为True，那么字段是必填的
    date_release = fields.Date('Release Date')
    author_ids = fields.Many2many('res.partner', string='Authors')
    #多对多，One2many：One2many：一对多关系。
    is_public = fields.Boolean(groups='my_library.group_library_librarian')
    #groups是
    private_notes = fields.Text(groups='my_library.group_library_librarian')
    report_missing = fields.Text(
        string="Book is missing",
        groups='my_library.group_library_librarian')

    def report_missing_book(self):
        self.ensure_one()
        message = "Book is missing (Reported by: %s)" % self.env.user.name
        self.sudo().write({
            'report_missing': message
        })
