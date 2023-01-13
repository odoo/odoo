# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class FgPosConfig(models.Model):
    _inherit = "pos.config"

    def use_coupon_code(self, code, creation_date, partner_id, reserved_program_ids):
        # if not partner_id:
        #     return {
        #         "successful": False,
        #         "payload": {
        #             "error_message": _("This order not available customer, first set custom.")
        #         },
        #     }
        coupon_to_check = self.env["coupon.coupon"].search(
            [("code", "=", code), ("program_id", "in", self.program_ids.ids)]
        )
        # If not unique, we only check the first coupon.
        coupon_to_check = coupon_to_check[:1]
        if not coupon_to_check:
            return {
                "successful": False,
                "payload": {
                    "error_message": _("This coupon is invalid (%s).") % (code)
                },
            }
        message = coupon_to_check._check_coupon_code(
            fields.Date.from_string(creation_date[:11]),
            partner_id,
            reserved_program_ids=reserved_program_ids,
        )
        error_message = message.get("error", False)
        if error_message:
            return {
                "successful": False,
                "payload": {"error_message": error_message},
            }
        if coupon_to_check.program_id and coupon_to_check.program_id.fg_discount_type:
            partner_id = self.env['res.partner'].browse(int(partner_id))
            if coupon_to_check.program_id.fg_discount_type == 'is_pwd_discount':
                if not partner_id.x_pwd_id:
                    return {
                        "successful": False,
                        "payload": {
                            "error_message": _("PWD ID not set on customer (%s), first set custom.") % (partner_id.name)
                        },
                    }
            if coupon_to_check.program_id.fg_discount_type == 'is_senior_discount':
                if not partner_id.x_senior_id:
                    return {
                        "successful": False,
                        "payload": {
                            "error_message": _("Senior ID not set on customer (%s), first set custom.") % (partner_id.name)
                        },
                    }
        coupon_to_check.write({"state": "used"})
        return {
            "successful": True,
            "payload": {
                "program_id": coupon_to_check.program_id.id,
                "coupon_id": coupon_to_check.id,
            },
        }

