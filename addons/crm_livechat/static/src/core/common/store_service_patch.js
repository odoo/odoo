import { Store } from "@mail/core/common/store_plugin";
import { patchModel } from "@mail/model/export";

export const storePatch = patchModel(Store, {
    setup() {
        super.setup(...arguments);
        this.has_access_create_lead = false;
    },
});
