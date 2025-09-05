import { fields, Record } from "@mail/core/common/record";
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
    activity_type_id = fields.One("mail.activity.type");
    /** @type {string|false} */
    activity_decoration;
    /** @type {Object[]} */
    attachment_ids;
    /** @type {boolean} */
    can_write;
    /** @type {'suggest'|'trigger'} */
    chaining_type;
    create_date = fields.Datetime();
    create_uid = fields.One("res.users");
    date_deadline = fields.Date();
    date_done = fields.Date();
    /** @type {string} */
    display_name;
    /** @type {boolean} */
    has_recommended_activities;
    /** @type {string} */
    feedback;
    /** @type {string} */
    icon = "fa-tasks";
    mail_template_ids = fields.Many("mail.template");
    note = fields.Html("");
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
    user_id = fields.One("res.users");
    /** @type {string} */
    write_date;
    /** @type {[number, string]} */
    write_uid;

    serialize() {
        return JSON.parse(JSON.stringify(this.toData(["user_id"])));
    }
}

Activity.register();
