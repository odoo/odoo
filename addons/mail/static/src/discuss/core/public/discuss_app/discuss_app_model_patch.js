import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import { browser } from "@web/core/browser/browser";

import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    /**
     * The public page has no backend router/action stack, so `activeId` can't be
     * persisted as a `router.pushState` query param the way the backend does (it
     * would rewrite the path to `/odoo`). Instead, a channel selection is reflected
     * in the URL path (e.g. `/discuss/channel/10`), while anything else (e.g. a
     * sidebar tab) has no channel to route to, so it goes to the channel-less
     * `/discuss` route with the tab as an `active_id` query param.
     * @override
     */
    setActiveURL(activeId) {
        const url = new URL(browser.location);
        const [model, id] = activeId?.split("_") ?? [];
        if (model === "discuss.channel") {
            url.pathname = `/discuss/channel/${id}`;
            url.searchParams.delete("active_id");
        } else {
            url.pathname = "/discuss";
            url.searchParams.set("active_id", activeId);
        }
        browser.history.pushState(browser.history.state, null, url.toString());
    },
});
