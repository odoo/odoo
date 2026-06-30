import { fields, Record } from "@mail/model/export";

import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";

export class MessagingMenu extends Record {
    static singleton = true;

    static new() {
        const nav = super.new(...arguments);
        nav.initializeCountersFetcher = nav.store.makeCachedFetchData(
            "/mail/messaging_menu/initialize_counters",
            () => {
                const domain_by_tab_id_by_record_type = {};
                for (const tab of nav.allTabs) {
                    if (!tab.domain || tab.hidden) {
                        continue;
                    }
                    const defaultFilter = tab.defaultFilter;
                    const counterDomain = defaultFilter
                        ? Domain.and([tab.domain, defaultFilter.domain]).toList({})
                        : tab.domain;
                    domain_by_tab_id_by_record_type[tab.recordType] ??= {};
                    domain_by_tab_id_by_record_type[tab.recordType][tab.id] = counterDomain;
                }
                return { domain_by_tab_id_by_record_type };
            }
        );
        return nav;
    }

    bookmarkTab = fields.One("MessagingMenuTab", {
        compute() {
            if (this.store.self_user?.share !== false) {
                return;
            }
            return {
                id: "bookmark",
                important: false,
                recordType: "mail.message",
                domain: [["bookmarked_partner_ids", "=", this.store.self_user?.partner_id?.id]],
                icon: "fa fa-bookmark-o",
                activeIcon: "fa fa-bookmark",
                sequence: 120,
                label: _t("Bookmarks"),
                hideWhenEmpty: true,
                matchesMessage: (msg) => msg.is_bookmarked,
                actions: [
                    {
                        id: "remove-all-bookmarks",
                        text: _t("Remove all"),
                        isDisabled: () => !this.bookmarkTab.counter,
                        onClick: () => this.store.removeAllBookmarks(),
                    },
                ],
            };
        },
        eager: true,
    });
    globalCounter = fields.Attr(0, {
        compute() {
            return this._computeGlobalCounter();
        },
    });
    notificationTab = fields.One("MessagingMenuTab", {
        compute() {
            if (this.store.self_user?.notification_type !== "inbox") {
                return;
            }
            return {
                id: "notification",
                recordType: "mail.message",
                domain: [
                    ["notification_ids.res_partner_id", "=", this.store.self_user?.partner_id?.id],
                    ...this.notificationExtraDomain,
                ],
                icon: "fa fa-bell-o",
                activeIcon: "fa fa-bell",
                sequence: 60,
                label: _t("Notifications"),
                emptyState: {
                    title: _t("You're all caught up!"),
                    subtitle: _t("New messages will appear here."),
                },
                matchesMessage: (msg) =>
                    (msg.needaction || msg.needaction_done) && this.notificationMatchesExtra(msg),
                filters: [
                    {
                        id: "notification_unread",
                        text: _t("Unread"),
                        domain: [["needaction", "=", true]],
                        isDefault: true,
                        matchesMessage: (msg) =>
                            msg.needaction && this.notificationMatchesExtra(msg),
                    },
                ],
                actions: [
                    {
                        id: "mark-all-read",
                        text: _t("Mark all read"),
                        isDisabled: () => !this.notificationTab.counter,
                        onClick: () => this.store.markNeedactionMessagesAsRead(),
                    },
                ],
            };
        },
        eager: true,
    });
    allTabs = fields.Many("MessagingMenuTab", {
        inverse: "messagingMenuAsTab",
        sort(t1, t2) {
            return t1.sequence - t2.sequence || t1.id.localeCompare(t2.id);
        },
    });
    visibleTabs = fields.Many("MessagingMenuTab", {
        inverse: "messagingMenuAsVisibleTabs",
        sort(t1, t2) {
            return t1.sequence - t2.sequence || t1.id.localeCompare(t2.id);
        },
    });

    _computeGlobalCounter() {
        return this.visibleTabs.reduce((sum, t) => sum + (t.important ? t.counter ?? 0 : 0), 0);
    }

    /** Extra domain appended to the notification tab. Extended by the /discuss/ bundle to
     * exclude channels from the notification messages. */
    get notificationExtraDomain() {
        return [];
    }

    /** Extra membership predicate AND-ed into the notification tab. Extended by the
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
