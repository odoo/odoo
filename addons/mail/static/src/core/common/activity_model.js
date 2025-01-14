import { Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";

/**
 * @typedef Data
 * @property {string} activity_category
 * @property {[number, string]} activity_type_id
 * @property {string|false} activity_decoration
 * @property {boolean} can_write
 * @property {'suggest'|'trigger'} chaining_type
 * @property {string} create_date
 * @property {[number, string]} create_uid
 * @property {string} date_deadline
 * @property {string} date_done
 * @property {string} display_name
 * @property {boolean} has_recommended_activities
 * @property {string} icon
 * @property {number} id
 * @property {Object[]} mail_template_ids
 * @property {string} note
 * @property {number|false} previous_activity_type_id
 * @property {number|false} recommended_activity_type_id
 * @property {string} res_model
 * @property {[number, string]} res_model_id
 * @property {number} res_id
 * @property {string} res_name
 * @property {number|false} request_partner_id
 * @property {'overdue'|'planned'|'today'} state
 * @property {string} summary
 * @property {[number, string]} user_id
 * @property {string} write_date
 * @property {[number, string]} write_uid
 */

export class Activity extends Record {
    static name = "mail.activity";
    static id = "id";
    /** @type {Object.<number, import("models").Activity>} */
    static records = {};
    /** @returns {import("models").Activity} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @template T
     * @param {T} data
     * @param {Object} [param1]
     * @param {boolean} param1.broadcast
     * @returns {T extends any[] ? import("models").Activity[] : import("models").Activity}
     */
    static insert(data, { broadcast = true } = {}) {
        return super.insert(...arguments);
    }
    /**
     * @param {Data} data
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
}

Activity.register();
