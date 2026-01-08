import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";

import { Chatter } from "@mail/chatter/web_portal/chatter";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        const showNotificationMessages = browser.localStorage.getItem(
            'muk_web_chatter.notifications'
        );
        this.state.showNotificationMessages = (
            showNotificationMessages != null ? 
            JSON.parse(showNotificationMessages) : true
        );
    },
    onClickNotificationsToggle() {
        const showNotificationMessages = !this.state.showNotificationMessages;
        browser.localStorage.setItem(
            'muk_web_chatter.notifications', showNotificationMessages
        );
        this.state.showNotificationMessages = showNotificationMessages;
    },
});


