# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning


class EbayCategory(models.Model):
    _name = 'ebay.category'
    _description = 'eBay Category'

    name = fields.Char('Name')
    full_name = fields.Char('Full Name', store=True, compute='_compute_full_name')
    # The IDS are string because of the limitation of the SQL integer range
    category_id = fields.Char('Category ID')
    category_parent_id = fields.Char('Category Parent ID')
    leaf_category = fields.Boolean(default=False)
    category_type = fields.Selection(
        [('ebay', 'Official eBay Category'), ('store', 'Custom Store Category')],
        string='Category Type',
    )

    @api.depends('category_parent_id', 'name')
    def _compute_full_name(self):
        for rec in self:
            name = rec.name if rec.name else ''
            parent_id = rec.category_parent_id
            category_type = rec.category_type
            while parent_id != '0':
                parent = rec.search([
                    ('category_id', '=', parent_id),
                    ('category_type', '=', category_type),
                ])
                parent_name = parent.name if parent.name else ''
                name = parent_name + " > " + name
                parent_id = parent.category_parent_id if parent.category_parent_id else '0'
            rec.full_name = name

    @api.depends('full_name')
    def _compute_display_name(self):
        for cat in self:
            cat.display_name = cat.full_name

    @api.model
    def _cron_sync(self, auto_commit=False):
        try:
            self._sync_categories()
        except UserError as e:
            if auto_commit:
                self.env.cr.rollback()
                self.env.user.partner_id.message_post(
                    body=_("eBay error: Impossible to synchronize the categories. \n'%s'", e.args[0]))
                self.env.cr.commit()
            else:
                raise e
        except RedirectWarning as e:
            if not auto_commit:
                raise e
            # not configured, ignore
            return

    @api.model
    def _sync_categories(self):
        self._sync_store_categories()

        domain = self.env['ir.config_parameter'].sudo().get_param('ebay_domain')
        prod = self.env['product.template']
        # First call to 'GetCategories' to only get the categories' version
        categories = prod._ebay_execute('GetCategories')
        ebay_version = categories.dict()['Version']
        version = self.env['ir.config_parameter'].sudo().get_param(
            'ebay_sandbox_category_version'
            if domain == 'sand'
            else 'ebay_prod_category_version')
        if version != ebay_version:
            # If the version returned by eBay is different than the one in Odoo
            # Another call to 'GetCategories' with all the information (ReturnAll) is done
            self.env['ir.config_parameter'].set_param('ebay_sandbox_category_version'
                                                      if domain == 'sand'
                                                      else 'ebay_prod_category_version',
                                                      ebay_version)
            if domain == 'sand':
                levellimit = 2
            else:
                levellimit = 4
            call_data = {
                'DetailLevel': 'ReturnAll',
                'LevelLimit': levellimit,
            }
            response = prod._ebay_execute('GetCategories', call_data)
            categories = response.dict()['CategoryArray']['Category']
            # Delete the eBay categories not existing anymore on eBay
            category_ids = [c['CategoryID'] for c in categories]
            self.search([
                ('category_id', 'not in', category_ids),
                ('category_type', '=', 'ebay'),
            ]).unlink()
            self._create_categories(categories)

    @api.model
    def _create_categories(self, categories):
        for category in categories:
            cat = self.search([
                ('category_id', '=', category['CategoryID']),
                ('category_type', '=', 'ebay'),
            ])
            if not cat:
                cat = self.create({
                    'category_id': category['CategoryID'],
                    'category_type': 'ebay',
                })
            cat.write({
                'name': category['CategoryName'],
                'category_parent_id': category['CategoryParentID'] if category['CategoryID'] != category['CategoryParentID'] else '0',
                'leaf_category': category.get('LeafCategory'),
            })
            if category['CategoryLevel'] == '1':
                call_data = {
                    'CategoryID': category['CategoryID'],
                    'ViewAllNodes': True,
                    'DetailLevel': 'ReturnAll',
                    'AllFeaturesForCategory': True,
                }
                response = self.env['product.template']._ebay_execute('GetCategoryFeatures', call_data)
                if 'ConditionValues' in response.dict()['Category']:
                    conditions = response.dict()['Category']['ConditionValues']['Condition']
                    if not isinstance(conditions, list):
                        conditions = [conditions]
                    for condition in conditions:
                        if not self.env['ebay.item.condition'].search([('code', '=', condition['ID'])]):
                            self.env['ebay.item.condition'].create({
                                'code': condition['ID'],
                                'name': condition['DisplayName'],
                            })

    @api.model
    def _sync_store_categories(self):
        try:
            response = self.env['product.template']._ebay_execute('GetStore')
        except UserError as e:
            # If the user is not using a store we don't fetch the store categories
            if '13003' in e.args[0]:
                return
            raise e
        categories = response.dict()['Store']['CustomCategories']['CustomCategory']
        if not isinstance(categories, list):
            categories = [categories]
        new_categories = []
        self._create_store_categories(categories, '0', new_categories)
        # Delete the store categories not existing anymore on eBay
        self.search([
            ('category_id', 'not in', new_categories),
            ('category_type', '=', 'store'),
        ]).unlink()

    @api.model
    def _create_store_categories(self, categories, parent_id, new_categories):
        for category in categories:
            cat = self.search([
                ('category_id', '=', category['CategoryID']),
                ('category_type', '=', 'store'),
            ])
            if not cat:
                cat = self.create({
                    'category_id': category['CategoryID'],
                    'category_type': 'store',
                })
            cat.write({
                'name': category['Name'],
                'category_parent_id': parent_id,
            })
            new_categories.append(category['CategoryID'])
            if 'ChildCategory' in category:
                childs = category['ChildCategory']
                if not isinstance(childs, list):
                    childs = [childs]
                cat._create_store_categories(childs, cat.category_id, new_categories)
            else:
                cat.leaf_category = True


class EbayPolicy(models.Model):
    _name = 'ebay.policy'
    _description = 'eBay Policy'

    name = fields.Char('Name')
    policy_id = fields.Char('Policy ID')
    policy_type = fields.Char('Type')
    short_summary = fields.Text('Summary')

    @api.model
    def _sync_policies(self):
        response = self.env['product.template']._ebay_execute('GetUserPreferences',
            {'ShowSellerProfilePreferences': True})
        if 'SellerProfilePreferences' not in response.dict() or \
           not response.dict()['SellerProfilePreferences']['SupportedSellerProfiles']:
                raise UserError(_('No Business Policies'))
        policies = response.dict()['SellerProfilePreferences']['SupportedSellerProfiles']['SupportedSellerProfile']
        if not isinstance(policies, list):
            policies = [policies]
        # Delete the policies not existing anymore on eBay
        policy_ids = [p['ProfileID'] for p in policies]
        self.search([('policy_id', 'not in', policy_ids)]).unlink()
        for policy in policies:
            record = self.search([('policy_id', '=', policy['ProfileID'])])
            if not record:
                record = self.create({
                    'policy_id': policy['ProfileID'],
                })
            record.write({
                'name': policy['ProfileName'],
                'policy_type': policy['ProfileType'],
                'short_summary': policy['ShortSummary'] if 'ShortSummary' in policy else ' ',
            })


class EbayItemCondition(models.Model):
    _name = 'ebay.item.condition'
    _description = 'eBay Item Condition'

    name = fields.Char('Name')
    code = fields.Integer('Code')


class EbaySite(models.Model):
    _name = "ebay.site"
    _description = 'eBay Site'

    name = fields.Char("Name", readonly=True)
    ebay_id = fields.Char("eBay ID", readonly=True)
