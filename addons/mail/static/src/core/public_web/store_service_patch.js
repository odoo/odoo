import { Store, storeService } from "@mail/core/common/store_service";
import { fields } from "@mail/model/export";
import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.discuss = fields.One("DiscussApp");
        this.messagingMenu = fields.One("MessagingMenu", { compute: () => ({}) });
        /** @type {number|undefined} */
        this.action_discuss_id;
    },
    onStarted() {
        super.onStarted(...arguments);
        this.discuss = {};
    },
});

patch(storeService, {
    start(env, services) {
        const store = super.start(...arguments);
        const discussActionIds = ["mail.action_discuss", "discuss"];
        if (store.action_discuss_id) {
            discussActionIds.push(store.action_discuss_id);
        }
        store.discuss.isActive ||= discussActionIds.includes(router.current.action);
        services.ui.bus.addEventListener("resize", () => {
            const thread = store.discuss.thread;
            if (services.ui.isSmall && thread?.channel) {
                store.discuss.messagingMenuSidebarState.activeTab =
                    thread.channel.primaryMessagingMenuTab;
            } else {
                store.discuss.messagingMenuSidebarState.activeTab = store.messagingMenu.allTabs[0];
            }
        });
        return store;
    },
});
