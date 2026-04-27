# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from . import models

_logger = logging.getLogger(__name__)


def _accounting_post_init(env):
    country_code = env.company.country_id.code
    if country_code:
        module_list = []

        if country_code in ('AU', 'CA', 'US'):
            module_list.append('account_reports_cash_basis')

        module_ids = env['ir.module.module'].search([('name', 'in', module_list), ('state', '=', 'uninstalled')])
        if module_ids:
            module_ids.sudo().button_install()


def uninstall_hook(env):
    try:
        group_user = env.ref("account.group_account_user")
        group_user.write({
            'name': "Show Full Accounting Features",
            'implied_ids': [(3, env.ref('account.group_account_invoice').id)],
            'category_id': env.ref("base.module_category_hidden").id,
        })
        group_readonly = env.ref("account.group_account_readonly")
        group_readonly.write({
            'name': "Show Full Accounting Features - Readonly",
            'category_id': env.ref("base.module_category_hidden").id,
        })
    except ValueError as e:
        _logger.warning(e)

    try:
        group_manager = env.ref("account.group_account_manager")
        group_manager.write({'name': "Billing Manager",
                             'implied_ids': [(4, env.ref("account.group_account_invoice").id),
                                             (3, env.ref("account.group_account_readonly").id),
                                             (3, env.ref("account.group_account_user").id)]})
    except ValueError as e:
        _logger.warning(e)

    # make the account_accountant features disappear (magic)
    env.ref("account.group_account_user").write({'users': [(5, False, False)]})
    env.ref("account.group_account_readonly").write({'users': [(5, False, False)]})

    # this menu should always be there, as the module depends on account.
    # if it's not, there is something wrong with the db that should be investigated.
    invoicing_menu = env.ref("account.menu_finance")
    menus_to_move = [
        "account.menu_finance_receivables",
        "account.menu_finance_payables",
        "account.menu_finance_entries",
        "account.menu_finance_reports",
        "account.menu_finance_configuration",
        "account.menu_board_journal_1",
    ]
    for menu_xmlids in menus_to_move:
        try:
            env.ref(menu_xmlids).parent_id = invoicing_menu
        except ValueError as e:
            _logger.warning(e)
