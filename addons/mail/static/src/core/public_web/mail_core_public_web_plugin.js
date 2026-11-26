import { StorePlugin } from "@mail/core/common/store_plugin";

import { Plugin, usePlugin } from "@odoo/owl";

import { services } from "@web/core/services";

export class MailCorePublicWebPlugin extends Plugin {
    /** Started with the store it uses (see `StorePlugin`). */
    static sequence = 110;

    setup() {
        const store = usePlugin(StorePlugin);
        store.ensureInitialized();
        store.messagingMenu.initializeCountersFetcher.fetch();
    }
}

services.add(MailCorePublicWebPlugin);
