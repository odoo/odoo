import { Store, storeService } from "@mail/core/common/store_service";
import { fields } from "@mail/model/export";
import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";
import { cleanTerm } from "@mail/utils/common/format";
import { threadCompareRegistry } from "@mail/core/common/thread_compare";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.discuss = fields.One("DiscussApp");
        /** @type {number|undefined} */
        this.action_discuss_id;
        this.menuThreads = fields.Many("mail.thread", {
            /** @this {import("models").Store} */
            compute() {
                /** @type {import("models").Thread[]} */
                const searchTerm = cleanTerm(this.discuss.searchTerm);
                let threads = Object.values(this["mail.thread"].records).filter(
                    (thread) =>
                        (thread.channel?.displayToSelf ||
                            (thread.needactionMessages.length > 0 &&
                                thread.model !== "mail.box")) &&
                        cleanTerm(thread.displayName).includes(searchTerm)
                );
                const tab = this.discuss.activeTab;
                if (tab === "inbox") {
                    threads = threads.filter((thread) =>
                        this.tabToThreadType("mailbox").includes(thread.channel?.channel_type)
                    );
                } else if (tab === "starred") {
                    threads = [this.starred];
                } else if (tab !== "notification") {
                    threads = threads.filter((thread) =>
                        this.tabToThreadType(tab).includes(thread.channel?.channel_type)
                    );
                }
                return threads;
            },
            /**
             * @this {import("models").Store}
             * @param {import("models").Thread} thread1
             * @param {import("models").Thread} thread2
             */
            sort(thread1, thread2) {
                const compareFunctions = threadCompareRegistry.getAll();
                for (const fn of compareFunctions) {
                    const result = fn(thread1, thread2);
                    if (result !== undefined) {
                        return result;
                    }
                }
                return thread2.localId > thread1.localId ? 1 : -1;
            },
        });
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
            if (services.ui.isSmall && store.discuss.thread?.channel?.channel_type) {
                store.discuss.activeTab = store.discuss.thread.channel?.channel_type;
            }
        });
        return store;
    },
});
