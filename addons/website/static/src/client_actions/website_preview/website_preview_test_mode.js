/** @odoo-module **/
import { patch } from 'web.utils';
import { WebsitePreview } from '@website/client_actions/website_preview/website_preview';

patch(WebsitePreview.prototype, 'website_preview_test_mode', {
    /**
     * @override
     */
    get testMode() {
        return true;
    }
});
