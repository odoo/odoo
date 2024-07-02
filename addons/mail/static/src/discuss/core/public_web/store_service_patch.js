import { Store } from "@mail/core/common/store_service";
import { Record } from "@mail/model/record";
import { router } from "@web/core/browser/router";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.discuss = Record.one("DiscussApp", {
            compute() {
                return { activeTab: "main" };
            },
        });
        this.menuThreads = Record.many("Thread", {
            /** @this {import("models").Store} */
            compute() {
                /** @type {import("models").Thread[]} */
                let threads = Object.values(this.Thread.records).filter(
                    (thread) =>
                        thread.displayToSelf ||
                        (thread.needactionMessages.length > 0 && thread.model !== "mail.box")
                );
                const tab = this.discuss.activeTab;
                if (tab !== "main") {
                    threads = threads.filter(({ channel_type }) =>
                        this.tabToThreadType(tab).includes(channel_type)
                    );
                } else if (tab === "main" && this.env.inDiscussApp) {
                    threads = threads.filter(({ channel_type }) =>
                        this.tabToThreadType("mailbox").includes(channel_type)
                    );
                }
                return threads;
            },
            /**
             * @this {import("models").Store}
             * @param {import("models").Thread} a
             * @param {import("models").Thread} b
             */
            sort(a, b) {
                /**
                 * Ordering:
                 * - threads with needaction
                 * - unread channels
                 * - read channels
                 * - odoobot chat
                 *
                 * In each group, thread with most recent message comes first
                 */
                const aOdooBot = a.isCorrespondentOdooBot;
                const bOdooBot = b.isCorrespondentOdooBot;
                if (aOdooBot && !bOdooBot) {
                    return 1;
                }
                if (bOdooBot && !aOdooBot) {
                    return -1;
                }
                const aNeedaction = a.needactionMessages.length;
                const bNeedaction = b.needactionMessages.length;
                if (aNeedaction > 0 && bNeedaction === 0) {
                    return -1;
                }
                if (bNeedaction > 0 && aNeedaction === 0) {
                    return 1;
                }
                const aUnread = a.selfMember?.message_unread_counter;
                const bUnread = b.selfMember?.message_unread_counter;
                if (aUnread > 0 && bUnread === 0) {
                    return -1;
                }
                if (bUnread > 0 && aUnread === 0) {
                    return 1;
                }
                const aMessageDatetime = a.newestPersistentNotEmptyOfAllMessage?.datetime;
                const bMessageDateTime = b.newestPersistentNotEmptyOfAllMessage?.datetime;
                if (!aMessageDatetime && bMessageDateTime) {
                    return 1;
                }
                if (!bMessageDateTime && aMessageDatetime) {
                    return -1;
                }
                if (aMessageDatetime && bMessageDateTime && aMessageDatetime !== bMessageDateTime) {
                    return bMessageDateTime - aMessageDatetime;
                }
                return b.localId > a.localId ? 1 : -1;
            },
        });
        const discussActionIds = ["mail.action_discuss", "discuss"];
        if (this.action_discuss_id) {
            discussActionIds.push(this.action_discuss_id);
        }
        this.discuss.isActive ||= discussActionIds.includes(router.current.action);
        Store.env.services.ui.bus.addEventListener("resize", () => {
            this.discuss.activeTab = "main";
            if (Store.env.services.ui.isSmall && this.discuss.thread?.channel_type) {
                this.discuss.activeTab = this.discuss.thread.channel_type;
            }
        });
        this.channels = this.makeCachedFetchData({ channels_as_member: true });
    },
};
patch(Store.prototype, StorePatch);
