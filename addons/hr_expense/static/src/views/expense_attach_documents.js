import { registry } from "@web/core/registry";
import { checkFileSize } from "@web/core/utils/files";
import { AttachDocumentWidget } from "@web/views/widgets/attach_document/attach_document";

export class ExpenseAttachDocumentWidget extends AttachDocumentWidget {
    async onInputChange() {
        const ufile = [...this.fileInput.files];
        for (const file of ufile) {
            if (!checkFileSize(file.size, this.notification)) {
                return null;
            }
        }
        const fileData = await this.http.post("/mail/attachment/upload", {
            csrf_token: odoo.csrf_token,
            ufile: ufile,
            thread_model: this.props.record.resModel,
            thread_id: this.props.record.resId,
        });
        if (fileData.error) {
            throw new Error(fileData.error);
        }
        await this.onFileUploaded(fileData.data["ir.attachment"] || []);
    }
}

export const attachDocumentWidget = {
    component: ExpenseAttachDocumentWidget,
    extractProps: ({ attrs }) => {
        const { action, highlight, string } = attrs;
        return {
            action,
            highlight: !!highlight,
            string,
        };
    },
};

registry.category("view_widgets").add("expense_attach_document", attachDocumentWidget);
