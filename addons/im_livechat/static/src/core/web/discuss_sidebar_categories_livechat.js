/* @odoo-module */

import { discussSidebarCategoriesRegistry } from "@mail/discuss/core/web/discuss_sidebar_categories";

discussSidebarCategoriesRegistry.add(
    "livechats",
    {
        predicate: (store) => store.discuss.livechat.threads.some((thread) => thread?.is_pinned),
        value: (store) => store.discuss.livechat,
    },
    { sequence: 20 }
);
