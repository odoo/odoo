# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountTaxUpdate(models.TransientModel):
    """
    This class manages the update of account.tax from account.tax.template.
    """
    _name = "account.tax.update"
    _description = "Update taxes from tax templates"

    def update_taxes(self):
        company = self.env.company
        template_to_tax = self._get_template_to_tax_xmlid_mapping(company)
        templates = self.env['account.tax.template'].search([("chart_template_id", "=", company.chart_template_id.id)])
        questionable_taxes = []
        for template in templates:
            if template.id not in template_to_tax:
                # if the tax template is not present in the mapping, it means the corresponding tax was removed from
                # the db, or no xmlid exists for the tax (in the case of old db or new tax)
                # -> create a new tax
                self._create_tax_from_template(company, template)
            else:
                # there is a corresponding xmlid in taxes, let's check if it's exactly the same taxe
                tax = self.env["account.tax"].browse(template_to_tax[template.id])
                if self._tax_and_template_compare(template, tax):
                    # -> update the tax : we only updates tax tags
                    tax_rep_lines = tax.invoice_repartition_line_ids + tax.refund_repartition_line_ids
                    template_rep_lines = template.invoice_repartition_line_ids + template.refund_repartition_line_ids
                    for tax_line, template_line in zip(tax_rep_lines, template_rep_lines):
                        tags_to_add = template_line._get_tags_to_add()
                        tags_to_unlink = tax_line.tag_ids
                        if tags_to_add != tags_to_unlink:
                            tax_line.write({"tag_ids": [(6, 0, tags_to_add.ids)]})
                            self._tags_cleanup(tags_to_unlink)
                else:
                    # it's not exactly the same tax
                    # -> create new tax + drop old tax xmlid
                    self._create_tax_from_template(company, template, old_tax=tax)
                    questionable_taxes.append(tax)
        # we send a message to accountant managers to warn them some taxes might be unrelevant now
        if questionable_taxes:
            self._send_message_to_accountants(questionable_taxes)

    def _create_tax_from_template(self, company, template, old_tax=None):
        """
        Create a new tax from template with template xmlid, if there was already an old tax with that xmlid we
        remove the xmlid from it but don't modify anything else.
        """
        def _remove_xml_id(xml_id):
            module, name = xml_id.split(".", 1)
            self.env['ir.model.data'].search([('module', '=', module), ('name', '=', name)]).unlink()

        template_vals = template._get_tax_vals_complete(company)
        chart_template = self.env["account.chart.template"].with_context(default_company_id=company.id)
        if old_tax:
            xml_id = old_tax.get_xml_id().get(old_tax.id)
            if xml_id:
                _remove_xml_id(xml_id)
        chart_template.create_record_with_xmlid(company, template, "account.tax", template_vals)

    def _get_template_to_tax_xmlid_mapping(self, company):
        """
        This function uses ir_model_data to return a mapping between the tax templates and the taxes, using their xmlid
        :returns: {
            account.tax.template.id: account.tax.id
            }
        """
        self.env['ir.model.data'].flush()
        self.env.cr.execute(
            """
            SELECT template.res_id AS template_res_id,
                   tax.res_id AS tax_res_id
            FROM ir_model_data tax
            JOIN ir_model_data template
            ON template.name = substr(tax.name, strpos(tax.name, '_') + 1)
            WHERE tax.model = 'account.tax'
            AND tax.name LIKE %s
            -- tax.name is of the form: {company_id}_{account.tax.template.name}
            """,
            [r"%s\_%%" % company.id],
        )
        tuples = self.env.cr.fetchall()
        template_to_tax = dict(tuples)
        return template_to_tax

    def _tax_and_template_compare(self, template, tax):
        """
        This function compares account.tax and account.tax.template repartition lines.
        A tax is considered the same as the template if they have the same:
            - amount_type
            - amount
            - repartition lines percentages in the same order
        """
        if tax.amount_type != template.amount_type or tax.amount != template.amount \
                or len(tax.invoice_repartition_line_ids) != len(template.invoice_repartition_line_ids) \
                or len(tax.refund_repartition_line_ids) != len(template.refund_repartition_line_ids):
            return False

        tax_rep_lines = tax.invoice_repartition_line_ids + tax.refund_repartition_line_ids
        template_rep_lines = template.invoice_repartition_line_ids + template.refund_repartition_line_ids
        for rep_line_tax, rep_line_template in zip(tax_rep_lines, template_rep_lines):
            if rep_line_tax.factor_percent != rep_line_template.factor_percent:
                return False
        return True

    def _tags_cleanup(self, tags):
        """
        Checks if the tags are still used by move.line or repartition.line.
        If it's still referenced, we archieve it, else we delete it.
        """
        for tag in tags:
            aml_using_tags = self.env['account.move.line'].sudo().search([('tax_tag_ids', 'in', tag.id)])
            tax_using_tags = self.env['account.tax.repartition.line'].sudo().search([('tag_ids', 'in', tag.id)])
            if aml_using_tags or tax_using_tags:
                tag.active = False
            else:
                tag.unlink()

    def _send_message_to_accountants(self, taxes_to_report):
        # message = self.env['mail.message'].create({
        #     'subject': _('Invitation to follow %(document_model)s: %(document_name)s', document_model=model_name,
        #                  document_name=document.display_name),
        #     'body': wizard.message,
        #     'record_name': document.display_name,
        #     'email_from': email_from,
        #     'reply_to': email_from,
        #     'model': wizard.res_model,
        #     'res_id': wizard.res_id,
        #     'no_auto_thread': True,
        # })
        pass
