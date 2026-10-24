# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import SUPERUSER_ID, Command, api

_logger = logging.getLogger(__name__)

SE_TEMPLATES = ('se_K1', 'se_K2', 'se_K3', 'se_K2_HB', 'se_K2_NPO')


def _add_missing_k2_accounts(env, company):
    """Create the K2 accounts a former K2 mini company does not have yet.

    Existing accounts are matched on their code and linked to the template
    xmlid, so nothing is duplicated. Taxes and fiscal positions are left alone.
    """
    ChartTemplate = env['account.chart.template'].with_company(company)
    Account = env['account.account'].with_company(company).with_context(active_test=False)
    existing = {
        account.code: account
        for account in Account.search(Account._check_company_domain(company))
    }
    created = 0
    for xmlid, vals in ChartTemplate._parse_csv('se_K2', 'account.account').items():
        account = ChartTemplate.ref(xmlid, raise_if_not_found=False) or existing.get(vals['code'])
        if not account:
            tags = [env.ref(tag.strip()).id for tag in (vals.get('tag_ids') or '').split(',') if tag.strip()]
            account = Account.create({
                'code': vals['code'],
                'name': vals['name'],
                'account_type': vals['account_type'],
                'reconcile': bool(vals.get('reconcile')),
                'non_trade': bool(vals.get('non_trade')),
                'tag_ids': [Command.set(tags)],
                'company_ids': [Command.set(company.ids)],
            })
            created += 1
        env['ir.model.data']._update_xmlids([{
            'xml_id': ChartTemplate.company_xmlid(xmlid, company),
            'record': account,
            'noupdate': True,
        }])
    ChartTemplate._load_translations(companies=company)
    _logger.info("l10n_se: added %s K2 accounts to former K2 mini company %s", created, company.name)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute("SELECT to_regclass('l10n_se_k2_mini_companies')")
    k2_mini_ids = []
    if cr.fetchone()[0]:
        cr.execute("SELECT company_id FROM l10n_se_k2_mini_companies")
        k2_mini_ids = [row[0] for row in cr.fetchall()]
        cr.execute("DROP TABLE l10n_se_k2_mini_companies")

    # Accounts live on the root company; branches share them.
    for company in env['res.company'].browse(k2_mini_ids).filtered(lambda c: not c.parent_id):
        _add_missing_k2_accounts(env, company)

    # Update all Swedish companies with the current template data,
    # without creating taxes or fiscal positions the user may have removed.
    companies = env['res.company'].search([('chart_template', 'in', SE_TEMPLATES)], order="parent_path")
    for company in companies:
        env['account.chart.template'].try_loading(company.chart_template, company, force_create=False)
