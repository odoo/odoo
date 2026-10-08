import { StorePlugin } from "@mail/core/common/store_plugin";

import { patch } from "@web/core/utils/patch";

patch(StorePlugin.prototype, {
    setup() {
        super.setup(...arguments);
        // The public page has no session data: its payload is embedded in the page. Insert it
        // as part of the store start, hence before the app is mounted, because the Discuss
        // client action reads it (channel to display, welcome page, token) when it is set up.
        this.store.insert(odoo.discuss_data);
        this.store.isOdooWhiteTheme = this.store.publicColorScheme !== "dark";
    },
});
