# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    app_system_name = fields.Char('System Name', help="Setup System Name,which replace Odoo")
    app_show_lang = fields.Boolean('Show Quick Language Switcher',
                                   help="When enable,User can quick switch language in user menu")
    app_show_debug = fields.Boolean('Show Quick Debug', help="When enable,everyone login can see the debug menu")
    app_show_documentation = fields.Boolean('Show Documentation', help="When enable,User can visit user manual")
    app_show_documentation_dev = fields.Boolean('Show Developer Documentation',
                                                help="When enable,User can visit development documentation")
    app_show_support = fields.Boolean('Show Support', help="When enable,User can vist your support site")
    app_show_account = fields.Boolean('Show My Account', help="When enable,User can login to your website")
    app_show_enterprise = fields.Boolean('Show Enterprise Tag', help="Uncheck to hide the Enterprise tag")
    app_show_share = fields.Boolean('Show Share Dashboard', help="Uncheck to hide the Odoo Share Dashboard")
    app_show_poweredby = fields.Boolean('Show Powered by Odoo', help="Uncheck to hide the Powered by text")
    group_show_author_in_apps = fields.Boolean(string="Show Author in Apps Dashboard", implied_group='app_odoo_customize.group_show_author_in_apps',
                                               help="Uncheck to Hide Author and Website in Apps Dashboard")
    module_odoo_referral = fields.Boolean('Show Odoo Referral', help="Uncheck to remove the Odoo Referral")

    app_documentation_url = fields.Char('Documentation Url')
    app_documentation_dev_url = fields.Char('Developer Documentation Url')
    app_support_url = fields.Char('Support Url')
    app_account_title = fields.Char('My Odoo.com Account Title')
    app_account_url = fields.Char('My Odoo.com Account Url')
    app_enterprise_url = fields.Char('Customize Module Url(eg. Enterprise)')
    app_ribbon_name = fields.Char('Show Demo Ribbon')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir_config = self.env['ir.config_parameter'].sudo()
        app_system_name = ir_config.get_param('app_system_name', default='odooApp')

        app_show_lang = True if ir_config.get_param('app_show_lang') == "True" else False
        app_show_debug = True if ir_config.get_param('app_show_debug') == "True" else False
        app_show_documentation = True if ir_config.get_param('app_show_documentation') == "True" else False
        app_show_documentation_dev = True if ir_config.get_param('app_show_documentation_dev') == "True" else False
        app_show_support = True if ir_config.get_param('app_show_support') == "True" else False
        app_show_account = True if ir_config.get_param('app_show_account') == "True" else False
        app_show_enterprise = True if ir_config.get_param('app_show_enterprise') == "True" else False
        app_show_share = True if ir_config.get_param('app_show_share') == "True" else False
        app_show_poweredby = True if ir_config.get_param('app_show_poweredby') == "True" else False

        app_documentation_url = ir_config.get_param('app_documentation_url',
                                                    default='https://www.sunpop.cn/documentation/user/12.0/en/index.html')
        app_documentation_dev_url = ir_config.get_param('app_documentation_dev_url',
                                                        default='https://www.sunpop.cn/documentation/12.0/index.html')
        app_support_url = ir_config.get_param('app_support_url', default='https://www.sunpop.cn/trial/')
        app_account_title = ir_config.get_param('app_account_title', default='My Online Account')
        app_account_url = ir_config.get_param('app_account_url', default='https://www.sunpop.cn/my-account/')
        app_enterprise_url = ir_config.get_param('app_enterprise_url', default='https://www.sunpop.cn')
        app_ribbon_name = ir_config.get_param('app_ribbon_name', default='*Sunpop.cn')
        res.update(
            app_system_name=app_system_name,
            app_show_lang=app_show_lang,
            app_show_debug=app_show_debug,
            app_show_documentation=app_show_documentation,
            app_show_documentation_dev=app_show_documentation_dev,
            app_show_support=app_show_support,
            app_show_account=app_show_account,
            app_show_enterprise=app_show_enterprise,
            app_show_share=app_show_share,
            app_show_poweredby=app_show_poweredby,

            app_documentation_url=app_documentation_url,
            app_documentation_dev_url=app_documentation_dev_url,
            app_support_url=app_support_url,
            app_account_title=app_account_title,
            app_account_url=app_account_url,
            app_enterprise_url=app_enterprise_url,
            app_ribbon_name=app_ribbon_name
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ir_config = self.env['ir.config_parameter'].sudo()
        ir_config.set_param("app_system_name", self.app_system_name or "")
        ir_config.set_param("app_show_lang", self.app_show_lang or "False")
        ir_config.set_param("app_show_debug", self.app_show_debug or "False")
        ir_config.set_param("app_show_documentation", self.app_show_documentation or "False")
        ir_config.set_param("app_show_documentation_dev", self.app_show_documentation_dev or "False")
        ir_config.set_param("app_show_support", self.app_show_support or "False")
        ir_config.set_param("app_show_account", self.app_show_account or "False")
        ir_config.set_param("app_show_enterprise", self.app_show_enterprise or "False")
        ir_config.set_param("app_show_share", self.app_show_share or "False")
        ir_config.set_param("app_show_poweredby", self.app_show_poweredby or "False")

        ir_config.set_param("app_documentation_url",
                            self.app_documentation_url or "https://www.sunpop.cn/documentation/user/12.0/en/index.html")
        ir_config.set_param("app_documentation_dev_url",
                            self.app_documentation_dev_url or "https://www.sunpop.cn/documentation/12.0/index.html")
        ir_config.set_param("app_support_url", self.app_support_url or "https://www.sunpop.cn/trial/")
        ir_config.set_param("app_account_title", self.app_account_title or "My Online Account")
        ir_config.set_param("app_account_url", self.app_account_url or "https://www.sunpop.cn/my-account/")
        ir_config.set_param("app_enterprise_url", self.app_enterprise_url or "https://www.sunpop.cn")
        ir_config.set_param("app_ribbon_name", self.app_ribbon_name or "*Sunpop.cn")

    def set_module_url(self):
        sql = "UPDATE ir_module_module SET website = '%s' WHERE license like '%s' and website <> ''" % (self.app_enterprise_url, 'OEEL%')
        try:
            self._cr.execute(sql)
            self._cr.commit()
        except Exception as e:
            pass

    # 清数据，o=对象, s=序列 
    def remove_app_data(self, o, s=[]):
        for line in o:
            obj_name = line
            obj = self.pool.get(obj_name)
            if not obj:
                # 有时安装出错数据乱，没有 obj 但有 table
                t_name = obj_name.replace('.', '_')
            else:
                t_name = obj._table

            sql = "delete from %s" % t_name
            try:
                self._cr.execute(sql)
                self._cr.commit()
            except Exception as e:
                _logger.error('remove data error: %s,%s', line, e)
        # 更新序号
        for line in s:
            domain = [('code', '=ilike', line + '%')]
            try:
                seqs = self.env['ir.sequence'].sudo().search(domain)
                if seqs.exists():
                    seqs.write({
                        'number_next': 1,
                    })
            except Exception as e:
                _logger.error('reset sequence data error: %s,%s', line, e)
        return True
    
    def remove_sales(self):
        to_removes = [
            # 清除销售单据
            'sale.order.line',
            'sale.order',
            # 销售提成，自用
            # 'sale.commission.line',
            # 不能删除报价单模板
            # 'sale.order.template.option',
            # 'sale.order.template.line',
            # 'sale.order.template',
        ]
        seqs = [
            'sale',
        ]
        return self.remove_app_data(to_removes, seqs)

    def remove_product(self):
        to_removes = [
            # 清除产品数据
            'product.product',
            'product.template',
        ]
        seqs = [
            'product.product',
        ]
        return self.remove_app_data(to_removes, seqs)

    def remove_product_attribute(self):
        to_removes = [
            # 清除产品属性
            'product.attribute.value',
            'product.attribute',
        ]
        seqs = []
        return self.remove_app_data(to_removes, seqs)

    def remove_pos(self):
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
        res = self.remove_app_data(to_removes, seqs)

        # 更新要关帐的值，因为 store=true 的计算字段要重置

        try:
            statement = self.env['account.bank.statement'].sudo().search([])
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
        return self.remove_app_data(to_removes, seqs)

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
        return self.remove_app_data(to_removes, seqs)

    def remove_mrp(self):
        to_removes = [
            # 清除生产单据
            'mrp.workcenter.productivity',
            'mrp.workorder',
            'mrp.production.workcenter.line',
            'change.production.qty',
            'mrp.production',
            'mrp.production.product.line',
            'mrp.unbuild',
            'change.production.qty',
            'sale.forecast.indirect',
            'sale.forecast',
        ]
        seqs = [
            'mrp.',
        ]
        return self.remove_app_data(to_removes, seqs)

    def remove_mrp_bom(self):
        to_removes = [
            # 清除生产BOM
            'mrp.bom.line',
            'mrp.bom',
        ]
        seqs = []
        return self.remove_app_data(to_removes, seqs)

    def remove_inventory(self):
        to_removes = [
            # 清除库存单据
            'stock.quant',
            'stock.move.line',
            'stock.package.level',
            'stock.quantity.history',
            'stock.quant.package',
            'stock.move',
            # 'stock.pack.operation',
            'stock.picking',
            'stock.scrap',
            'stock.picking.batch',
            'stock.inventory.line',
            'stock.inventory',
            'stock.valuation.layer',
            'stock.production.lot',
            # 'stock.fixed.putaway.strat',
            'procurement.group',
        ]
        seqs = [
            'stock.',
            'picking.',
            'WH/',
        ]
        return self.remove_app_data(to_removes, seqs)

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
            'account.analytic.line',
            'account.analytic.account',
            'account.partial.reconcile',
            'account.move.line',
            'hr.expense.sheet',
            'account.move',
        ]
        res = self.remove_app_data(to_removes, [])

        # extra 更新序号
        domain = [
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
        to_removes = [
            # 清除财务科目，用于重设
            'res.partner.bank',
            'res.bank',
            'account.move.line',
            'account.invoice',
            'account.payment',
            'account.bank.statement',
            'account.tax.account.tag',
            'account.tax',
            'account.account.account.tag',
            'wizard_multi_charts_accounts',
            'account.journal',
            'account.account',
        ]
        # todo: 要做 remove_hr，因为工资表会用到 account
        # 更新account关联，很多是多公司字段，故只存在 ir_property，故在原模型，只能用update
        try:
            # reset default tax，不管多公司
            field1 = self.env['ir.model.fields']._get('product.template', "taxes_id").id
            field2 = self.env['ir.model.fields']._get('product.template', "supplier_taxes_id").id

            sql = ("delete from ir_default where field_id = %s or field_id = %s") % (field1, field2)
            sql2 = ("update account_journal set bank_account_id=NULL;")
            self._cr.execute(sql)
            self._cr.execute(sql2)
            self._cr.commit()
        except Exception as e:
            pass
        try:
            # 增加对 pos的处理
            sql = ("update pos_config set journal_id=NULL;")
            self._cr.execute(sql)
            self._cr.commit()
        except Exception as e:
            pass
        try:
            rec = self.env['res.partner'].search([])
            for r in rec:
                r.write({
                    'property_account_receivable_id': None,
                    'property_account_payable_id': None,
                })
        except Exception as e:
            _logger.error('remove data error: %s,%s', 'account_chart', e)
        try:
            rec = self.env['product.category'].search([])
            for r in rec:
                r.write({
                    'property_account_income_categ_id': None,
                    'property_account_expense_categ_id': None,
                    'property_account_creditor_price_difference_categ': None,
                    'property_stock_account_input_categ_id': None,
                    'property_stock_account_output_categ_id': None,
                    'property_stock_valuation_account_id': None,
                })
        except Exception as e:
            pass
        try:
            rec = self.env['stock.location'].search([])
            for r in rec:
                r.write({
                    'valuation_in_account_id': None,
                    'valuation_out_account_id': None,
                })
        except Exception as e:
            pass

        seqs = []
        return self.remove_app_data(to_removes, seqs)

    def remove_project(self):
        to_removes = [
            # 清除项目
            'account.analytic.line',
            'project.task',
            'project.forecast',
            'project.project',
        ]
        seqs = []
        return self.remove_app_data(to_removes, seqs)

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
        return self.remove_app_data(to_removes, seqs)

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
        return self.remove_app_data(to_removes)

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
            'website.redirect',
            'website.seo.metadata',
            # 'website.page',
            # 'website.menu',
            # 'website',
        ]
        seqs = []
        return self.remove_app_data(to_removes, seqs)

    def remove_message(self):
        to_removes = [
            # 清除消息数据
            'mail.message',
            'mail.followers',
            'mail.activity',
        ]
        seqs = []
        return self.remove_app_data(to_removes, seqs)

    def remove_workflow(self):
        to_removes = [
            # 清除工作流
            'wkf.workitem',
            'wkf.instance',
        ]
        seqs = []
        return self.remove_app_data(to_removes, seqs)

    def remove_all_biz(self):
        self.remove_account()
        self.remove_inventory()
        self.remove_mrp()
        self.remove_purchase()
        self.remove_sales()
        self.remove_project()
        self.remove_pos()
        self.remove_expense()
        self.remove_quality()
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
