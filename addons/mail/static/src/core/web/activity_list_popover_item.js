/* @odoo-module */

import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { computeDelay } from "@mail/utils/common/dates";

import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { FileUploader } from "@web/views/fields/file_handler";

/**
 * @typedef {Object} Props
 * @property {import("models").Activity} activity
 * @property {function} onActivityChanged
 * @property {function} [onClickDoneAndScheduleNext]
 * @property {function} onClickEditActivityButton
 * @extends {Component<Props, Env>}
 */
export class ActivityListPopoverItem extends Component {
    static components = { ActivityMailTemplate, ActivityMarkAsDone, FileUploader };
    static props = [
        "activity",
        "onActivityChanged?",
        "onClickDoneAndScheduleNext?",
        "onClickEditActivityButton?",
    ];
    static template = "mail.ActivityListPopoverItem";

    setup() {
        this.user = useService("user");
        this.state = useState({ hasMarkDoneView: false });
        if (this.props.activity.activity_category === "upload_file") {
            this.attachmentUploader = useAttachmentUploader(
                this.env.services["mail.thread"].getThread(
                    this.props.activity.res_model,
                    this.props.activity.res_id
                )
            );
        }
        this.closeMarkAsDone = this.closeMarkAsDone.bind(this);
    }

    closeMarkAsDone() {
        this.state.hasMarkDoneView = false;
    }

    get delayLabel() {
        const diff = computeDelay(this.props.activity.date_deadline);
        if (diff === 0) {
            return _t("Today");
        } else if (diff === -1) {
            return _t("Yesterday");
        } else if (diff < 0) {
            return _t("%s days overdue", Math.round(Math.abs(diff)));
        } else if (diff === 1) {
            return _t("Tomorrow");
        } else {
            return _t("Due in %s days", Math.round(Math.abs(diff)));
        }
    }

    get hasEditButton() {
        const activity = this.props.activity;
        return (
            activity.state !== "done" && activity.chaining_type === "suggest" && activity.can_write
        );
    }

    get hasFileUploader() {
        const activity = this.props.activity;
        return activity.state !== "done" && activity.activity_category === "upload_file";
    }

    get hasMarkDoneButton() {
        return this.props.activity.state !== "done" && !this.hasFileUploader;
    }

    onClickEditActivityButton() {
        this.props.onClickEditActivityButton();
        this.env.services["mail.activity"]
            .edit(this.props.activity.id)
            .then(() => this.props.onActivityChanged());
    }

    onClickMarkAsDone() {
        this.state.hasMarkDoneView = !this.state.hasMarkDoneView;
    }

    async onFileUploaded(data) {
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data);
        await this.env.services["mail.activity"].markAsDone(this.props.activity, [attachmentId]);
        this.props.onActivityChanged();
    }

    get activityAssigneeAvatar() {
        return url("/web/image", {
            field: "avatar_128",
            id: this.props.activity.user_id[0],
            model: "res.users",
        });
    }

    get dateDeadlineFormatted() {
        return luxon.DateTime.fromISO(this.props.activity.date_deadline).toLocaleString(
            luxon.DateTime.DATE_SHORT
        );
    }

    get dateDoneFormatted() {
        return luxon.DateTime.fromISO(this.props.activity.date_done).toLocaleString(
            luxon.DateTime.DATE_SHORT
        );
    }
}
