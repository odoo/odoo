from odoo import fields, models


class UoM(models.Model):
    _inherit = "uom.uom"

    l10n_pk_edi_uom_code = fields.Selection(
        selection=[
            ('3', 'MT'),
            ('4', 'Bill of lading'),
            ('5', 'SET'),
            ('6', 'KWH'),
            ('8', '40KG'),
            ('9', 'Liter'),
            ('11', 'SqY'),
            ('12', 'Bag'),
            ('13', 'KG'),
            ('46', 'MMBTU'),
            ('48', 'Meter'),
            ('50', 'Pcs'),
            ('53', 'Carat'),
            ('55', 'Cubic Metre'),
            ('57', 'Dozen'),
            ('59', 'Gram'),
            ('61', 'Gallon'),
            ('63', 'Kilogram'),
            ('65', 'Pound'),
            ('67', 'Timber Logs'),
            ('69', 'Numbers, pieces, units'),
            ('71', 'Packs'),
            ('73', 'Pair'),
            ('75', 'Square Foot'),
            ('77', 'Square Metre'),
            ('79', 'Thousand Unit'),
            ('81', 'Mega Watt'),
            ('83', 'Foot'),
            ('85', 'Barrels'),
            ('87', 'NO'),
            ('88', 'Others'),
            ('96', '1000 kWh'),
        ],
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
