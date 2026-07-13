import { Activity } from "@mail/core/common/activity_model";
import { dataUrlToBlob } from "@mail/core/common/attachment_uploader_hook";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

import { isEmptyBlock } from "@html_editor/utils/dom_info";

import { createElementWithContent } from "@web/core/utils/html";
import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    setup() {
        super.setup(...arguments);
        this.isNoteEmpty = this.computed(
            () => !this.note || isEmptyBlock(createElementWithContent("div", this.note))
        );
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
                        dialog_size: "medium",
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
    /**
     * Upload the files on the record of the activity, then mark it as done with them.
     *
     * @param {{ data: string, name: string, type: string }[]} uploadDatas data given by the FileUploader
     */
    async uploadAndMarkAsDone(uploadDatas) {
        const thread = this.store["mail.thread"].insert({ model: this.res_model, id: this.res_id });
        const uploadService = this.store.env.services["mail.attachment_upload"];
        const attachments = await Promise.all(
            uploadDatas.map(({ data, name, type }) =>
                uploadService.upload(
                    thread,
                    undefined,
                    new File([dataUrlToBlob(data, type)], name, { type }),
                    { activity: this }
                )
            )
        );
        const validAttachments = attachments.filter(Boolean);
        if (validAttachments.length > 0) {
            await this.markAsDone(validAttachments.map(({ id }) => id));
            if (validAttachments.length < uploadDatas.length) {
                this.store.env.services.notification.add(
                    _t("The activity was marked as done, but some files failed to upload."),
                    { type: "warning" }
                );
            }
        }
        return validAttachments.length > 0;
    },
    /** @returns {Promise<import("@web/webclient/actions/action_plugin").ActionDescription>} */
    async markAsDoneAndScheduleNext() {
        const action = await this.store.env.services.orm.call(
            "mail.activity",
            "action_feedback_schedule_next",
            [[this.id]],
            { feedback: this.feedback }
        );
        this.store.activityBroadcastChannel?.postMessage({
            type: "RELOAD_CHATTER",
            payload: { id: this.res_id, model: this.res_model },
        });
        return action;
    },
    remove({ broadcast = true } = {}) {
        if (!this.exists()) {
            return;
        }
        this.delete();
        if (broadcast) {
            this.store.activityBroadcastChannel?.postMessage({
                type: "DELETE",
                payload: { id: this.id },
            });
        }
    },
});
