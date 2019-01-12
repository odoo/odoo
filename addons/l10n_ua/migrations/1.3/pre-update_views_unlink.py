from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, dict())

    w = env.ref('l10n_ua.view_ua_company_form', raise_if_not_found=False)
    if w:
        w.unlink()
    w = env.ref('l10n_ua.view_partner_form_l1', raise_if_not_found=False)
    if w:
        w.unlink()
    w = env.ref('l10n_ua.view_res_partner_filter_l', raise_if_not_found=False)
    if w:
        w.unlink()
    w = env.ref('l10n_ua.view_users_inherit_form', raise_if_not_found=False)
    if w:
        w.unlink()
