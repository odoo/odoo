import { Store } from "@mail/core/common/store_service";

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    _hasFullscreenUrlOnUpdate() {
        const channel = this.discuss?.thread?.channel;
        let base = browser.location.href;
        if (channel?.invitationLink) {
            base = channel.invitationLink;
        } else if (channel) {
            base = `/discuss/channel/${channel.id}`;
        }
        const url = new URL(base, browser.location.origin);
        url.search = browser.location.search;
        url.searchParams.delete("fullscreen");
        browser.history.replaceState(browser.history.state, null, url);
    },
};
patch(Store.prototype, StorePatch);
