import { DiscussClientAction } from "@mail/core/public_web/discuss_app/client_action";
import { WelcomePage } from "@mail/discuss/core/public/welcome_page";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

DiscussClientAction.components = { ...DiscussClientAction.components, WelcomePage };
patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        const url = new URL(browser.location.href);
        url.searchParams.delete("email_token");
        browser.history.replaceState(browser.history.state, null, url.toString());
        browser.addEventListener("popstate", () => this.restoreDiscussThread(this.props));
    },
    /** @override */
    getActiveId() {
        const { pathname } = new URL(browser.location);
        const channelId =
            pathname.match(/^\/discuss\/channel\/(\d+)$/)?.[1] ??
            pathname.match(/^\/chat\/(\d+)\/[^/]+$/)?.[1];
        return channelId ? `discuss.channel_${channelId}` : null;
    },
    async restoreDiscussThread() {
        await super.restoreDiscussThread(...arguments);
        this.store.is_welcome_page_displayed ||=
            this.store.discuss.thread?.channel.default_display_mode === "video_full_screen";
        const channel = this.store.discuss.thread?.channel;
        if (!channel) {
            return;
        }
        if (this.store.is_welcome_page_displayed && channel.invitationLink) {
            browser.history.replaceState(
                browser.history.state,
                null,
                `${new URL(channel.invitationLink).pathname}${browser.location.search}`
            );
        } else if (this.store.isChannelTokenSecret) {
            browser.history.replaceState(
                browser.history.state,
                null,
                `/discuss/channel/${channel.id}${browser.location.search}`
            );
        }
    },
    closeWelcomePage() {
        this.store.is_welcome_page_displayed = false;
    },
});
