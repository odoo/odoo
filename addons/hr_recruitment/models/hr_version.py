from odoo import api, fields, models


class HrVersion(models.Model):
    _inherit = "hr.version"

    date_version = fields.Date(groups="hr.group_hr_user,hr_recruitment.group_hr_recruitment_user")
    hr_responsible_id = fields.Many2one(groups="hr.group_hr_user,hr_recruitment.group_hr_recruitment_user")
    contract_template_payroll_summary = fields.Html(
        string="Contract Summary",
        compute="_compute_contract_template_payroll_summary",
        compute_sudo=True,
        groups="hr_recruitment.group_hr_recruitment_user"
    )

    @api.model
    def _exclude_fields_from_template_summary(self):
        return ['hr_responsible_id', 'job_id', 'department_id']

    @api.depends("contract_wage")
    def _compute_contract_template_payroll_summary(self):
        """
        Build an HTML summary dynamically from the whitelist fields.
        """
        whitelist = self.env['hr.version']._get_whitelist_fields_from_template()
        blacklist = self.env['hr.version']._exclude_fields_from_template_summary()
        for record in self:
            if record.employee_id or self.env.user.has_group("hr.group_hr_user"):
                record.contract_template_payroll_summary = False
                continue

            left_col, right_col = [], []
            for field_name in set(whitelist):
                if field_name in blacklist:
                    continue
                field = record._fields.get(field_name)
                if not field:
                    continue

                value = record[field_name]
                if not value:
                    continue

                label = field.string or field_name.replace("_", " ").title()

                if field.type == "monetary":
                    val_str = f"{value:.2f} {record.currency_id.symbol}"
                elif field.type == "many2one":
                    val_str = value.display_name
                elif field.type in ("date", "datetime"):
                    val_str = fields.Date.to_string(value)
                else:
                    val_str = str(value)

                target_col = right_col if field.type == "monetary" else left_col
                target_col.append(f"<tr><th>{label}</th><td>{val_str}</td></tr>")

            if left_col or right_col:
                record.contract_template_payroll_summary = f"""
                    <div>
                        <h4 style="margin:40px 0 10px;">Contract Summary</h4>
                        <div style="display:flex;gap:28px;">
                            <table style="flex:1;border-collapse:collapse;">{''.join(left_col)}</table>
                            <table style="flex:1;border-collapse:collapse;">{''.join(right_col)}</table>
                        </div>
                    </div>
                """
            else:
                record.contract_template_payroll_summary = False
