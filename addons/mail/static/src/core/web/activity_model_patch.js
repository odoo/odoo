import { Activity } from "@mail/core/common/activity_model";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    setup() {
        super.setup(...arguments);
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
        await new Promise((resolve) =>
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
                        dialog_size: "large",
                    },
                },
                {
                    onClose: resolve,
                }
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
    /** @returns {Promise<import("@web/webclient/actions/action_service").ActionDescription>} */
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
});
