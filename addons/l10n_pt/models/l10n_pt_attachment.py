from odoo import fields, models


class L10nPtAttachment(models.Model):
    _name = 'l10n.pt.attachment'
    _description = "Report Binaries for Portugal"
    _check_company_auto = True

    res_model = fields.Char(string="Model", required=True)
    res_id = fields.Many2oneReference(string="Record id", model_field='res_model', required=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    report_name = fields.Char(string="Report", required=True)
    original_binary = fields.Binary(string="Original File")
    reprint_binary = fields.Binary(string="Reprinted File")

    _sql_constraints = [('report_res_id_uniq', "unique(res_model, res_id, report_name)", "This report already exists for this record and model.")]
