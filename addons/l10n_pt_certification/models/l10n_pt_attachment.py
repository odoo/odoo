import base64

from odoo import fields, models


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
    original = fields.Boolean(string="Original Print")
    cancelled = fields.Boolean(string="Canceled")

    _sql_constraints = [('report_res_id_uniq', "unique(res_model, res_id, report_name)", "This report already exists for this record and model.")]

    def _get_l10n_pt_report_binary(self, doc, template, values):
        """
        The first time a PT document is printed, it should indicate it is an "Original". Reprinted documents must
        mention "2ª Via". If there are any changes in the data of partners or of the company in between the original
        print and the reprint, the original data must be kept in the document. To do so, the binary of the original
        prints are saved in 'l10n.pt.attachment'. A reprint retrieves that binary, changes only the print version, and
        saves the binary of this reprint. Subsequent reprints retrieve the reprint binary.
        """
        attachment = self.search([
            ('res_id', '=', doc.id),
            ('res_model', '=', values['doc_model']),
            ('report_name', '=', template),
            ('company_id', '=', doc.company_id.id),
        ])
        # Original print (first time this report is generated for this record)
        if not attachment:
            attachment = self.create({
                'res_id': doc.id,
                'res_model': values['doc_model'],
                'report_name': template,
                'company_id': doc.company_id.id,
                'report_binary': base64.b64encode(
                    self.env['ir.actions.report'].with_context(ignore_pt_versioning=True)._render_template(template, values)
                ),
                'cancelled': doc.state == 'cancel',
                'original': True,
            })
        # Record has been cancelled, which is treated as a new report with an Original and Reprint version
        elif attachment and not attachment.cancelled and doc.state == 'cancel':
            attachment.write({
                'report_binary': base64.b64encode(
                    self.env['ir.actions.report'].with_context(ignore_pt_versioning=True)._render_template(template, values)
                ),
                'cancelled': True,
                'original': True,
            })
        # First reprint, ensures data is the same by retrieving the original binary and update reprint version
        elif attachment and attachment.original:
            replaced_report_str = base64.b64decode(attachment.report_binary).decode('utf-8').replace(
                '<span id="l10n_pt_print_version">Original',
                '<span id="l10n_pt_print_version">2ª Via',
            )
            attachment.write({
                'report_binary': base64.b64encode(replaced_report_str.encode('utf-8')),
                'original': False,
            })
        return attachment.report_binary
