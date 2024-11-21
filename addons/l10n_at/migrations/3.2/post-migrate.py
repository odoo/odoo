# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID, Command


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Tag PCVIII is no longer referenced in the Balance Sheet: users should use PCVIII3 instead.
    if (
        (tag_pcviii := env.ref('l10n_at.account_tag_l10n_at_PCVIII', raise_if_not_found=False))
        and (tag_pcviii3 := env.ref('l10n_at.account_tag_l10n_at_PCVIII3', raise_if_not_found=False))
    ):
        env['account.account'].search([('tag_ids', '=', tag_pcviii.id)]).write({
            'tag_ids': [Command.unlink(tag_pcviii.id), Command.link(tag_pcviii3.id)],
        })
