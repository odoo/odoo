import { patch } from "@web/core/utils/patch";
import { MailAttachments } from "@account/components/mail_attachments/mail_attachments_selector";
import { useService } from "@web/core/utils/hooks";
import { SelectAddDocumentCreateDialog } from "@documents/views/view_dialogs/select_add_document_create_dialog";

patch(MailAttachments.prototype, {

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    },

    openDocumentsDialog() {
        const data = this.props.record.data;
        const resId = JSON.parse(data.res_ids || "[]")[0];

        const closeDocumentsDialog = this.dialog.add(SelectAddDocumentCreateDialog, {
            resModel: "documents.document",
            title: "Search: Documents",
            noCreate: true,
            domain: [
                ["type", "=", "binary"],
                ["shortcut_document_id", "=", false],
            ],
            context: {
                list_view_ref: "documents.documents_view_list_add_documents_attachment",
                documents_search_panel_no_trash: true,
                documents_view_secondary: true,
            },

            chatterParams: {
                thread: {
                    model: data.model,
                    id: resId,
                },

                composer: {
                    attachments: this.attachments,
                    composerText: this.props.record.data.body || "",
                },

                pasteDocumentsLink: async (resIds) => {

                    const records = await this.orm.read(
                        "documents.document",
                        resIds,
                        ["display_name", "access_url"]
                    );

                    const linksHtml = records
                        .map(r => `<a href="${r.access_url}" target="_blank">${r.display_name}</a>`)
                        .join("<br/>");

                    const appendedHtml = `<p><br/><strong>Attached Documents:</strong><br/>${linksHtml}</p>`;

                    const currentBody = this.props.record.data.body || "";
                    const newBody = currentBody + appendedHtml;

                    await this.props.record.update({
                        body: newBody,
                    });

                    closeDocumentsDialog();
                },
            },
        });
    },

});
