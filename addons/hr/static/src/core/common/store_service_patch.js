import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    setup() {
        super.setup();
        /** @type {{[key: number]: {id: number, user_id: number, hasCheckedUser: boolean}}} */
        this.employees = {};
    },
};

patch(Store.prototype, storeServicePatch);
