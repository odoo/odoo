import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResPartner extends mailModels.ResPartner {
    is_in_meeting = fields.Boolean({ compute: "_compute_is_in_meeting" });

    _compute_is_in_meeting() {
        for (const partner of this) {
            partner.is_in_meeting =
                this.env["calendar.attendee"].search([
                    ["partner_id", "=", partner.id],
                    ["state", "=", "accepted"],
                ]).length > 0;
        }
    }

    _store_im_status_fields(res) {
        super._store_im_status_fields(res);
        this._compute_is_in_meeting();
        res.attr("is_in_meeting");
    }
}
