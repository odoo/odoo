/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { WebsiteBuilderClientAction } from "./website_builder_action";

patch(WebsiteBuilderClientAction.prototype, {
    /**
     * @override
     */
    get testMode() {
        return true;
    },
});
