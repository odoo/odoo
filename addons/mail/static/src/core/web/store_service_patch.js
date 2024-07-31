import { Record } from "@mail/core/common/record";
import { Store } from "@mail/core/common/store_service";
import { compareDatetime } from "@mail/utils/common/misc";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.activityCounter = 0;
        this.activity_counter_bus_id = 0;
        this.activityGroups = Record.attr([], {
            onUpdate() {
                this.onUpdateActivityGroups();
            },
            sort(g1, g2) {
                /**
                 * Sort by model ID ASC but always place the activity group for "mail.activity" model at
                 * the end (other activities).
                 */
                const getSortId = (activityGroup) =>
                    activityGroup.model === "mail.activity" ? Number.MAX_VALUE : activityGroup.id;
                return getSortId(g1) - getSortId(g2);
            },
        });
        this.inbox = Record.one("Thread");
        this.starred = Record.one("Thread");
        this.history = Record.one("Thread");
    },
    onStarted() {
        super.onStarted(...arguments);
        this.inbox = {
            id: "inbox",
            model: "mail.box",
            name: _t("Inbox"),
        };
        this.starred = {
            id: "starred",
            model: "mail.box",
            name: _t("Starred"),
        };
        this.history = {
            id: "history",
            model: "mail.box",
            name: _t("History"),
        };
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
    get initMessagingParams() {
        return {
            ...super.initMessagingParams,
            failures: true,
            systray_get_activities: true,
        };
    },
    getNeedactionChannels() {
        return this.getRecentChannels().filter((channel) => channel.importantCounter > 0);
    },
    getRecentChannels() {
        return Object.values(this.Thread.records)
            .filter((thread) => thread.model === "discuss.channel")
            .sort((a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id);
    },
    onUpdateActivityGroups() {},
    async scheduleActivity(resModel, resIds, defaultActivityTypeId = undefined) {
        const context = {
            active_model: resModel,
            active_ids: resIds,
            active_id: resIds[0],
            ...(defaultActivityTypeId !== undefined
                ? { default_activity_type_id: defaultActivityTypeId }
                : {}),
        };
        return new Promise((resolve) =>
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
                { onClose: resolve }
            )
        );
    },
    _onActivityBroadcastChannelMessage({ data }) {
        switch (data.type) {
            case "INSERT":
                this.Activity.insert(data.payload, { broadcast: false, html: true });
                break;
            case "DELETE": {
                const activity = this.Activity.insert(data.payload, { broadcast: false });
                activity.remove({ broadcast: false });
                break;
            }
            case "RELOAD_CHATTER": {
                const thread = this.Thread.insert({
                    model: data.payload.model,
                    id: data.payload.id,
                });
                thread.fetchNewMessages();
                break;
            }
        }
    },
    async unstarAll() {
        // apply the change immediately for faster feedback
        this.store.starred.counter = 0;
        this.store.starred.messages = [];
        await this.env.services.orm.call("mail.message", "unstar_all");
    },
};
patch(Store.prototype, StorePatch);
