import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/model/misc";
import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    setup() {
        super.setup(...arguments);
        this.is_in_meeting = fields.Attr(false);
    },
});
