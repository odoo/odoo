/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebsiteBuilder } from "@website/builder/website_builder";

patch(WebsiteBuilder.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.websiteEditService && typeof this.websiteEditService.clearRpcCache !== "function") {
            this.websiteEditService.clearRpcCache = () => {};
        }
    },
});
