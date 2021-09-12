# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "Odoo SaaS Kit",
  "summary"              :  """Odoo SaaS Kit allows you to run your Odoo As A SaaS business. After installation and set uo you can sell Odoo As A Saas to your client via subscription based model""",
  "category"             :  "Extra Tools",
  "version"              :  "2.0.1",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/",
  "description"          :  """Provide Odoo as a Service(Saas) on your servers with Odoo saas Kit.""",
  "live_test_url"        :  "http://odoodemo.webkul.com/demo_feedback?module=odoo_saas_kit",
  "depends"              :  [
                             'sale_management',
                             'portal',
                             'base',
                             'website_sale',
                             'account',
                            ],
  "data"                 :  [
                             'security/odoo_saas_kit_security.xml',
                             'security/ir.model.access.csv',
                             'views/res_config_views.xml',
                             'views/templates.xml',
                             'data/contract_sequence.xml',
                             'data/client_sequence.xml',
                             'data/email_templates.xml',
                             'data/contract_expiry_template.xml',
                             'views/subdomain_page.xml',
                             'data/recurring_invoice_cron.xml',
                             'data/client_creation_cron.xml',
                             'data/contract_expiry_cron.xml',
                             'views/saas_server_view.xml',
                             'views/module_category_view.xml',
                             'views/module_view.xml',
                             'views/product_view.xml',
                             'views/account_invoice_view.xml',
                             'wizards/contract_creation_view.xml',
                             'wizards/disable_client_wizard.xml',
                             'wizards/custom_domain_wizard_view.xml',
                             'views/custom_domain.xml',
                             'views/saas_plan_view.xml',
                             'views/saas_contract_view.xml',
                             'views/saas_client_view.xml',
                             'views/sale_view.xml',
                             'views/saas_portal_templates.xml',
                             'views/user_pricing_template.xml',
                             'views/menuitems.xml',
                            ],
  "images"               :  ['static/description/Banner.gif'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  749,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
  "external_dependencies":  {'python': ['urllib']},
}