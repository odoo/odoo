import { Store } from "@mail/core/common/store_service";

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    _hasFullscreenUrlOnUpdate() {
        const url = new URL(browser.location.href);
        if (!this._hasFullscreenUrl) {
            url.searchParams.delete("fullscreen");
        } else if (!url.searchParams.has("fullscreen")) {
            url.searchParams.append("fullscreen", "1");
        }
        browser.history.replaceState(browser.history.state, null, url);
    },
};
patch(Store.prototype, StorePatch);
