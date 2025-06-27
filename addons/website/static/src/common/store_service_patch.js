import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    setup() {
        super.setup();
        this.websiteBuilder = {
            on: false,
            editing: undefined,
            iframeWindow: undefined,
        };
    },
};

patch(Store.prototype, storeServicePatch);
