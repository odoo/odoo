import { Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";

export class Activity extends Record {
    static _name = "mail.activity";
    static id = "id";
    /**
     * @param {Object} data
     * @param {Object} [param1]
     * @param {boolean} param1.broadcast
     * @returns {import("models").Activity}
     */
    static _insert(data, { broadcast = true } = {}) {
        /** @type {import("models").Activity} */
        const activity = this.preinsert(data);
        assignDefined(activity, data);
        if (broadcast) {
            this.store.activityBroadcastChannel?.postMessage({
                type: "INSERT",
                payload: activity.serialize(),
            });
        }
        return activity;
    }

    /** @type {number} */
    id;
    /** @type {boolean} */
    active;
    /** @type {string} */
    activity_category;
    /** @type {[number, string]} */
    activity_type_id;
    /** @type {string|false} */
    activity_decoration;
    /** @type {Object[]} */
    attachment_ids;
    /** @type {boolean} */
    can_write;
    /** @type {'suggest'|'trigger'} */
    chaining_type;
    /** @type {luxon.DateTime} */
    create_date = Record.attr(undefined, { type: "datetime" });
    /** @type {[number, string]} */
    create_uid;
    /** @type {luxon.DateTime} */
    date_deadline = Record.attr(undefined, { type: "date" });
    /** @type {luxon.DateTime} */
    date_done = Record.attr(undefined, { type: "date" });
    /** @type {string} */
    display_name;
    /** @type {boolean} */
    has_recommended_activities;
    /** @type {string} */
    feedback;
    /** @type {string} */
    icon = "fa-tasks";
    /** @type {Object[]} */
    mail_template_ids;
    note = Record.attr("", { html: true });
    persona = Record.one("Persona");
    /** @type {number|false} */
    previous_activity_type_id;
    /** @type {number|false} */
    recommended_activity_type_id;
    /** @type {string} */
    res_model;
    /** @type {[number, string]} */
    res_model_id;
    /** @type {number} */
    res_id;
    /** @type {string} */
    res_name;
    /** @type {'overdue'|'planned'|'today'} */
    state;
    /** @type {string} */
    summary;
    /** @type {[number, string]} */
    user_id;
    /** @type {string} */
    write_date;
    /** @type {[number, string]} */
    write_uid;

    serialize() {
        return JSON.parse(JSON.stringify(this.toData()));
    }
}

Activity.register();
