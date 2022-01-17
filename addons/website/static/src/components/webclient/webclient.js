/** @odoo-module **/

import { WebClient } from '@web/webclient/webclient';
import { FullscreenIndication } from '@website/components/fullscreen_indication/fullscreen_indication';
import { patch } from 'web.utils';
import { useService } from '@web/core/utils/hooks';

const { useState, useExternalListener } = owl;

patch(WebClient.prototype, 'website_web_client', {
    setup() {
        this._super();
        this.website = useService('website');

        this.fullscreenState = useState({
            isFullscreen: false,
        });

        useExternalListener(document, 'keydown', (ev) => {
            // Toggle fullscreen mode when pressing escape.
            if (ev.keyCode === 27 && this.website.currentWebsite) {
                this.fullscreenState.isFullscreen = !this.fullscreenState.isFullscreen;
                document.body.classList.toggle('o_website_fullscreen', this.fullscreenState.isFullscreen);
            }
        });
    },
});

WebClient.components.FullscreenIndication = FullscreenIndication;
