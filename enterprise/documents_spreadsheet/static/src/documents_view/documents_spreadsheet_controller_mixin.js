/** @odoo-module **/

import { TemplateDialog } from "@documents_spreadsheet/spreadsheet_template/spreadsheet_template_dialog";
import { useService } from "@web/core/utils/hooks";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { SpreadsheetCloneXlsxDialog } from "@documents_spreadsheet/spreadsheet_clone_xlsx_dialog/spreadsheet_clone_xlsx_dialog";
import { _t } from "@web/core/l10n/translation";

import { XLSX_MIME_TYPES } from "@documents_spreadsheet/helpers";

export const DocumentsSpreadsheetControllerMixin = () => ({
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        // Hack-ish way to do this but the function is added by a hook which we can't really override.
        this.baseOnOpenDocumentsPreview = this.onOpenDocumentsPreview.bind(this);
        this.onOpenDocumentsPreview = this._onOpenDocumentsPreview.bind(this);
    },

    /**
     * Prevents spreadsheets from being in the viewable attachments list
     * when previewing a file in the FileViewer.
     *
     * @override
     */
    isRecordPreviewable(record) {
        return (
            super.isRecordPreviewable(...arguments) &&
            !["spreadsheet", "frozen_spreadsheet"].includes(record.data.handler)
        );
    },

    /**
     * @override
     */
    async _onOpenDocumentsPreview({ mainDocument }) {
        const mainDocumentOrTarget = mainDocument.shortcutTarget;
        if (["spreadsheet", "frozen_spreadsheet"].includes(mainDocumentOrTarget.data.handler)) {
            this.action.doAction({
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    spreadsheet_id: mainDocumentOrTarget.resId,
                },
            });
        } else if (XLSX_MIME_TYPES.includes(mainDocumentOrTarget.data.mimetype)) {
            // Keep MainDocument as `active` can be different for shortcut and target.
            if (!mainDocument.data.active) {
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Restore file?"),
                    body: _t(
                        "Spreadsheet files cannot be handled from the Trash. Would you like to restore this document?"
                    ),
                    cancel: () => {},
                    confirm: async () => {
                        await this.orm.call("documents.document", "action_unarchive", [
                            mainDocument.resId,
                        ]);
                        this.env.searchModel.toggleCategoryValue(
                            1,
                            mainDocument.data.folder_id[0] ?? false
                        );
                    },
                    confirmLabel: _t("Restore"),
                });
            } else if (this.documentService.userIsInternal) {
                this.dialogService.add(SpreadsheetCloneXlsxDialog, {
                    title: _t("Excel file preview"),
                    cancel: () => {},
                    cancelLabel: _t("Discard"),
                    documentId: mainDocumentOrTarget.resId,
                    confirmLabel: _t("Open with Odoo Spreadsheet"),
                });
            }
        } else {
            return this.baseOnOpenDocumentsPreview(...arguments);
        }
    },

    async onClickCreateSpreadsheet(ev) {
        const folderId = this.env.searchModel.getSelectedFolderId() || undefined;
        const context = this.props.context;
        if (folderId === "COMPANY") {
            context.default_owner_id = this.documentService.store.odoobot.userId;
        }
        this.dialogService.add(TemplateDialog, {
            folderId,
            context,
            folders: this.env.searchModel
                .getFolders()
                .filter((folder) => folder.id && typeof folder.id === "number"),
        });
    },
});
