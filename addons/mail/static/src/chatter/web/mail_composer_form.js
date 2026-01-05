import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { EventBus, toRaw, useEffect, useRef, useSubEnv } from "@odoo/owl";
import { useCustomDropzone } from "@web/core/dropzone/dropzone_hook";
import { useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { MailAttachmentDropzone } from "@mail/core/common/mail_attachment_dropzone";

export class MailComposerFormController extends formView.Controller {
    static props = {
        ...formView.Controller.props,
        fullComposerBus: { type: EventBus, optional: true },
    };
    static defaultProps = { fullComposerBus: new EventBus() };
    setup() {
        super.setup();
        toRaw(this.env.dialogData).model = "mail.compose.message";
        useSubEnv({
            fullComposerBus: this.props.fullComposerBus,
        });
    }
}

export class MailComposerFormRenderer extends formView.Renderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        // Autofocus the visible editor in edition mode.
        this.root = useRef("compiled_view_root");
        useEffect(
            (isInEdition, el) => {
                if (
                    el &&
                    isInEdition &&
                    this.props.record.data.composition_comment_option === "reply_all"
                ) {
                    const element = el.querySelector(".note-editable[contenteditable]");
                    if (element) {
                        element.focus();
                        document.dispatchEvent(new Event("selectionchange", {}));
                    }
                }
            },
            () => [this.props.record.isInEdition, this.root.el, this.props.record.resId]
        );

        const getActiveMailThreads = () =>
            JSON.parse(this.props.record.data.res_ids).map((resId) => {
                const thread = this.mailStore.Thread.insert({
                    model: this.props.record.data.model,
                    id: resId,
                });
                return thread;
            });

        // Add file dropzone on full mail composer:
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.operations = useX2ManyCrud(() => this.props.record.data["attachment_ids"], true);

        useCustomDropzone(this.root, MailAttachmentDropzone, {
            /** @param {Event} event */
            onDrop: async (event) => {
                for (const thread of getActiveMailThreads()) {
                    for (const file of event.dataTransfer.files) {
                        const attachment = await this.attachmentUploadService.upload(
                            thread,
                            thread.composer,
                            file
                        );
                        await this.operations.saveRecord([attachment.id]);
                    }
                }
            },
        });

        /** @param {function} */
        const onCloseWizardModal = (callback) => {
            this.env.dialogData.dismiss = callback;
        };

        onCloseWizardModal(async () => {
            const selectedPartnerIds = this.props.record.data.partner_ids.currentIds;
            const selectedPartners = await this.orm.searchRead(
                "res.partner",
                [["id", "in", selectedPartnerIds]],
                ["email", "id", "lang", "name"]
            );

            /**
             * @param {SuggestedRecipient} recipient
             * @returns {SuggestedRecipient}
             */
            const updateRecipientWithCorrespondingPartner = (recipient) => {
                const partner = selectedPartners.find(
                    (partner) => partner.id === recipient.id || partner.email === recipient.email
                );
                if (partner) {
                    return {
                        ...recipient,
                        email: partner.email,
                        lang: partner.lang,
                        name: partner.name,
                        partner_id: partner.id,
                    };
                }
                return recipient;
            };

            /**
             * @param {SuggestedRecipient} recipient
             * @returns {boolean}
             */
            const isRecipientSelectedFromFullMailComposer = (recipient) =>
                selectedPartnerIds.includes(recipient.partner_id);

            for (const thread of getActiveMailThreads()) {
                // Update the recipient lists:
                thread.suggestedRecipients = thread.suggestedRecipients.map(
                    updateRecipientWithCorrespondingPartner
                );
                thread.additionalRecipients = thread.additionalRecipients.map(
                    updateRecipientWithCorrespondingPartner
                );

                // Remove the recipients that got removed from the composer:
                thread.suggestedRecipients = thread.suggestedRecipients.filter(
                    isRecipientSelectedFromFullMailComposer
                );
                thread.additionalRecipients = thread.additionalRecipients.filter(
                    isRecipientSelectedFromFullMailComposer
                );

                // Add the recipients that got added to the composer:
                for (const partner of selectedPartners) {
                    const allRecipients = [
                        ...thread.suggestedRecipients,
                        ...thread.additionalRecipients,
                    ];
                    if (!allRecipients.some((recipient) => recipient.partner_id === partner.id)) {
                        thread.additionalRecipients.push({
                            display_name: partner.display_name,
                            email: partner.email,
                            lang: partner.lang,
                            name: partner.name,
                            partner_id: partner.id,
                        });
                    }
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
