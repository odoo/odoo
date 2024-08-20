import { Store, storeService } from "@mail/core/common/store_service";
import { Record } from "@mail/core/common/record";
import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.discuss = Record.one("DiscussApp");
        this.action_discuss_id;
    },
    onStarted() {
        super.onStarted(...arguments);
        this.discuss = { activeTab: "main" };
        this.env.bus.addEventListener(
            "discuss.channel/new_message",
            ({ detail: { channel, message } }) => {
                if (this.env.services.ui.isSmall || message.isSelfAuthored) {
                    return;
                }
                if (channel.isCorrespondentOdooBot && this.odoobotOnboarding) {
                    // this cancels odoobot onboarding auto-opening of chat window
                    this.odoobotOnboarding = false;
                    return;
                }
                channel.notifyMessageToUser(message);
            }
        );
    },
    getDiscussSidebarCategoryCounter(categoryId) {
        return this.DiscussAppCategory.get({ id: categoryId }).threads.reduce((acc, channel) => {
            if (categoryId === "channels") {
                return channel.message_needaction_counter > 0 ? acc + 1 : acc;
            } else {
                return channel.selfMember?.message_unread_counter > 0 ? acc + 1 : acc;
            }
        }, 0);
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
            store.discuss.activeTab = "main";
            if (services.ui.isSmall && store.discuss.thread?.channel_type) {
                store.discuss.activeTab = store.discuss.thread.channel_type;
            }
        });
        return store;
    },
});
