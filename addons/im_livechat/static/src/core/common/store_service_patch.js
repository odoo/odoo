import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storePatch = {
    setup() {
        super.setup(...arguments);
        /** @type {boolean|undefined} */
        this.can_download_transcript = undefined;
        this.has_access_livechat = false;
    },
};
patch(Store.prototype, storePatch);
