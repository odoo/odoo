/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

export class ActivityService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        try {
            // useful for synchronizing activity data between multiple tabs
            this.broadcastChannel = new browser.BroadcastChannel("mail.activity.channel");
            this.broadcastChannel.onmessage = this._onBroadcastChannelMessage.bind(this);
        } catch {
            // BroadcastChannel API is not supported (e.g. Safari < 15.4), so disabling it.
            this.broadcastChannel = null;
        }
        this.env = env;
        this.store = services["mail.store"];
        this.orm = services.orm;
    }

    /**
     * @param {import("models").Activity} activity
     * @param {number[]} attachmentIds
     */
    async markAsDone(activity, attachmentIds = []) {
        await this.orm.call("mail.activity", "action_feedback", [[activity.id]], {
            attachment_ids: attachmentIds,
            feedback: activity.feedback,
        });
        this.broadcastChannel?.postMessage({
            type: "RELOAD_CHATTER",
            payload: { id: activity.res_id, model: activity.res_model },
        });
    }

    async markAsDoneAndScheduleNext(activity) {
        const action = await this.env.services.orm.call(
            "mail.activity",
            "action_feedback_schedule_next",
            [[activity.id]],
            { feedback: activity.feedback }
        );
        this.broadcastChannel?.postMessage({
            type: "RELOAD_CHATTER",
            payload: { id: activity.res_id, model: activity.res_model },
        });
        return action;
    }

    async edit(activityId) {
        return new Promise((resolve) =>
            this.env.services.action.doAction(
                {
                    type: "ir.actions.act_window",
                    name: _t("Schedule Activity"),
                    res_model: "mail.activity",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    res_id: activityId,
                },
                { onClose: resolve }
            )
        );
    }

    async schedule(resModel, resIds, defaultActivityTypeId = undefined) {
        const context = {
            active_model: resModel,
            active_ids: resIds,
            active_id: resIds[0],
            ...(defaultActivityTypeId !== undefined
                ? {
                      default_activity_type_id: defaultActivityTypeId,
                  }
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
    }

    delete(activity, { broadcast = true } = {}) {
        activity.delete();
        if (broadcast) {
            this.broadcastChannel?.postMessage({ type: "DELETE", payload: { id: activity.id } });
        }
    }

    _onBroadcastChannelMessage({ data }) {
        switch (data.type) {
            case "INSERT":
                this.store.Activity.insert(data.payload, { broadcast: false, html: true });
                break;
            case "DELETE": {
                const activity = this.store.Activity.insert(data.payload, { broadcast: false });
                this.delete(activity, { broadcast: false });
                break;
            }
            case "RELOAD_CHATTER": {
                const thread = this.env.services["mail.thread"].getThread(
                    data.payload.model,
                    data.payload.id
                );
                this.env.services["mail.thread"].fetchNewMessages(thread);
                break;
            }
        }
    }

    _serialize(activity) {
        activity = activity.toData();
        return JSON.parse(JSON.stringify(activity));
    }
}

export const activityService = {
    dependencies: ["mail.store", "orm"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new ActivityService(env, services);
    },
};

registry.category("services").add("mail.activity", activityService);
