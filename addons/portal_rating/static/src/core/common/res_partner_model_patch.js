import { ResPartner } from "@mail/core/common/res_partner_model";

import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {boolean|undefined} can publish a comment on a rating */
        this.is_user_publisher = undefined;
    },
});
