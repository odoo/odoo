import { ResUsers } from "@mail/core/common/model_definitions";
import { patch } from "@web/core/utils/patch";

patch(ResUsers.prototype, {
    /** @type {string} */
    get email() {
        return this.partner_id?.email;
    },

    /** @type {string} */
    get name() {
        return this.partner_id?.name;
    },

    /** @type {string} */
    get phone() {
        return this.partner_id?.phone;
    },
});

export { ResUsers };
