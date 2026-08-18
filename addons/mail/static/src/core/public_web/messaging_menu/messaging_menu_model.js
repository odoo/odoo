import { fields, Record } from "@mail/model/export";

import { _t } from "@web/core/l10n/translation";

/** @type {import("menu_tabs").MenuTabs} */
export const MENU_TABS = { BOOKMARK: "bookmark", NOTIFICATION: "notification" };

export class MessagingMenu extends Record {
    static singleton = true;

    setup() {
        super.setup(...arguments);
        this.assignComputed("bookmarkTab", function computeBookmarkTab() {
            if (this.store.self_user?.share !== false) {
                return;
            }
            return this.store.MessagingMenuTab.insert({
                id: MENU_TABS.BOOKMARK,
                important: false,
                recordType: "mail.message",
                includesMessage: (msg) => msg.is_bookmarked,
                icon: "bookmark",
                activeIcon: "bookmark",
                sequence: 120,
                label: _t("Bookmarks"),
                hideWhenZeroCounter: true,
                actions: [
                    {
                        id: "remove-all-bookmarks",
                        text: _t("Remove all"),
                        isDisabled: () => !this.bookmarkTab.counter,
                        onClick: () => this.store.removeAllBookmarks(),
                        preventDropdownClose: true,
                    },
                ],
            });
        });
        this.assignComputed("notificationTab", function computeNotificationTab() {
            if (this.store.self_user?.notification_type !== "inbox") {
                return;
            }
            return this.store.MessagingMenuTab.insert({
                id: MENU_TABS.NOTIFICATION,
                recordType: "mail.message",
                includesMessage: (msg) =>
                    (msg.needaction || msg.needaction_done) && this.notificationMatchesExtra(msg),
                icon: "notifications",
                activeIcon: "notifications",
                sequence: 60,
                label: _t("Notifications"),
                emptyState: {
                    title: _t("You're all caught up!"),
                    subtitle: _t("Notifications of the documents you follow will appear here."),
                },
                filters: [
                    {
                        id: "notification_unread",
                        text: _t("Unread"),
                        includesMessage: (msg) =>
                            msg.needaction && this.notificationMatchesExtra(msg),
                        isDefault: true,
                    },
                ],
                actions: [
                    {
                        id: "mark-all-read",
                        text: _t("Mark all read"),
                        isDisabled: () => !this.notificationTab.counter,
                        onClick: () => this.store.markNeedactionMessagesAsRead(),
                        preventDropdownClose: true,
                    },
                ],
            });
        });
    }

    bookmarkTab = fields.One("MessagingMenuTab");
    globalCounter = this.computed(() => this._computeGlobalCounter());
    initializeCountersFetcher = this.computed(() =>
        this.store.makeCachedFetchData("/mail/messaging_menu/initialize_counters", () => {
            const filter_id_by_tab_id_by_record_type = {};
            for (const tab of this.allTabs) {
                if (tab.hidden) {
                    continue;
                }
                filter_id_by_tab_id_by_record_type[tab.recordType] ??= {};
                filter_id_by_tab_id_by_record_type[tab.recordType][tab.id] =
                    tab.defaultFilter?.id ?? null;
            }
            return { filter_id_by_tab_id_by_record_type };
        })
    );
    notificationTab = fields.One("MessagingMenuTab");
    get allTabs() {
        return [...this.store.MessagingMenuTab.records.values()];
    }
    get sortedAllTabs() {
        return [...this.allTabs].sort(
            (t1, t2) => t1.sequence - t2.sequence || t1.id.localeCompare(t2.id)
        );
    }
    _computeGlobalCounter() {
        return this.visibleTabs.reduce((sum, t) => sum + (t.important ? t.counter ?? 0 : 0), 0);
    }

    get visibleTabs() {
        return this.allTabs.filter((tab) => tab.isShown);
    }
    get sortedVisibleTabs() {
        return [...this.visibleTabs].sort(
            (t1, t2) => t1.sequence - t2.sequence || t1.id.localeCompare(t2.id)
        );
    }

    /**
     * Extra actions appended to a tab by the bundles extending it.
     *
     * @param {import("menu_tabs").MenuTabs[keyof import("menu_tabs").MenuTabs]} tabId
     */
    extraTabActions(tabId) {
        return [];
    }

    /** Extra membership predicate ANDed into the notification tab. Extended by the
     * /discuss/ bundle to exclude channels from the notification messages. */
    notificationMatchesExtra() {
        return true;
    }

    /**
     * Tab hosting OdooBot extras (delivery failures, push notification request). Null in
     * the base mail bundle: discuss overrides it to point to the chat tab, keeping mail
     * unaware of the "chat" concept.
     */
    get odooBotNotificationsTab() {
        return null;
    }
}

MessagingMenu.register();
