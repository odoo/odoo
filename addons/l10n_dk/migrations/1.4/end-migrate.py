from odoo import SUPERUSER_ID, Command, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # All accounts that are removed in this version.
    deprecated_accounts = (
        'dk_coa_1350', 'dk_coa_1830', 'dk_coa_1970', 'dk_coa_2250', 'dk_coa_2270', 'dk_coa_2300', 'dk_coa_2330',
        'dk_coa_2420', 'dk_coa_2520', 'dk_coa_2630', 'dk_coa_2640', 'dk_coa_2850', 'dk_coa_2940', 'dk_coa_2950',
        'dk_coa_2960', 'dk_coa_2965', 'dk_coa_2968', 'dk_coa_2970', 'dk_coa_2980', 'dk_coa_3180', 'dk_coa_3620',
        'dk_coa_3680', 'dk_coa_5040', 'dk_coa_5060', 'dk_coa_5080', 'dk_coa_5270', 'dk_coa_5680', 'dk_coa_5840',
        'dk_coa_5850', 'dk_coa_5880', 'dk_coa_6060', 'dk_coa_6220', 'dk_coa_6230', 'dk_coa_6250', 'dk_coa_6270',
        'dk_coa_6290', 'dk_coa_6300', 'dk_coa_6580', 'dk_coa_7020', 'dk_coa_7160', 'dk_coa_7170', 'dk_coa_7190',
        'dk_coa_7520', 'dk_coa_7630', 'dk_coa_7630',
    )
    # All tags (right-hand side) that should be replaced with new tags (left-hand side).
    new_tag_name_to_old_tag_names = {
        'account_tag_1745': ('account_tag_2250',),
        'account_tag_1760': ('account_tag_1830',),
        'account_tag_1801': ('account_tag_2270',),
        'account_tag_1910': ('account_tag_1890',),
        'account_tag_2375': ('account_tag_1970',),
        'account_tag_2430': ('account_tag_2420',),
        'account_tag_2810': ('account_tag_2300',),
        'account_tag_2845': ('account_tag_2850',),
        'account_tag_2885': ('account_tag_2968',),
        'account_tag_2887': ('account_tag_2960', 'account_tag_2965'),
        'account_tag_2888': ('account_tag_2640',),
        'account_tag_2895': ('account_tag_2330', 'account_tag_2630', 'account_tag_2970'),
        'account_tag_2896': ('account_tag_2520',),
        'account_tag_2898': ('account_tag_2950',),
        'account_tag_2910': ('account_tag_2940',),
        'account_tag_2946': ('account_tag_2980',),
        'account_tag_3170': ('account_tag_3180',),
        'account_tag_3185': ('account_tag_1350', 'account_tag_3680'),
        'account_tag_3530': ('account_tag_1540',),
        'account_tag_3596': ('account_tag_3620',),
        'account_tag_5042': ('account_tag_5080',),
        'account_tag_5076': ('account_tag_5040',),
        'account_tag_5077': ('account_tag_5060',),
        'account_tag_5111': ('account_tag_5120',),
        'account_tag_5112': ('account_tag_5130',),
        'account_tag_5281': ('account_tag_5270',),
        'account_tag_5676': ('account_tag_5680',),
        'account_tag_5836': ('account_tag_5840',),
        'account_tag_5837': ('account_tag_5850',),
        'account_tag_5844': ('account_tag_5880',),
        'account_tag_6061': ('account_tag_6060',),
        'account_tag_6240': ('account_tag_6270',),
        'account_tag_6252': ('account_tag_6220',),
        'account_tag_6256': ('account_tag_6230',),
        'account_tag_6282': ('account_tag_6250',),
        'account_tag_6305': ('account_tag_6290',),
        'account_tag_6315': ('account_tag_6300',),
        'account_tag_6470': ('account_tag_6471',),
        'account_tag_6480': ('account_tag_6481', 'account_tag_6482', 'account_tag_6483', 'account_tag_6484'),
        'account_tag_6800': ('account_tag_6580',),
        'account_tag_6985': ('account_tag_7020',),
        'account_tag_7175': ('account_tag_7160',),
        'account_tag_7185': ('account_tag_7170',),
        'account_tag_7195': ('account_tag_7190',),
        'account_tag_7345': ('account_tag_7630',),
        'account_tag_7535': ('account_tag_7520',),
    }
    all_tag_names = [tag_name for old_tag_names in new_tag_name_to_old_tag_names.values() for tag_name in old_tag_names]
    all_tag_names += list(new_tag_name_to_old_tag_names.keys())
    all_tags_domain = [
        ('model', '=', 'account.account.tag'),
        ('module', '=', 'l10n_dk'),
        ('name', 'in', all_tag_names),
    ]
    tag_to_id = dict(env['ir.model.data']._read_group(all_tags_domain, groupby=['name', 'res_id']))

    dk_companies = env['res.company'].search([('chart_template', '=', 'dk')], order='parent_path')

    # Add the new tags while removing the old tags, otherwise the search will not find the accounts to update.
    for new_tag_name, old_tag_names in new_tag_name_to_old_tag_names.items():
        old_tag_ids = [tag_to_id[old_tag_name] for old_tag_name in old_tag_names if old_tag_name in tag_to_id]
        new_tag_id = tag_to_id.get(new_tag_name)
        if not old_tag_ids or not new_tag_id:
            continue
        env['account.account'].with_context(active_test=False).search([
            ('company_ids', 'in', dk_companies.ids),
            ('tag_ids', 'in', old_tag_ids),
        ]).tag_ids = [
            Command.link(new_tag_id),
            *[Command.unlink(old_tag_id) for old_tag_id in old_tag_ids],
        ]

    # Remove the existing account groups.
    env['account.group'].search([('company_id', 'in', dk_companies.ids)]).unlink()

    deprecated_account_names = [f'{company.id}_{account}' for account in deprecated_accounts for company in dk_companies]
    deprecated_account_ids = set(env['ir.model.data'].search([
        ('model', '=', 'account.account'),
        ('module', '=', 'account'),
        ('name', 'in', deprecated_account_names),
    ]).mapped('res_id'))

    for account in env['account.account'].with_context(active_test=False).search([('company_ids', 'in', dk_companies.ids)]):
        # Adapt existing codes to use 6 digits.
        for company in dk_companies:
            account_comp = account.with_company(company)
            if account_comp.code and len(account_comp.code) < 6:
                account_comp.code = account_comp.code.ljust(6, '0')
        # Deprecate removed accounts.
        if account.id in deprecated_account_ids:
            account.deprecated = True

    for company in dk_companies:
        # Reload the accounts and tags that we updated.
        env['account.chart.template'].try_loading('dk', company)
