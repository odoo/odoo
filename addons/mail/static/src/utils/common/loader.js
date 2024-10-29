import { markRaw } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";

function makeItem(bundleName) {
    return {
        loaded: false,
        loadingListeners: markRaw([]),
        _load: memoize(() => loadBundle(bundleName)),
        async load() {
            try {
                await this._load();
            } catch {
                // Could be intentional (tour ended successfully while bundle still loading)
            } finally {
                for (const listener of this.loadingListeners) {
                    listener();
                }
                this.loadingListeners = [];
                this.loaded = true;
            }
        },
        onLoaded(cb) {
            this.loadingListeners.push(cb);
        },
    };
}

export const loader = {
    lamejs: makeItem("mail.assets_lamejs"),
    marked: makeItem("mail.assets_marked"),
    odoo_sfu: makeItem("mail.assets_odoo_sfu"),
};
