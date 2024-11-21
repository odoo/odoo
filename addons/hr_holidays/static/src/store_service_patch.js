import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    get onlineMemberStatuses() {
        return super.onlineMemberStatuses + ["leave_online", "leave_away"];
    },
};

patch(Store.prototype, storeServicePatch);
