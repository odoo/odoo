import base64

from psycopg2.errors import UniqueViolation

from odoo import fields, models
from odoo.exceptions import ConcurrencyError


PRINT_VERSION_ORIGINAL = '<span id="l10n_pt_print_version">Original</span>'
PRINT_VERSION_REPRINT = '<span id="l10n_pt_print_version">2ª Via</span>'
CANCELLED_MARK = '<span id="l10n_pt_cancelled" class="text-danger"> - Documento Cancelado</span>'


class L10nPtAttachment(models.Model):
    """
    Stores the report binaries for all Portuguese documents, allowing reprints to utilize the same binary.
    """
    _name = 'l10n.pt.attachment'
    _description = "Report Binaries for Portugal"
    _check_company_auto = True

    res_model = fields.Char(string="Model", required=True)
    res_id = fields.Many2oneReference(string="Record id", model_field='res_model', required=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    report_name = fields.Char(string="Report", required=True)
    report_binary = fields.Binary(string="File Binary", required=True)

    _report_res_id_uniq = models.Constraint(
        'unique(res_model, res_id, report_name)',
        "This report already exists for this record and model.",
    )

    def _get_l10n_pt_report_html(self, doc, template, values):
        """
        The report of a PT document, as it was first printed.

        A reprint must keep the content of the original, even if the partner's or the company's data
        changed since, and say it is not the original (Despacho 8632/2014 2.2.15). So the first print
        of each report of a document is stored, and every later print of that report serves it
        again. The print version is decided per document, not per report: only the document's first
        print, whatever the report or the channel (the PoS prints the receipt of its invoices), is
        the "Original"; every other print is a "2ª Via", marked cancelled once the document is
        (FAQ 2764). Only a print counts (``l10n_pt_print`` in the context, see
        ``_pre_render_qweb_pdf``): an HTML preview stores nothing and leaves the version alone.
        """
        is_print = self.env.context.get('l10n_pt_print')
        # Look the report up by exactly the key `_report_res_id_uniq` enforces.
        attachment = self.search([
            ('res_id', '=', doc.id),
            ('res_model', '=', values['doc_model']),
            ('report_name', '=', template),
        ])
        if attachment:
            html = base64.b64decode(attachment.report_binary).decode()
        else:
            html = self.env['ir.actions.report'].with_context(ignore_pt_versioning=True)._render_template(template, values).decode()
            if is_print:
                try:
                    with self.env.cr.savepoint():
                        self.create({
                            'res_id': doc.id,
                            'res_model': values['doc_model'],
                            'report_name': template,
                            'company_id': doc.company_id.id,
                            'report_binary': base64.b64encode(html.encode()),
                        })
                except UniqueViolation as e:
                    # A concurrent transaction printed the original first; this transaction's snapshot
                    # predates its commit, so the search above could not see it. Retrying the request
                    # sees it and renders a reprint, as if both prints had run one after the other.
                    raise ConcurrencyError(
                        f"Concurrent first print of {template} for {values['doc_model']}({doc.id})"
                    ) from e
        # The stored report always reads "Original": it is relabelled here, for this print.
        if doc._l10n_pt_is_cancelled() and 'id="l10n_pt_cancelled"' not in html:
            html = html.replace(PRINT_VERSION_ORIGINAL, PRINT_VERSION_ORIGINAL + CANCELLED_MARK)
        if doc.l10n_pt_print_version:
            html = html.replace(PRINT_VERSION_ORIGINAL, PRINT_VERSION_REPRINT)
        elif is_print and (labels := doc._l10n_pt_get_first_print_copy_labels()) != ['Original']:
            # A first print made of several copies, e.g. the three exemplars of a transport document.
            html = ''.join(
                html.replace(PRINT_VERSION_ORIGINAL, f'<span id="l10n_pt_print_version">{label}</span>')
                for label in labels
            )
        if is_print:
            doc.update_l10n_pt_print_version()
        return html.encode()
