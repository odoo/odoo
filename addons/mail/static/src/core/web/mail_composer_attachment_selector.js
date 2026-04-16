import { dataUrlToBlob } from "@mail/core/common/attachment_uploader_hook";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";

import { Component, onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { FileUploader } from "@web/views/fields/file_handler";

export class MailComposerAttachmentSelector extends Component {
    static template = "mail.MailComposerAttachmentSelector";
    static components = { FileUploader };
    static props = {
        ...standardFieldProps,
        maxEmailSizeField: { type: String, optional: true },
    };

    setup() {
        this.mailStore = useService("mail.store");
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.operations = useX2ManyCrud(() => this.props.record.data["attachment_ids"], true);
        // Turn attachments into links if needed when opening the composer.
        onMounted(() => {
            // The delay is required for the html-editor to be ready to receive the event that does the work.
            setTimeout(this.inlineAttachmentIfNeeded.bind(this), 1000);
        });
    }

    /** @param {Object} data */
    async onFileUploaded({ data, name, type }) {
        let resIds;
        if (this.props.record.resModel === "mail.scheduled.message") {
            resIds = [this.props.record.data.res_id.resId];
        } else {
            // composer does not store res_ids past a certain limit, assume active_ids is used
            resIds = this.props.record.data.res_ids
                ? JSON.parse(this.props.record.data.res_ids)
                : this.props.record.context.active_ids;
        }
        const thread = await this.mailStore["mail.thread"].insert({
            model: this.props.record.data.model || this.props.record.context.active_model,
            id: resIds[0],
        });
        const file = new File([dataUrlToBlob(data, type)], name, { type });
        const attachment = await this.attachmentUploadService.upload(thread, thread.composer, file);
        if (attachment) {
            await this.operations.saveRecord([attachment.id]);
        }
    }

    /**
     * Turn attachments into link if the mail exceeds the configured maximum size (if provided).
     *
     * Note that this method emits the ADD_INLINE_ATTACHMENTS events to turn the attachments into links.
     */
    inlineAttachmentIfNeeded() {
        const maxEmailSize =
            this.props.maxEmailSizeField && this.props.record.data[this.props.maxEmailSizeField];
        if (!maxEmailSize) {
            return;
        }
        const totalSize = this.props.record.data.attachment_ids.records
            .map((a) => a.data.file_size)
            .reduce((acc, current) => acc + current, 0);
        // The server estimate not only the attachment size but also the content, see mail_mail._estimate_email_size
        const emailOverhead = 100 * 1024;
        if (totalSize + emailOverhead > maxEmailSize * 1024 * 1024) {
            this.env.fullComposerBus.trigger("ADD_INLINE_ATTACHMENTS", {
                attachments: this.props.record.data.attachment_ids.records,
                message: _t(
                    "Your attachments exceed %(maxSizeInMB)sMB and will be sent as secure links to ensure they reach your recipients",
                    {
                        maxSizeInMB: Math.round(maxEmailSize),
                    }
                ),
            });
        }
    }
}

export const mailComposerAttachmentSelector = {
    component: MailComposerAttachmentSelector,
    extractProps: (fieldInfo, _) => ({
        maxEmailSizeField: fieldInfo.options.max_email_size_field,
    }),
    relatedFields: () => {
        return [
            { name: "file_size", type: "integer", readOnly: true },
            { name: "id", type: "integer", readonly: true },
        ];
    },
};

registry
    .category("fields")
    .add("mail_composer_attachment_selector", mailComposerAttachmentSelector);
