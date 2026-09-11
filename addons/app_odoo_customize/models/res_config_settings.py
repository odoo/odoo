# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    app_system_name = fields.Char('System Name', help="Setup System Name,which replace Odoo",
                                  default='odooAi', config_parameter='app_system_name')
    app_show_lang = fields.Boolean('Show Quick Language Switcher',
                                   help="When enable,User can quick switch language in user menu",
                                   config_parameter='app_show_lang')
    app_show_debug = fields.Boolean('Show Quick Debug', help="When enable,everyone login can see the debug menu",
                                    config_parameter='app_show_debug')
    app_show_documentation = fields.Boolean('Show Documentation', help="When enable,User can visit user manual",
                                            config_parameter='app_show_documentation')
    # 停用
    app_show_documentation_dev = fields.Boolean('Show Developer Documentation',
                                                help="When enable,User can visit development documentation")
    app_show_support = fields.Boolean('Show Support', help="When enable,User can vist your support site",
                                      config_parameter='app_show_support')
    app_show_account = fields.Boolean('Show My Account', help="When enable,User can login to your website",
                                      config_parameter='app_show_account')
    app_show_enterprise = fields.Boolean('Show Enterprise Tag', help="Uncheck to hide the Enterprise tag",
                                         config_parameter='app_show_enterprise')
    app_show_share = fields.Boolean('Show Share Dashboard', help="Uncheck to hide the Odoo Share Dashboard",
                                    config_parameter='app_show_share')
    app_show_poweredby = fields.Boolean('Show Powered by Odoo', help="Uncheck to hide the Powered by text",
                                        config_parameter='app_show_poweredby')
    group_show_author_in_apps = fields.Boolean(string="Show Author in Apps Dashboard", implied_group='app_odoo_customize.group_show_author_in_apps',
                                               help="Uncheck to Hide Author and Website in Apps Dashboard")
    module_odoo_referral = fields.Boolean('Show Odoo Referral', help="Uncheck to remove the Odoo Referral")

    app_documentation_url = fields.Char('Documentation Url', config_parameter='app_documentation_url')
    app_documentation_dev_url = fields.Char('Developer Documentation Url', config_parameter='app_documentation_dev_url')
    app_support_url = fields.Char('Support Url', config_parameter='app_support_url')
    app_account_title = fields.Char('My Odoo.com Account Title', config_parameter='app_account_title')
    app_account_url = fields.Char('My Odoo.com Account Url', config_parameter='app_account_url')
    app_enterprise_url = fields.Char('Customize Module Url(eg. Enterprise)', config_parameter='app_enterprise_url')
    app_ribbon_name = fields.Char('Show Demo Ribbon', config_parameter='app_ribbon_name')
    app_navbar_pos_pc = fields.Selection(string="Navbar PC", selection=[
        ('top', 'Top(Default)'),
        ('bottom', 'Bottom'),
        # ('left', 'Left'),
    ], config_parameter='app_navbar_pos_pc')
    app_navbar_pos_mobile = fields.Selection(string="Navbar Mobile", selection=[
        ('top', 'Top(Default)'),
        ('bottom', 'Bottom'),
        # ('left', 'Left'),
    ], config_parameter='app_navbar_pos_mobile')
    
    # 安全与提速
    app_debug_only_admin = fields.Boolean('Debug for Admin', config_parameter='app_debug_only_admin',
                                          help="Check to only Debug / Debug Assets for Odoo Admin. Deny debug from url for other user.")
    app_stop_subscribe = fields.Boolean('Stop Odoo Subscribe / Follow', help="Check to stop subscribe and follow. This to make odoo speed up.",
                                        config_parameter='app_stop_subscribe')
    # 处理额外模块
    module_app_odoo_doc = fields.Boolean("Help Document Anywhere", help='Get Help Documentation on current odoo operation or topic.')
    module_app_chatgpt = fields.Boolean("Ai Center", help='Use Ai to boost you business.')
    
    # 应用帮助文档
    app_doc_root_url = fields.Char('Help of topic domain', config_parameter='app_doc_root_url', default='https://odooai.cn')

    @api.model
    def set_module_url(self):
        if not self._app_check_sys_op():
            raise UserError(_('Not allow.'))
        try:
            config_parameter = self.env['ir.config_parameter'].sudo()
            app_enterprise_url = config_parameter.get_param('app_enterprise_url', 'https://www.odooai.cn')
            modules = self.env['ir.module.module'].search([('license', 'like', 'OEEL%'), ('website', '!=', False)])
            if modules:
                sql = "UPDATE ir_module_module SET website = '%s' WHERE id IN %s" % (app_enterprise_url, tuple(modules.ids))
                self._cr.execute(sql)
        except Exception as e:
            pass

    # 清数据，o=对象, s=序列 
    def _remove_app_data(self, o, s=[]):
        if not self._app_check_sys_op():
            raise UserError(_('Not allow.'))
        
        for line in o:
            # 检查是否存在
            try:
                if not self.env['ir.model']._get(line):
                    continue
            except Exception as e:
                _logger.warning('remove data error get ir.model: %s,%s', line, e)
                continue
            obj_name = line
            obj = self.pool.get(obj_name)
            if not obj:
                # 有时安装出错数据乱，没有 obj 但有 table
                t_name = obj_name.replace('.', '_')
            else:
                t_name = obj._table

            sql = "delete from %s" % t_name
            # 增加多公司处理
            try:
                self._cr.execute(sql)
                self._cr.commit()
            except Exception as e:
                _logger.warning('remove data error: %s,%s', line, e)
        # 更新序号
        for line in s:
            domain = ['|', ('code', '=ilike', line + '%'), ('prefix', '=ilike', line + '%')]
            try:
                seqs = self.env['ir.sequence'].sudo().search(domain)
                if seqs.exists():
                    seqs.write({
                        'number_next': 1,
                    })
            except Exception as e:
                _logger.warning('reset sequence data error: %s,%s', line, e)
        return True
    
    def remove_sales(self):
        to_removes = [
            # 清除销售单据
            'sale.order.line',
            'sale.order',
            # 销售提成，自用
            # 'sale.commission.line',
            # 不能删除报价单模板
            'sale.order.template.option',
            'sale.order.template.line',
            'sale.order.template',
        ]
        seqs = [
            'sale',
        ]
        return self._remove_app_data(to_removes, seqs)

    def remove_product(self):
        to_removes = [
            # 清除产品数据
            'product.product',
            'product.template',
        ]
        seqs = [
            'product.product',
        ]
        return self._remove_app_data(to_removes, seqs)

    def remove_product_attribute(self):
        to_removes = [
            # 清除产品属性
            'product.attribute.value',
            'product.attribute',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs)

    def remove_pos(self):
        if not self._app_check_sys_op():
            return False
        to_removes = [
            # 清除POS单据
            'pos.payment',
            'pos.order.line',
            'pos.order',
            'pos.session',
        ]
        seqs = [
            'pos.',
        ]
        res = self._remove_app_data(to_removes, seqs)

        # 更新要关帐的值，因为 store=true 的计算字段要重置

        try:
            statement = self.env['account.bank.statement'].search([])
            for s in statement:
                s._end_balance()
        except Exception as e:
            _logger.error('reset sequence data error: %s', e)
        return res

    def remove_purchase(self):
        to_removes = [
            # 清除采购单据
            'purchase.order.line',
            'purchase.order',
            'purchase.requisition.line',
            'purchase.requisition',
        ]
        seqs = [
            'purchase.',
        ]
        return self._remove_app_data(to_removes, seqs)

    def remove_expense(self):
        to_removes = [
            # 清除
            'hr.expense.sheet',
            'hr.expense',
            'hr.payslip',
            'hr.payslip.run',
        ]
        seqs = [
            'hr.expense.',
        ]
        return self._remove_app_data(to_removes, seqs)

    def remove_mrp(self):
        to_removes = [
            # 清除生产单据
            'mrp.workcenter.productivity',
            'mrp.workorder',
            # 'mrp.production.workcenter.line',
            'change.production.qty',
            'mrp.production',
            # 'mrp.production.product.line',
            'mrp.unbuild',
            'change.production.qty',
            # 'sale.forecast.indirect',
            # 'sale.forecast',
        ]
        seqs = [
            'mrp.',
        ]
        return self._remove_app_data(to_removes, seqs)

    def remove_mrp_bom(self):
        to_removes = [
            # 清除生产BOM
            'mrp.bom.line',
            'mrp.bom',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs)

    def remove_inventory(self):
        to_removes = [
            # 清除库存单据
            'stock.quant',
            'stock.move.line',
            'stock.package_level',
            'stock.quantity.history',
            'stock.quant.package',
            'stock.move',
            # 'stock.pack.operation',
            'stock.picking',
            'stock.scrap',
            'stock.picking.batch',
            'stock.inventory.adjustment.name',
            'stock.valuation.layer',
            'stock.lot',
            # 'stock.fixed.putaway.strat',
            'procurement.group',
        ]
        seqs = [
            'stock.',
            'picking.',
            'procurement.group',
            'product.tracking.default',
            'WH/',
        ]
        return self._remove_app_data(to_removes, seqs)

    def remove_account(self):
        to_removes = [
            # 清除财务会计单据
            'payment.transaction',
            # 'account.voucher.line',
            # 'account.voucher',
            # 'account.invoice.line',
            # 'account.invoice.refund',
            # 'account.invoice',
            'account.bank.statement.line',
            'account.payment',
            'account.batch.payment',
            'account.analytic.line',
            'account.analytic.account',
            'account.partial.reconcile',
            'account.move.line',
            'hr.expense.sheet',
            'account.move',
        ]
        res = self._remove_app_data(to_removes, [])

        # extra 更新序号
        domain = [
            ('company_id', '=', self.env.company.id),
            '|', ('code', '=ilike', 'account.%'),
            '|', ('prefix', '=ilike', 'BNK1/%'),
            '|', ('prefix', '=ilike', 'CSH1/%'),
            '|', ('prefix', '=ilike', 'INV/%'),
            '|', ('prefix', '=ilike', 'EXCH/%'),
            '|', ('prefix', '=ilike', 'MISC/%'),
            '|', ('prefix', '=ilike', '账单/%'),
            ('prefix', '=ilike', '杂项/%')
        ]
        try:
            seqs = self.env['ir.sequence'].search(domain)
            if seqs.exists():
                seqs.write({
                    'number_next': 1,
                })
        except Exception as e:
            _logger.error('reset sequence data error: %s,%s', domain, e)
        return res

    def remove_account_chart(self):
        company_id = self.env.company.id
        self = self.with_company(self.env.company)
        to_removes = [
            # 清除财务科目，用于重设。有些是企业版的也处理下
            'account.reconcile.model',
            'account.transfer.model.line',
            'account.transfer.model',
            'res.partner.bank',
            # 'account.invoice',
            'account.payment',
            'account.bank.statement',
            # 'account.tax.account.tag',
            'account.tax',
            'account.tax.template',
            # 'wizard_multi_charts_accounts',
            'account.account',
            # 'account.journal',
        ]
        # todo: 要做 remove_hr，因为工资表会用到 account
        # 更新account关联，很多是多公司字段，故只存在 ir_property，故在原模型，只能用update
        try:
            field1 = self.env['ir.model.fields']._get('product.template', "taxes_id").id
            field2 = self.env['ir.model.fields']._get('product.template', "supplier_taxes_id").id

            sql = "delete from ir_default where (field_id = %s or field_id = %s) and company_id=%d" \
                  % (field1, field2, company_id)
            sql2 = "update account_journal set bank_account_id=NULL where company_id=%d;" % company_id
            self._cr.execute(sql)
            self._cr.execute(sql2)
            self._cr.commit()
        except Exception as e:
            _logger.error('remove data error: %s,%s', 'account_chart: set tax and account_journal', e)

        # 增加对 pos的处理
        if self.env['ir.model']._get('pos.config'):
            self.env['pos.config'].write({
                'journal_id': False,
            })
        #     todo: 以下处理参考 res.partner的合并，将所有m2o的都一次处理，不需要次次找模型
        # partner 处理
        try:
            rec = self.env['res.partner'].search([])
            rec.write({
                'property_account_receivable_id': None,
                'property_account_payable_id': None,
            })
            self._cr.commit()
        except Exception as e:
            _logger.error('remove data error: %s,%s', 'account_chart', e)
        # 品类处理
        try:
            rec = self.env['product.category'].search([])
            rec.write({
                'property_account_income_categ_id': None,
                'property_account_expense_categ_id': None,
                'property_account_creditor_price_difference_categ': None,
                'property_stock_account_input_categ_id': None,
                'property_stock_account_output_categ_id': None,
                'property_stock_valuation_account_id': None,
                'property_stock_journal': None,
            })
            self._cr.commit()
        except Exception as e:
            pass
        # 产品处理
        try:
            rec = self.env['product.template'].search([])
            rec.write({
                'property_account_income_id': None,
                'property_account_expense_id': None,
                'property_account_creditor_price_difference': None,
            })
            self._cr.commit()
        except Exception as e:
            pass
        # pos处理，清支付，清账本
        try:
            rec = self.env['pos.config'].search([])
            rec.write({
                'invoice_journal_id': None,
                'journal_id': None,
                'payment_method_ids': None,
                'fiscal_position_ids': None,
            })
            self._cr.commit()
        except Exception as e:
            pass
        # 日记账处理
        try:
            rec = self.env['account.journal'].search([])
            rec.write({
                'account_control_ids': None,
                'bank_account_id': None,
                'default_account_id': None,
                'loss_account_id': None,
                'profit_account_id': None,
                'suspense_account_id': None,
            })
            self._cr.commit()
        except Exception as e:
            pass  # raise Warning(e)

        # 库存计价处理
        try:
            rec = self.env['stock.location'].search([])
            rec.write({
                'valuation_in_account_id': None,
                'valuation_out_account_id': None,
            })
            self._cr.commit()
        except Exception as e:
            pass  # raise Warning(e)
        # 库存计价默认值处理
        try:
            # 当前有些日记账的默认值要在 ir.property 处理 _set_default，比较麻烦
            todo_list = [
                'property_stock_account_input_categ_id',
                'property_stock_account_output_categ_id',
                'property_stock_valuation_account_id',
                'property_stock_journal',
            ]
            for name in todo_list:
                field_id = self.env['ir.model.fields']._get('product.category', name).id
                prop = self.env['ir.property'].sudo().search([
                    ('fields_id', '=', field_id),
                ])
                if prop:
                    prop.unlink()
            self._cr.commit()
        except Exception as e:
            pass  # raise Warning(e)
        # 先 unlink 处理
        j_ids = self.env['account.journal'].sudo().search([])
        if j_ids:
            try:
                j_ids.unlink()
                self._cr.commit()
            except Exception as e:
                pass  # raise Warning(e)
        try:
            c_ids = self.env['res.company'].sudo().search([])
            c_ids.sudo().write({
                'chart_template_id': False,
            })
        except Exception as e:
            pass  # raise Warning(e)
        seqs = []
        res = self._remove_app_data(to_removes, seqs)
        return res

    def remove_project(self):
        to_removes = [
            # 清除项目
            'account.analytic.line',
            'project.task',
            # 'project.forecast',
            'project.update',
            'project.collaborator',
            'project.milestone',
            # 'project.project.stage',
            'project.task.recurrence',
            # 表名为 project_task_user_rel
            'project.task.stage.personal',
            'project.project',
        ]
        seqs = []
        try:
            sql = "delete from project_sale_line_employee_map"
            self._cr.execute(sql)
            self._cr.commit()
        except Exception as e:
            _logger.error('remove data error: %s,%s', 'project: project_sale_line_employee_map', e)
        return self._remove_app_data(to_removes, seqs)

    def remove_quality(self):
        to_removes = [
            # 清除质检数据
            'quality.check',
            'quality.alert',
            # 'quality.point',
            # 'quality.alert.stage',
            # 'quality.alert.team',
            # 'quality.point.test_type',
            # 'quality.reason',
            # 'quality.tag',
        ]
        seqs = [
            'quality.check',
            'quality.alert',
            # 'quality.point',
        ]
        return self._remove_app_data(to_removes, seqs)

    def remove_quality_setting(self):
        to_removes = [
            # 清除质检设置
            'quality.point',
            'quality.alert.stage',
            'quality.alert.team',
            'quality.point.test_type',
            'quality.reason',
            'quality.tag',
        ]
        return self._remove_app_data(to_removes)
    
    def remove_event(self):
        to_removes = [
            # 清除
            'website.event.menu',
            'event.sponsor',
            'event.sponsor.type',
            'event.meeting.room',
            'event.registration.answer',
            'event.question.answer',
            'event.question',
            'event.quiz',
            'event.quiz.answer',
            'event.quiz.question',
            'event.track',
            'event.track.visitor',
            'event.track.location',
            'event.track.tag',
            'event.track.tag.category',
            'event.track.stage',
            'event.mail.registration',
            'event.mail',
            'event.type.mail',
            'event.lead.rule',
            'event.booth.registration',
            'event.booth',
            'event.type',
            'event.type.booth',
            'event.booth.category',
            'event.registration',
            'event.ticket',
            'event.type.ticket',
            'event.event',
            'event.stage',
            'event.tag',
            'event.tag.category',
            'event.type',
        ]
        seqs = [
            'event.event.',
        ]
        return self._remove_app_data(to_removes, seqs)

    def remove_website(self):
        to_removes = [
            # 清除网站数据，w, w_blog
            'blog.tag.category',
            'blog.tag',
            'blog.post',
            'blog.blog',
            'product.wishlist',
            'website.published.multi.mixin',
            'website.published.mixin',
            'website.multi.mixin',
            'website.visitor',
            'website.rewrite',
            'website.seo.metadata',
            # 'website.page',
            # 'website.menu',
            # 'website',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs)

    def remove_message(self):
        to_removes = [
            # 清除消息数据
            'mail.message',
            'mail.followers',
            'mail.activity',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs)

    def remove_workflow(self):
        to_removes = [
            # 清除工作流
            # 'wkf.workitem',
            # 'wkf.instance',
        ]
        seqs = []
        return self._remove_app_data(to_removes, seqs)

    def remove_all_biz(self):
        self.remove_account()
        self.remove_quality()
        self.remove_inventory()
        self.remove_purchase()
        self.remove_mrp()
        self.remove_sales()
        self.remove_project()
        self.remove_pos()
        self.remove_expense()
        self.remove_event()
        self.remove_message()
        return True

    def reset_cat_loc_name(self):
        ids = self.env['product.category'].search([
            ('parent_id', '!=', False)
        ], order='complete_name')
        for rec in ids:
            try:
                rec._compute_complete_name()
            except:
                pass
        ids = self.env['stock.location'].search([
            ('location_id', '!=', False),
            ('usage', '!=', 'views'),
        ], order='complete_name')
        for rec in ids:
            try:
                rec._compute_complete_name()
            except:
                pass
        return True

    def action_set_app_doc_root_to_my(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.app_doc_root_url = base_url

    # def action_set_all_to_app_doc_root_url(self):
    #     if self.app_doc_root_url:
