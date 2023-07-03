/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";

/**
 * @typedef Data
 * @property {number} activity_type_id
 * @property {Object[]} attachments_ids
 * @property {Object} done_by
 * @property {string} date_done
 * @property {number} id
 * @property {string} res_model
 * @property {number} res_id
 * @property {string} summary
 */

export class CompletedActivity extends Record {
    static id = "id";
    /** @type {Object.<number, Activity>} */
    static records = {};

    static insert(data) {
        const completedActivity = this.get(data) ?? this.new(data);
        Object.assign(completedActivity, { id: data.id });
        assignDefined(completedActivity, data);
        return completedActivity;
    }

    /** @type {number} */
    activity_type_id;
    /** @type {Object[]} */
    attachment_ids;
    /** @type {Object} */
    completed_by;
    /** @type {string} */
    date_done;
    /** @type {string} */
    icon;
    /** @type {number} */
    id;
    /** @type {string} */
    res_model;
    /** @type {number} */
    res_id;
    /** @type {string} */
    summary;
}

CompletedActivity.register();
