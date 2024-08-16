import { Store } from "@mail/model/store";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    get onlineMemberStatuses() {
        return super.onlineMemberStatuses + ["leave_online", "leave_away"];
    },
};

patch(Store.prototype, storeServicePatch);
