# -*- coding: utf-8 -*-
import logging
import time

from odoo.modules.loading import force_demo
from odoo.tools import make_index_name, SQL
from odoo.tests import standalone
from odoo.addons.account.models.chart_template import AccountChartTemplate
from unittest.mock import patch

_logger = logging.getLogger(__name__)


@standalone('all_l10n')
def test_all_l10n(env):
    """ This test will install all the l10n_* modules.
    As the module install is not yet fully transactional, the modules will
    remain installed after the test.
    """

    try_loading = type(env['account.chart.template']).try_loading

    def try_loading_patch(self, template_code, company, install_demo=True, force_create=True):
        self = self.with_context(l10n_check_fields_complete=True)
        return try_loading(self, template_code, company, install_demo, force_create)


    # Ensure the presence of demo data, to see if they can be correctly installed
    if not env.ref('base.module_account').demo:
        force_demo(env)

    # Install the requiriments
    _logger.info('Installing all l10n modules')
    l10n_mods = env['ir.module.module'].search([
        ('name', '=like', 'l10n_%'),
        ('state', '=', 'uninstalled'),
        '!', ('name', '=like', 'l10n_hk_hr%'),  #failling for obscure reason
    ])
    with patch.object(AccountChartTemplate, 'try_loading', try_loading_patch):
        l10n_mods.button_immediate_install()

    # In all_l10n tests we need to verify demo data
    demo_failures = env['ir.demo_failure'].search([])
    if demo_failures:
        _logger.warning("Error while testing demo data for all_l10n tests.")
        for failure in demo_failures:
            _logger.warning("Demo data of module %s has failed: %s",
                failure.module_id.name, failure.error)

    env.reset()     # clear the set of environments
    env = env()     # get an environment that refers to the new registry
    idxs = []
    for model in env.registry.values():
        if not model._auto:
            continue

        for field in model._fields.values():
            # TODO: handle non-orm indexes where the account field is alone or first
            if not field.store or field.index \
                    or field.type != 'many2one' \
                    or field.comodel_name != 'account.account':
                continue

            idxname = make_index_name(model._table, field.name)
            env.cr.execute(SQL(
                "CREATE INDEX IF NOT EXISTS %s ON %s (%s)%s",
                SQL.identifier(idxname),
                SQL.identifier(model._table),
                SQL.identifier(field.name),
                SQL("") if field.required else SQL(" WHERE %s IS NOT NULL", SQL.identifier(field.name)),
            ))
            idxs.append(idxname)

    # Install Charts of Accounts
    _logger.info('Loading chart of account')
    already_loaded_codes = set(env['res.company'].search([]).mapped('chart_template'))
    not_loaded_codes = [
        (template_code, template)
        for template_code, template in env['account.chart.template']._get_chart_template_mapping().items()
        if template_code not in already_loaded_codes
        # We can't make it disappear from the list, but we raise a UserError if it's not already the COA
        and template_code not in ('syscohada', 'syscebnl')
    ]
    companies = env['res.company'].create([
        {
            'name': f'company_coa_{template_code}',
            'country_id': template['country_id'],
        }
        for template_code, template in not_loaded_codes
    ])
    env.cr.commit()

    # Install the CoAs
    start = time.time()
    env.cr.execute('ANALYZE')
    logger = logging.getLogger('odoo.loading')
    logger.runbot('ANALYZE took %s seconds', time.time() - start)  # not sure this one is useful
    for (template_code, _template), company in zip(not_loaded_codes, companies):
        env.user.company_ids += company
        env.user.company_id = company
        _logger.info('Testing COA: %s (company: %s)', template_code, company.name)
        try:
            env['account.chart.template'].with_context(l10n_check_fields_complete=True).try_loading(template_code, company, install_demo=True)
            env.cr.commit()
        except Exception:
            _logger.error("Error when creating COA %s", template_code, exc_info=True)
            env.cr.rollback()

    env.cr.execute(SQL("DROP INDEX %s", SQL(", ").join(map(SQL.identifier, idxs))))
    env.cr.commit()
