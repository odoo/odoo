import { DiscussClientAction } from "@mail/core/public_web/discuss_app/client_action";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        if (browser.location.pathname.startsWith("/my/conversations/")) {
            browser.history.replaceState(
                browser.history.state,
                null,
                `/discuss/channel/${this.store.discuss.thread.id}${browser.location.search}`
            );
        }
    },
});
