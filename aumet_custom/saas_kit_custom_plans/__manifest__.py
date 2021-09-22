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
  "name"                 :  "Odoo SaaS Custom Plans",
  "summary"              :  """Odoo SaaS Custom Plans allows you to provide option to your clients to select custom Plans of their choice for Odoo Saas Kit""",
  "category"             :  "Extra Tools",
  "version"              :  "1.0.4",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/",
  "description"          :  """Provide Custom plan option for Odoo saas Kit.""",
  "live_test_url"        :  "http://odoodemo.webkul.com/demo_feedback?module=saas_kit_custom_plans",
  "depends"              :  [
                             'odoo_saas_kit',
                            ],
  "data"                 :  [
                             'security/ir.model.access.csv',
                             'views/saas_client.xml',
                             'views/product_view.xml',
                             'views/product_page.xml',
                             'views/saas_module.xml',
                             'views/odoo_version_view.xml',
                             'views/res_config_view.xml',
                             'data/request_sequence.xml',
                             'data/contract_expiry_warning_template.xml',
                             'views/contract_view.xml',
                             'views/menuitems.xml',
                             'views/page_template.xml',
                             'views/portal_template.xml',
                             'views/template.xml',
                             'data/product.xml',
                             'data/module_installation_crone.xml',
                             'data/contract_expiry_warning_mail_crone.xml'
                            ],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  99,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}
