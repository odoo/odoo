import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";
import { WelcomePage } from "@mail/discuss/core/public/welcome_page";
import { useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

DiscussClientAction.components = { ...DiscussClientAction.components, WelcomePage };
patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.publicState = useState({
            welcome: this.store.shouldDisplayWelcomeViewInitially,
        });
        if (this.store.isChannelTokenSecret) {
            // Change the URL to avoid leaking the invitation link.
            browser.history.replaceState(
                browser.history.state,
                null,
                `/discuss/channel/${this.store.discuss_public_thread_data.id}${browser.location.search}`
            );
        }
        browser.addEventListener("popstate", () => this.restoreDiscussThread(this.props));
    },
    getActiveId() {
        const currentURL = new URL(browser.location);
        if (!/\/discuss\/channel\/\d+$/.test(currentURL.pathname)) {
            return null;
        }
        return `discuss.channel_${currentURL.pathname.split("/")[3]}`;
    },
    async restoreDiscussThread() {
        await super.restoreDiscussThread(...arguments);
        this.publicState.welcome ||=
            this.store.discuss.thread?.default_display_mode === "video_full_screen";
    },
    closeWelcomePage() {
        this.publicState.welcome = false;
    },
});
