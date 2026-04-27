/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { WebsitePreview } from '@website/client_actions/website_preview/website_preview';

patch(WebsitePreview.prototype, {
    /**
     * @override
     */
    _isTopWindowURL({ pathname }) {
        return (
            pathname && (
                pathname.startsWith('/knowledge/article/')
                || pathname.includes('/knowledge/home')
            )
        ) || super._isTopWindowURL(...arguments);
    }
});
