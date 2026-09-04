# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class MailMail(models.Model):
    _inherit = "mail.mail"
    
    # 猴子补丁模式，改默认发邮件逻辑
    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        for m in self:
            email_to = m.email_to
            # 忽略掉无效email，避免被ban
            if email_to:
                if email_to.find('no-reply@odooai.cn') != -1 or email_to.find('postmaster-odoo@odooai.cn') != -1:
                    pass
                elif email_to.find('example.com') != -1 or email_to.find('@sunpop.cn') != -1 or email_to.find('@odooapp.cn') != -1:
                    _logger.warning(_("=================Email to ignore: %s") % email_to)
                    self = self - m
        if not self:
            return True
        return super(MailMail, self)._send(auto_commit, raise_exception, smtp_session)
