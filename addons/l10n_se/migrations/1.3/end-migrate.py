# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import SUPERUSER_ID, Command, api

_logger = logging.getLogger(__name__)

SE_TEMPLATES = ('se_K1', 'se_K2', 'se_K3', 'se_K2_HB', 'se_K2_NPO')

# Account types corrected in the chart data: {template xmlid: (former type, correct type)}.
# Financial costs (impairments, interest, exchange losses) were typed as other income.
ACCOUNT_TYPE_FIXES = {
    **dict.fromkeys((
        'a8070', 'a8072', 'a8076', 'a8077',
        'a8170', 'a8171', 'a8172', 'a8173', 'a8174', 'a8176', 'a8177',
        'a8236', 'a8271', 'a8272', 'a8273', 'a8336', 'a8370',
        'a8400', 'a8410', 'a8411', 'a8412', 'a8413', 'a8415', 'a8417', 'a8419',
        'a8421', 'a8424', 'a8429', 'a8436', 'a8460', 'a8461', 'a8462', 'a8463', 'a8480', 'a8490',
    ), ('income_other', 'expense')),
    'a1260': ('asset_non_current', 'asset_fixed'),
}


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


def _fix_account_types(env, company):
    """Correct the account types of existing accounts.

    The chart data is loaded with noupdate, so existing accounts keep their type.
    Only accounts still having the former type are changed: a type the user
    has set themselves is left alone.
    """
    ChartTemplate = env['account.chart.template'].with_company(company)
    fixed = 0
    for xmlid, (former_type, account_type) in ACCOUNT_TYPE_FIXES.items():
        account = ChartTemplate.ref(xmlid, raise_if_not_found=False)
        if account and account.account_type == former_type:
            account.account_type = account_type
            fixed += 1
    if fixed:
        _logger.info("l10n_se: corrected the account type of %s accounts of company %s", fixed, company.name)


def _fix_tax_report_dashes(env):
    """Replace the en dashes in the names of the tax report lines.

    The names in the data are updated with the module, but the translated
    names keep the en dashes they were loaded with.
    """
    report = env.ref('l10n_se.tax_report', raise_if_not_found=False)
    if not report:
        return
    env.cr.execute("""
        UPDATE account_report_line
           SET name = (SELECT jsonb_object_agg(key, translate(value, '\u2013\u2014', '--'))
                         FROM jsonb_each_text(name))
         WHERE report_id = %s
           AND name::text ~ '[\u2013\u2014]'
    """, [report.id])
    env.invalidate_all()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute("SELECT to_regclass('l10n_se_k2_mini_companies')")
    k2_mini_ids = []
    if cr.fetchone()[0]:
        cr.execute("SELECT company_id FROM l10n_se_k2_mini_companies")
        k2_mini_ids = [row[0] for row in cr.fetchall()]
        cr.execute("DROP TABLE l10n_se_k2_mini_companies")

    _fix_tax_report_dashes(env)

    # Accounts live on the root company; branches share them.
    for company in env['res.company'].browse(k2_mini_ids).filtered(lambda c: not c.parent_id):
        _add_missing_k2_accounts(env, company)

    # Update all Swedish companies with the current template data,
    # without creating taxes or fiscal positions the user may have removed.
    companies = env['res.company'].search([('chart_template', 'in', SE_TEMPLATES)], order="parent_path")
    for company in companies.filtered(lambda c: not c.parent_id):
        _fix_account_types(env, company)
    for company in companies:
        env['account.chart.template'].try_loading(company.chart_template, company, force_create=False)
