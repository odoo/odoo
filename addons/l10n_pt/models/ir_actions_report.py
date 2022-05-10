from markupsafe import Markup
from odoo import models, _


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _prepare_html(self, html, report_model):
        bodies, html_ids, header, footer, specific_paperformat_args = super()._prepare_html(html, report_model)
        if report_model != "account.move" or self.env.company.account_fiscal_country_id.code != "PT":
            return bodies, html_ids, header, footer, specific_paperformat_args
        records = self.env[report_model].browse(html_ids)
        new_bodies = []
        for i, record in enumerate(records):
            if not record.l10n_pt_original_html_body:
                new_bodies.append(bodies[i])
                find = Markup(f"""<span id="original_duplicate" class="text-muted">{_('Original')}</span>""")
                replace = Markup(f"""<span id="original_duplicate" class="text-muted">{_('Duplicate')}</span>""")
                record.l10n_pt_original_html_body = bodies[i].replace(find, replace)
            else:
                new_bodies.append(Markup(record.l10n_pt_original_html_body))
        return new_bodies, html_ids, header, footer, specific_paperformat_args
