import { Store } from "@mail/core/common/store_service";
import { Record } from "@mail/model/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storePatch = {
    setup() {
        super.setup(...arguments);
        this.self_employee = Record.one("hr.employee");
    },
};
patch(Store.prototype, storePatch);
