import { Store } from "@mail/core/common/store_plugin";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storePatch = {
    setup() {
        super.setup(...arguments);
        /** @type {boolean} */
        this.has_access_create_lead = undefined;
        /** @type {Array<import("models").DiscussChannel["channel_type"]>} */
        this.channel_types_with_lead_command = [];
    },
};
patch(Store.prototype, storePatch);
