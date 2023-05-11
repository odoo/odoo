/** @odoo-module **/

import { patch } from 'web.utils';
import { WebsitePreview } from '@website/client_actions/website_preview/website_preview';

patch(WebsitePreview.prototype, 'website_slides_website_preview', {
    /**
     * @override
     */
    _cleanIframeFallback() {
        // Remove autoplay in all youtube videos urls so videos are not playing
        // in the background
        const playersEl = this.iframefallback.el.contentDocument.querySelectorAll('[id^=youtube-player]');
        for (const playerEl of playersEl) {
            const url = new URL(playerEl.src);
            url.searchParams.delete('autoplay');
            playerEl.src = url.toString();
        }
        return this._super(...arguments);
    }
});
