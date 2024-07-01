/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { browser } from "@web/core/browser/browser";
import { useState } from "@odoo/owl";

patch(WebClient.prototype, "web", {
    /**
     * Overrides setup() method of Webclient to prevent
     * the flikering of the navbar during website
     * configurator
     *
     * @override
     */
    setup() {
        this._super(...arguments);
        let isWebsiteConfiguration = false;
        if(browser.sessionStorage && (this.currentAction = browser.sessionStorage.getItem("current_action"))){
            isWebsiteConfiguration = this.currentAction.includes("action_website_configuration");
        }
        this.state = useState({
            fullscreen: isWebsiteConfiguration
        });
    }
});
