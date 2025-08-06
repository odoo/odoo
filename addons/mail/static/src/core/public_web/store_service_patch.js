import { Store, storeService } from "@mail/core/common/store_service";
import { fields } from "@mail/core/common/record";
import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.discuss = fields.One("DiscussApp");
        /** @type {number|undefined} */
        this.action_discuss_id;
    },
    onStarted() {
        super.onStarted(...arguments);
        this.discuss = { activeTab: "notification" };
        this.env.bus.addEventListener(
            "discuss.channel/new_message",
            ({ detail: { channel, message, silent } }) => {
                if (this.env.services.ui.isSmall || message.isSelfAuthored || silent) {
                    return;
                }
                channel.notifyMessageToUser(message);
            }
        );
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
            store.discuss.activeTab = "notification";
            if (services.ui.isSmall && store.discuss.thread?.channel_type) {
                store.discuss.activeTab = store.discuss.thread.channel_type;
            }
        });
        return store;
    },
});
