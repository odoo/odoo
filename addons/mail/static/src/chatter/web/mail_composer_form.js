import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { toRaw, useEffect, useRef } from "@odoo/owl";
import { useCustomDropzone } from "@web/core/dropzone/dropzone_hook";
import { useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { MailAttachmentDropzone } from "@mail/core/common/mail_attachment_dropzone";

export class MailComposerFormController extends formView.Controller {
    setup() {
        super.setup();
        toRaw(this.env.dialogData).model = "mail.compose.message";
    }
}

export class MailComposerFormRenderer extends formView.Renderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        // Autofocus the visible editor in edition mode.
        this.root = useRef("compiled_view_root");
        useEffect((isInEdition, root) => {
            if (root && root.el && isInEdition && this.props.record.data.composition_comment_option !== "reply_all") {
                const element = root.el.querySelector(".note-editable[contenteditable]");
                if (element) {
                    element.focus();
                    document.dispatchEvent(new Event("selectionchange", {}));
                }
            }
        }, () => [
            this.props.record.isInEdition,
            this.root,
            this.props.record.resId
        ]);

        const getActiveMailThread = () => {
            const resIds = JSON.parse(this.props.record.data.res_ids);
            const thread = this.mailStore.Thread.insert({
                model: this.props.record.data.model,
                id: resIds[0],
            });
            return thread;
        };

        // Add file dropzone on full mail composer:
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.operations = useX2ManyCrud(() => {
            return this.props.record.data["attachment_ids"];
        }, true);

        useCustomDropzone(this.root, MailAttachmentDropzone, {
            /** @param {Event} event */
            onDrop: async event => {
                const thread = getActiveMailThread();
                for (const file of event.dataTransfer.files) {
                    const attachment = await this.attachmentUploadService.upload(thread, thread.composer, file);
                    await this.operations.saveRecord([attachment.id]);
                }
            }
        });

        /** @param {function} */
        const onCloseWizardModal = (callback) => {
            this.env.dialogData.dismiss = callback;
        };

        // Update the thread recipient lists:
        onCloseWizardModal(async () => {
            const thread = getActiveMailThread();
            const selectedPartnerIds = this.props.record.data.partner_ids.records.map(
                (partner) => partner.resId
            );
            const partners = await this.orm.searchRead(
                "res.partner",
                [["id", "in", selectedPartnerIds]],
                ["email", "id", "lang", "name"]
            );

            // Update the recipient lists:
            thread.suggestedRecipients = thread.suggestedRecipients.map((suggestedRecipient) => {
                const partner = partners.find(
                    (partner) =>
                        partner.id === suggestedRecipient.id ||
                        partner.email === suggestedRecipient.email
                );
                if (partner) {
                    return {
                        ...suggestedRecipient,
                        email: partner.email,
                        lang: partner.lang,
                        name: partner.name,
                        partner_id: partner.id,
                        persona: { type: "partner", id: partner.id },
                    };
                }
                return suggestedRecipient;
            });
            thread.additionalRecipients = thread.additionalRecipients.map((additionalRecipient) => {
                const partner = partners.find(
                    (partner) =>
                        partner.id === additionalRecipient.id ||
                        partner.email === additionalRecipient.email
                );
                if (partner) {
                    return {
                        ...additionalRecipient,
                        email: partner.email,
                        lang: partner.lang,
                        name: partner.name,
                        partner_id: partner.id,
                        persona: { type: "partner", id: partner.id },
                    };
                }
                return additionalRecipient;
            });

            // Remove the recipients that got removed from the composer:
            thread.suggestedRecipients = thread.suggestedRecipients.filter((suggestedRecipient) =>
                selectedPartnerIds.includes(suggestedRecipient.partner_id)
            );
            thread.additionalRecipients = thread.additionalRecipients.filter(
                (additionalRecipient) => selectedPartnerIds.includes(additionalRecipient.partner_id)
            );

            // Add the recipients that got added to the composer:
            for (const partner of partners) {
                const allRecipients = [
                    ...thread.suggestedRecipients,
                    ...thread.additionalRecipients,
                ];
                if (allRecipients.every((recipient) => recipient.partner_id !== partner.id)) {
                    thread.additionalRecipients.push({
                        email: partner.email,
                        lang: partner.lang,
                        name: partner.name,
                        partner_id: partner.id,
                        persona: { type: "partner", id: partner.id },
                    });
                }
            }
        });
    }
}

registry.category("views").add("mail_composer_form", {
    ...formView,
    Controller: MailComposerFormController,
    Renderer: MailComposerFormRenderer,
});
