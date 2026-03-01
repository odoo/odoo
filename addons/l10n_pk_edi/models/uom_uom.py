from odoo import fields, models

from odoo.addons.l10n_pk_edi.data.l10n_pk_edi_data import UOM_CODES


class UoM(models.Model):
    _inherit = "uom.uom"

    l10n_pk_edi_uom_code = fields.Selection(
        selection=UOM_CODES,
        string="FBR UoM Code",
        help="Unit of Measure(UoM) is a standard unit to express quantities of stock or products.",
    )

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _group_by_error_code(self):
        self.ensure_one()
        if not self.l10n_pk_edi_uom_code:
            return (
                ("message", self.env._("UOM(s) must have a FBR UoM Code.")),
                ("error_code", "uom_fbr_code_missing"),
                ("level", "danger"),
            )

        return False

    def _l10n_pk_edi_export_check(self):
        """Validate Invoice/Credit-Note for E-Invoicing compliance."""
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(
            lambda m: m._group_by_error_code()
        ).items():
            if not error_tuple:
                continue
            temp_dict = dict(error_tuple)
            alert_vals.update(
                {
                    temp_dict["error_code"]: {
                        "message": temp_dict["message"],
                        "level": temp_dict["level"],
                        "action": invalid_records._get_records_action(),
                        "action_text": self.env._("View UOM(s)"),
                    },
                },
            )

        return alert_vals
