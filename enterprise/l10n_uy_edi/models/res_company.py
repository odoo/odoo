from odoo import _, api, fields, models

from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    # EDI Environment fields

    l10n_uy_edi_ucfe_env = fields.Selection(
        selection=[
            ("production", "Production"),
            ("testing", "Testing"),
            ("demo", "Demo"),
        ],
        string="EDI environment",
        default="demo",
        help="UCFE environment to generate EDI invoices, if Demo is selected it will not connect to a webservice and"
        " it will do a dummy validation only in Odoo of the CFE")
    l10n_uy_edi_ucfe_password = fields.Char(
        "UCFE Provider WS Password",
        groups="base.group_system",
        help="This password is used exclusively for accessing UCFE webservices, enabling communication and data"
        " exchange between Odoo and UCFE. It is distinct from the password used to log in to UCFE's portal.")
    l10n_uy_edi_ucfe_commerce_code = fields.Char("UCFE Provider Commerce code", groups="base.group_system")
    l10n_uy_edi_ucfe_terminal_code = fields.Char("UCFE Provider Terminal code", groups="base.group_system")

    # DGI

    l10n_uy_edi_branch_code = fields.Char(
        "DGI Main-House or Branch Code",
        default=1,
        size=4,
        help=" This value is part of the XML when creating CFE. If not set properly all the CFEs will be rejected"
        "\nTo get this number you can follow next steps:"
        "\n1. Go to 'Servicios en linea DGI' page."
        "\n2. Select option 'Registro único tributario -> Consulta de datos' (menu link at the right side)."
        "\n3. Select option 'Consulta de Datos Registrales -> Consulta de Datos de Entidades'."
        "\n4. Open the generated PDF. Get the number on section 'Domicilio Fiscal -> Número de Local'")

    l10n_uy_edi_addenda_ids = fields.One2many("l10n_uy_edi.addenda", "company_id", "CFE Addendas")

    # Compute methods

    @api.constrains("l10n_uy_edi_branch_code")
    def _l10n_uy_edi_check_valid_branch_code(self):
        for company in self:
            if not company.l10n_uy_edi_branch_code.isdigit():
                raise ValidationError(_("Branch Code should be only numbers"))

    def _l10n_uy_edi_validate_company_data(self):
        self.ensure_one()
        errors = []
        if not self.vat:
            errors.append(_("Set your company RUT"))
        else:
            # Validate if the VAT is a valid RUT:  we use _run_vat_test() instead of check_vat() because we do not want
            # raise a ValidationError, also we are sure that the company identification type is RUT
            partner = self.partner_id
            if (
                partner.vat
                and partner.l10n_latam_identification_type_id.l10n_uy_dgi_code == "2"
                and partner._run_vat_test(partner.vat, partner.country_id, partner.is_company) != "uy"
            ):
                errors.append(_("Set a valid RUT in your company"))
        if not self.l10n_uy_edi_branch_code:
            errors.append(_("Set your company House Code"))
        if not self.state_id:
            errors.append(_("Set your company state"))
        if not self.city:
            errors.append(_("Set your company city"))
        if not self.street:
            errors.append(_("Set your company address (street and/or street2)"))

        return errors
