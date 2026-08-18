import { Store } from "@mail/core/common/store_service";
import { MENU_TABS } from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

let unread_store;

/**
 * Save the unread counter in the database shared with the service worker, so that the app
 * badge stays up to date.
 *
 * @param {number} counter
 * @param {boolean} [retry=true]
 */
async function saveUnreadCounter(counter, retry = true) {
    try {
        unread_store ??= new window.idbKeyval.Store(
            "odoo-mail-unread-db",
            "odoo-mail-unread-store"
        );
    } catch {
        // The browser does not allow the database to be opened (private mode, blocked
        // storage): opening it again would fail the same way, and the app badge is cosmetic.
        return;
    }
    try {
        await window.idbKeyval.set("unread", counter, unread_store);
    } catch {
        // The connection cached by idbKeyval was closed by the browser (site data cleared,
        // storage eviction, database deleted from another tab): drop it so that the retry
        // saves the counter on a new one. When that fails too the error is ignored.
        unread_store = undefined;
        if (retry) {
            await saveUnreadCounter(counter, false);
        }
    }
}

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        /** @type {BroadcastChannel|null} synchronizes activity data between tabs */
        this.activityBroadcastChannel = null;
        this.activityCounter = 0;
        this.activity_counter_bus_id = 0;
        this.activity_groups = undefined;
        this.activities_to_assign_count = undefined;
        this.onChange(
            () => this.activityGroups,
            function onChangeActivityGroups() {
                this.onUpdateActivityGroups();
            },
            { immediate: true }
        );
        this.messagingMenuSystrayState = this.computed(
            () =>
                this.MessagingMenuUIState.get("mail.systray") ??
                this.MessagingMenuUIState.insert({ id: "mail.systray", activeTab: MENU_TABS.CHAT })
        );
    },
    initialize() {
        super.initialize(...arguments);
        if (this.self_user?.share === false) {
            this.fetchStoreData("failures");
            this.fetchStoreData("systray_get_activities");
        }
    },
    onStarted() {
        super.onStarted(...arguments);
        try {
            // useful for synchronizing activity data between multiple tabs
            this.activityBroadcastChannel = new browser.BroadcastChannel("mail.activity.channel");
            this.activityBroadcastChannel.onmessage =
                this._onActivityBroadcastChannelMessage.bind(this);
        } catch {
            // BroadcastChannel API is not supported (e.g. Safari < 15.4), so disabling it.
            this.activityBroadcastChannel = null;
        }
    },
    get activityGroups() {
        return (this.activity_groups || []).slice().sort((g1, g2) => {
            /**
             * Sort by model ID ASC but always place the activity group for "mail.activity" model at
             * the end (other activities).
             */
            const getSortId = (activityGroup) =>
                activityGroup.model === "mail.activity" ? Number.MAX_VALUE : activityGroup.id;
            return getSortId(g1) - getSortId(g2);
        });
    },
    onPushNotificationDisplayed() {
        super.onPushNotificationDisplayed(...arguments);
        this.updateAppBadge();
    },
    onUpdateActivityGroups() {},
    /**
     * @param {string} resModel
     * @param {number[]} resIds
     * @param {number|undefined} defaultActivityTypeId
     */
    async scheduleActivity(resModel, resIds, defaultActivityTypeId = undefined) {
        const context = {
            active_model: resModel,
            active_ids: resIds,
            active_id: resIds[0],
            ...(defaultActivityTypeId !== undefined
                ? { default_activity_type_id: defaultActivityTypeId }
                : {}),
        };
        await new Promise((resolve) =>
            this.env.services.action.doAction(
                {
                    type: "ir.actions.act_window",
                    name:
                        resIds && resIds.length > 1
                            ? _t("Schedule Activity On Selected Records")
                            : _t("Schedule Activity"),
                    res_model: "mail.activity.schedule",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    context,
                },
                {
                    onClose: resolve,
                    additionalContext: {
                        dialog_size: "medium",
                    },
                }
            )
        );
    },
    updateAppBadge() {
        if (window.idbKeyval) {
            saveUnreadCounter(this.globalCounter);
            Promise.resolve(navigator.setAppBadge?.(this.globalCounter)).catch(() => {}); // FIXME: Illegal invocation error in HOOT
        }
    },
    /**
     * @param {object} param0
     * @param {{ type: "INSERT"|"DELETE"|"RELOAD_CHATTER", payload: Partial<import("models").Activity> }} param0.data
     */
    _onActivityBroadcastChannelMessage({ data }) {
        switch (data.type) {
            case "INSERT":
                this.insert(data.payload, { broadcast: false });
                break;
            case "DELETE": {
                const activity = this["mail.activity"].insert(data.payload, { broadcast: false });
                activity.remove({ broadcast: false });
                break;
            }
            case "RELOAD_CHATTER": {
                const thread = this["mail.thread"].insert({
                    model: data.payload.model,
                    id: data.payload.id,
                });
                thread.fetchNewMessages();
                break;
            }
        }
    },
    async removeAllBookmarks() {
        for (const message of this.store.messagingMenu.bookmarkTab.messages) {
            message.is_bookmarked = false;
        }
        await this.store.fetchStoreData("remove_all_bookmarks");
    },
    async markNeedactionMessagesAsRead() {
        const { orm, notification } = this.env.services;
        const readMessageIds = await orm.silent.call("mail.message", "mark_all_as_read");
        // Everything was read: the "Unread" filter view is now empty and fully loaded.
        const notificationTab = this.store.messagingMenu.notificationTab;
        notificationTab.loadStatusByFilterId = {
            ...notificationTab.loadStatusByFilterId,
            notification_unread: "loaded",
        };
        const close = notification.add(
            readMessageIds.length === 1
                ? _t("1 item marked as read")
                : _t("%(amount)s items marked as read", { amount: readMessageIds.length }),
            {
                type: "success",
                buttons: [
                    {
                        name: _t("Undo"),
                        icon: "undo",
                        onClick: () => {
                            orm.silent.call("mail.message", "mark_as_unread", [readMessageIds]);
                            close();
                        },
                    },
                ],
            }
        );
    },
    handleClickOnLink(ev, thread) {
        const model = ev.target.dataset.oeModel;
        const id = Number(ev.target.dataset.oeId);
        const isLinkHandledBySuper = super.handleClickOnLink(...arguments);
        if (!isLinkHandledBySuper && ev.target.tagName === "A" && id && model) {
            ev.preventDefault();
            Promise.resolve(
                this.env.services.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: model,
                    views: [[false, "form"]],
                    res_id: id,
                })
            ).then(() => this.onLinkFollowed(thread));
            return true;
        }
        return false;
    },
    /** @param {import("models").Thread} fromThread */
    onLinkFollowed(fromThread) {},
};
patch(Store.prototype, StorePatch);

registry.category("actions").add("mail.store_insert", function storeInsertAction(env, action) {
    const store = useService("mail.store");
    store.insert(action.params.store_values);
    return action.params.next_action;
});
