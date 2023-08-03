/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { WebsitePreview } from '@website/client_actions/website_preview/website_preview';

patch(WebsitePreview.prototype, {
    /**
     * @override
     */
    get testMode() {
        return true;
    }
});
