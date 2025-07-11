/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";

import { Chatter } from "@mail/core/web/chatter";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        const showTracking = browser.localStorage.getItem(
            'muk_web_chatter.tracking'
        );
        this.state.showTracking = (
            showTracking != null ? JSON.parse(showTracking) : true
        );
    },
    onClickTrackingToggle() {
        const showTracking = !this.state.showTracking;
        browser.localStorage.setItem(
            'muk_web_chatter.tracking', showTracking
        );
        this.state.showTracking = showTracking;
    },
});


