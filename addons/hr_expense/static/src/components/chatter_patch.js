import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { isDragSourceExternalFile } from "@mail/utils/common/misc";
import { useCustomDropzone } from "@web/core/dropzone/dropzone_hook";
import { MailAttachmentDropzone } from "@mail/core/common/mail_attachment_dropzone";

/**
 * Patch Chatter to add custom logic before the onDrop event.
 */
patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.props.record?.resModel === 'hr.expense') {
            useCustomDropzone(this.rootRef, MailAttachmentDropzone, {
                extraClass: "o-mail-Chatter-dropzone",
                /** @param {Event} ev */
                onDrop: async (ev) => {
                    if (this.state.composerType) {
                        return;
                    }

                    if (isDragSourceExternalFile(ev.dataTransfer)) {
                        const files = [...ev.dataTransfer.files];
                        if (!this.state.thread.id) {

                            // custom code to automatically fill the name because it is a required field
                            if (this.props.record.data.name === "") {
                                const untitled_expense = await this.orm.call('hr.expense', 'get_untitled_expense_name', [], {});
                                await this.props.record.update({ 'name': untitled_expense });
                            }

                            const saved = await this.props.saveRecord?.();
                            if (!saved) {
                                return;
                            }
                        }
                        Promise.all(files.map((file) => this.attachmentUploader.uploadFile(file))).then(
                            () => {
                                if (this.props.hasParentReloadOnAttachmentsChanged) {
                                    this.reloadParentView();
                                }
                            }
                        );
                        this.state.isAttachmentBoxOpened = true;
                    }
                },
            });
        }
    },
});