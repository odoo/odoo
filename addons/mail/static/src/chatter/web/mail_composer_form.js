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
    setup() {
        super.setup();
        toRaw(this.env.dialogData).model = "mail.compose.message";
        if (this.props.fullComposerBus) {
            useSubEnv({
                fullComposerBus: this.props.fullComposerBus,
            });
        }
    }
}

export class MailComposerFormRenderer extends formView.Renderer {
    setup() {
        super.setup();
        // Autofocus the visible editor in edition mode.
        this.root = useRef("compiled_view_root");
        useEffect((isInEdition, root) => {
            if (root && root.el && isInEdition) {
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

        // Add file dropzone on full mail composer:
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.operations = useX2ManyCrud(() => {
            return this.props.record.data["attachment_ids"];
        }, true);

        useCustomDropzone(this.root, MailAttachmentDropzone, {
            /** @param {Event} event */
            onDrop: async event => {
                const resIds = JSON.parse(this.props.record.data.res_ids);
                const thread = await this.mailStore.Thread.insert({
                    model: this.props.record.data.model,
                    id: resIds[0],
                });
                for (const file of event.dataTransfer.files) {
                    const attachment = await this.attachmentUploadService.upload(thread, thread.composer, file);
                    await this.operations.saveRecord([attachment.id]);
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
