import { Store } from "@mail/core/common/store_service";
import { fields } from "@mail/model/misc";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    setup() {
        super.setup();
        this.websiteBuilder = fields.One("WebsiteBuilder", {
            compute: () => ({}),
        });
    },
};

patch(Store.prototype, storeServicePatch);
