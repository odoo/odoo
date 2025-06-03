import { ResPartner } from "@mail/core/common/res_partner_model";

import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    /** @type {number|undefined} */
    employeeId: undefined,
});
