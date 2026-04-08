import { useChildSubEnv, useState } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";

export const ExpenseAttachmentPreviewMixin = (Base) => class extends Base {

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.mailPopoutService = useService("mail.popout");

        const saveHidden = localStorage.getItem(this.previewerStorageKey);

        this.attachmentPreviewState = useState({
            displayAttachment: saveHidden === null ? true : saveHidden === "true",
            selectedRecord: false,
            thread: null,
        });

        this.popout = useState({ active: false });
        useChildSubEnv({
            setPopout: this.setPopout.bind(this),
        });
    }

    get previewerStorageKey() {
        return "hr_expense.pdf_previewer_hidden";
    }

    get previewEnabled() {
        return true;
    }

    togglePreview() {
        this.attachmentPreviewState.displayAttachment = !this.attachmentPreviewState.displayAttachment;
        localStorage.setItem(
            this.previewerStorageKey,
            this.attachmentPreviewState.displayAttachment
        );
    }

    setPopout(value) {
        if (this.attachmentPreviewState.thread?.attachmentsInWebClientView.length) {
            this.popout.active = value;
        }
    }

    async setThread(lineData, attachmentField, modelField) {
        const attachments = lineData?.data[attachmentField]?.records || [];
        if (!lineData || !attachments.length) {
            this.attachmentPreviewState.thread = null;
            return;
        }
        const thread = this.store["mail.thread"].insert({
            attachments: attachments.map((attachment) => ({
                id: attachment.resId,
                mimetype: attachment.data.mimetype,
            })),
            id: lineData.data[modelField].id,
            model: lineData.fields[modelField].relation,
        });
        if (!thread.message_main_attachment_id && thread.attachmentsInWebClientView.length > 0) {
            thread.update({ message_main_attachment_id: thread.attachmentsInWebClientView[0] });
        }
        this.attachmentPreviewState.thread = thread;
    }
};
