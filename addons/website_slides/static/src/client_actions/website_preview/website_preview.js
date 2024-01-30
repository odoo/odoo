/** @odoo-module **/

import { patch } from 'web.utils';
import { WebsitePreview } from '@website/client_actions/website_preview/website_preview';

patch(WebsitePreview.prototype, 'website_slides_website_preview', {
    /**
     * @todo remove me in master, the cleaning of iframe is now done
     * globally in the website part
     * @override
     */
    _cleanIframeFallback() {
        return this._super(...arguments);
    }
});
