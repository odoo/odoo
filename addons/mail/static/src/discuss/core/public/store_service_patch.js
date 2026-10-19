import { storeService } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

patch(storeService, {
    start(env, services) {
        const store = super.start(...arguments);
        // The public page has no session data: its payload is embedded in the page. Insert it
        // as part of the store start, hence before the app is mounted, because the Discuss
        // client action reads it (channel to display, welcome page, token) when it is set up.
        store.insert(odoo.discuss_data);
        return store;
    },
});
