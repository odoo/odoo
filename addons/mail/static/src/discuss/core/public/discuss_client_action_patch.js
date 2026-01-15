import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";
import { WelcomePage } from "@mail/discuss/core/public/welcome_page";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

DiscussClientAction.components = { ...DiscussClientAction.components, WelcomePage };
patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.store.isChannelTokenSecret) {
            // Change the URL to avoid leaking the invitation link.
            browser.history.replaceState(
                browser.history.state,
                null,
                `/discuss/channel/${this.store.discuss.thread.id}${browser.location.search}`
            );
        }
        const url = new URL(browser.location.href);
        url.searchParams.delete("email_token");
        browser.history.replaceState(browser.history.state, null, url.toString());
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
        this.store.is_welcome_page_displayed ||=
            this.store.discuss.thread?.default_display_mode === "video_full_screen";
    },
    closeWelcomePage() {
        this.store.is_welcome_page_displayed = false;
    },
});
