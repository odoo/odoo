/* @odoo-module */

import { Activity } from "@mail/core/web/activity_model";
import { assignDefined } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { fetchNewMessages } from "../common/thread_service";
import { makeFnPatchable } from "@mail/utils/common/patch";
import { markup } from "@odoo/owl";

let gEnv;
let actionService;
let broadcastChannel;
let orm;
let store;

export function deleteActivity(activity, { broadcast = true } = {}) {
    delete store.activities[activity.id];
    if (broadcast) {
        broadcastChannel.postMessage({ type: "delete", payload: { id: activity.id } });
    }
}

/**
 * @param {import("@mail/core/web/activity_model").Data} data
 * @param {Object} [param1]
 * @param {boolean} param1.broadcast
 * @returns {import("@mail/core/web/activity_model").Activity}
 */
export const insertActivity = makeFnPatchable(function (data, { broadcast = true } = {}) {
    const activity = store.activities[data.id] ?? new Activity(store, data.id);
    if (data.request_partner_id) {
        data.request_partner_id = data.request_partner_id[0];
    }
    assignDefined(activity, data);
    if (broadcast) {
        broadcastChannel.postMessage({
            type: "insert",
            payload: _serializeActivity(activity),
        });
    }
    return activity;
});

/**
 * @param {import("@mail/core/web/activity_model").Activity} activity
 * @param {number[]} attachmentIds
 */
export async function markActivityAsDone(activity, attachmentIds = []) {
    await orm.call("mail.activity", "action_feedback", [[activity.id]], {
        attachment_ids: attachmentIds,
        feedback: activity.feedback,
    });
    broadcastChannel.postMessage({
        type: "reload chatter",
        payload: { resId: activity.res_id, resModel: activity.res_model },
    });
}

export async function markActivityAsDoneAndScheduleNext(activity) {
    const action = await orm.call(
        "mail.activity",
        "action_feedback_schedule_next",
        [[activity.id]],
        { feedback: activity.feedback }
    );
    broadcastChannel.postMessage({
        type: "reload chatter",
        payload: { resId: activity.res_id, resModel: activity.res_model },
    });
    return action;
}

export async function scheduleActivity(
    resModel,
    resId,
    activityId = false,
    defaultActivityTypeId = undefined
) {
    const context = {
        default_res_model: resModel,
        default_res_id: resId,
    };
    if (defaultActivityTypeId !== undefined) {
        context.default_activity_type_id = defaultActivityTypeId;
    }
    return new Promise((resolve) => {
        actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("Schedule Activity"),
                res_model: "mail.activity",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                context,
                res_id: activityId,
            },
            { onClose: resolve }
        );
    });
}

function _serializeActivity(activity) {
    const data = { ...activity };
    delete data._store;
    return JSON.parse(JSON.stringify(data));
}

export class ActivityService {
    constructor(env, services) {
        gEnv = env;
        actionService = services.action;
        // useful for synchronizing activity data between multiple tabs
        broadcastChannel = this.broadcastChannel = new BroadcastChannel("mail.activity.channel");
        broadcastChannel.onmessage = this._onBroadcastChannelMessage.bind(this);
        this.env = env;
        /** @type {import("@mail/core/common/store_service").Store} */
        store = services["mail.store"];
        orm = services.orm;
    }

    _onBroadcastChannelMessage({ data }) {
        switch (data.type) {
            case "insert":
                insertActivity(data.payload, { broadcast: false });
                break;
            case "delete":
                deleteActivity(data.payload, { broadcast: false });
                break;
            case "reload chatter": {
                let thread;
                // this prevents cyclic dependencies between message service and insertFollower
                gEnv.bus.trigger("core/web/thread_service.getThread", {
                    cb: (res) => (thread = res),
                    params: [data.payload.resModel, data.payload.resId],
                });
                fetchNewMessages(thread);
                break;
            }
        }
    }
}

export const activityService = {
    dependencies: ["action", "mail.store", "orm"],
    start(env, services) {
        return new ActivityService(env, services);
    },
};

registry.category("services").add("mail.activity", activityService);
