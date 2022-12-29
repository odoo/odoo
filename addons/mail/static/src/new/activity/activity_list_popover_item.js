/* @odoo-module */

import { ActivityMailTemplate } from "@mail/new/activity/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/new/activity/activity_markasdone_popover";

import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { FileUploader } from "@web/views/fields/file_handler";

import { computeDelay } from "@mail/new/utils/dates";
import { useAttachmentUploader } from "@mail/new/attachments/attachment_uploader_hook";

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("./activity_model").Activity} activity
 * @property {function} onActivityChanged
 * @property {function} [onClickDoneAndScheduleNext]
 * @property {function} onClickEditActivityButton
 * @extends {Component<Props, Env>}
 */
export class ActivityListPopoverItem extends Component {
    static components = { ActivityMailTemplate, ActivityMarkAsDone, FileUploader };
    static props = [
        "activity",
        "onActivityChanged",
        "onClickDoneAndScheduleNext?",
        "onClickEditActivityButton",
    ];
    static template = "mail.ActivityListPopoverItem";

    setup() {
        this.user = useService("user");
        this.state = useState({ hasMarkDoneView: false });
        if (this.props.activity.activity_category === "upload_file") {
            this.attachmentUploader = useAttachmentUploader(
                this.env.services["mail.chatter"].getThread(
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
            return sprintf(_t("%s days overdue"), Math.round(Math.abs(diff)));
        } else if (diff === 1) {
            return _t("Tomorrow");
        } else {
            return sprintf(_t("Due in %s days"), Math.round(Math.abs(diff)));
        }
    }

    get hasEditButton() {
        return this.props.activity.chaining_type === "suggest" && this.props.activity.can_write;
    }

    get hasFileUploader() {
        return this.props.activity.activity_category === "upload_file";
    }

    get hasMarkDoneButton() {
        return !this.hasFileUploader;
    }

    onClickEditActivityButton() {
        this.props.onClickEditActivityButton();
        this.env.services["mail.activity"]
            .schedule(
                this.props.activity.res_model,
                this.props.activity.res_id,
                this.props.activity.id
            )
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
}
