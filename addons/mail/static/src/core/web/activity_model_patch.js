import { Activity } from "@mail/core/common/activity_model";
import { Record } from "@mail/core/common/record";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {boolean} */
        this.active;
        /** @type {string} */
        this.activity_category;
        /** @type {[number, string]} */
        this.activity_type_id;
        /** @type {string|false} */
        this.activity_decoration;
        /** @type {Object[]} */
        this.attachment_ids;
        /** @type {boolean} */
        this.can_write;
        /** @type {'suggest'|'trigger'} */
        this.chaining_type;
        /** @type {luxon.DateTime} */
        this.create_date = Record.attr(undefined, { type: "datetime" });
        /** @type {[number, string]} */
        this.create_uid;
        /** @type {luxon.DateTime} */
        this.date_deadline = Record.attr(undefined, { type: "date" });
        /** @type {luxon.DateTime} */
        this.date_done = Record.attr(undefined, { type: "date" });
        /** @type {string} */
        this.display_name;
        /** @type {boolean} */
        this.has_recommended_activities;
        /** @type {string} */
        this.feedback;
        /** @type {string} */
        this.icon = "fa-tasks";
        /** @type {Object[]} */
        this.mail_template_ids;
        this.note = Record.attr("", { html: true });
        this.persona = Record.one("Persona");
        /** @type {number|false} */
        this.previous_activity_type_id;
        /** @type {number|false} */
        this.recommended_activity_type_id;
        /** @type {string} */
        this.res_model;
        /** @type {[number, string]} */
        this.res_model_id;
        /** @type {number} */
        this.res_id;
        /** @type {string} */
        this.res_name;
        /** @type {number|false} */
        this.request_partner_id;
        /** @type {'overdue'|'planned'|'today'} */
        this.state;
        /** @type {string} */
        this.summary;
        /** @type {[number, string]} */
        this.user_id;
        /** @type {string} */
        this.write_date;
        /** @type {[number, string]} */
        this.write_uid;
    },
    get dateDeadlineFormatted() {
        return formatDate(this.date_deadline);
    },
    get dateDoneFormatted() {
        return formatDate(this.date_done);
    },
    get dateCreateFormatted() {
        return formatDateTime(this.create_date);
    },
    async edit() {
        return new Promise((resolve) =>
            this.store.env.services.action.doAction(
                {
                    type: "ir.actions.act_window",
                    name: _t("Schedule Activity"),
                    res_model: "mail.activity",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    res_id: this.id,
                    context: {
                        default_res_model: this.res_model,
                        default_res_id: this.res_id,
                    },
                },
                { onClose: resolve }
            )
        );
    },
    /** @param {number[]} attachmentIds */
    async markAsDone(attachmentIds = []) {
        await this.store.env.services.orm.call("mail.activity", "action_feedback", [[this.id]], {
            attachment_ids: attachmentIds,
            feedback: this.feedback,
        });
        this.store.activityBroadcastChannel?.postMessage({
            type: "RELOAD_CHATTER",
            payload: { id: this.res_id, model: this.res_model },
        });
    },
    async markAsDoneAndScheduleNext() {
        const action = await this.store.env.services.orm.call(
            "mail.activity",
            "action_feedback_schedule_next",
            [[this.id]],
            { feedback: this.feedback }
        );
        this.activityBroadcastChannel?.postMessage({
            type: "RELOAD_CHATTER",
            payload: { id: this.res_id, model: this.res_model },
        });
        return action;
    },
    remove({ broadcast = true } = {}) {
        this.delete();
        if (broadcast) {
            this.activityBroadcastChannel?.postMessage({
                type: "DELETE",
                payload: { id: this.id },
            });
        }
    },
    serialize() {
        return JSON.parse(JSON.stringify(this.toData()));
    },
});
