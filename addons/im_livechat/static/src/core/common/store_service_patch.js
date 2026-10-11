import { Store } from "@mail/core/common/store_plugin";
import { patchModel } from "@mail/model/export";

export const storePatch = patchModel(Store, {
    setup() {
        super.setup(...arguments);
        /** @type {boolean|undefined} */
        this.can_download_transcript = undefined;
        this.has_access_livechat = false;
    },
});
