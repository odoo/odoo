/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebsiteBuilder } from "@website/builder/website_builder";
import { WebsiteBuilderClientAction } from "@website/client_actions/website_preview/website_builder_action";

patch(WebsiteBuilder.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.websiteEditService && typeof this.websiteEditService.clearRpcCache !== "function") {
            this.websiteEditService.clearRpcCache = () => {};
        }
    },
});

patch(WebsiteBuilderClientAction.prototype, {
    onIframeLoad(ev) {
        const iframe = this.websiteContent?.el;
        if (!iframe?.contentDocument?.body) {
            if (iframe && !iframe.dataset.themeSemsaBodyRetry) {
                iframe.dataset.themeSemsaBodyRetry = "1";
                window.setTimeout(() => {
                    delete iframe.dataset.themeSemsaBodyRetry;
                    if (iframe.contentDocument?.body) {
                        iframe.dispatchEvent(new Event("load"));
                    }
                }, 75);
            }
            return;
        }
        return super.onIframeLoad(ev);
    },
});
