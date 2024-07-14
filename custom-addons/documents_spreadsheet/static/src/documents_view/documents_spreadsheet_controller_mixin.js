/** @odoo-module **/

import { TemplateDialog } from "@documents_spreadsheet/spreadsheet_template/spreadsheet_template_dialog";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

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
        // Hack-ish way to do this but the function is added by a hook which we can't really override.
        this.baseOnOpenDocumentsPreview = this.onOpenDocumentsPreview.bind(this);
        this.onOpenDocumentsPreview = this._onOpenDocumentsPreview.bind(this);
    },

    /**
     * @override
     */
    documentsViewHelpers() {
        return {
            ...super.documentsViewHelpers(),
            sharePopupAction: this.sharePopupAction.bind(this),
        };
    },

    async sharePopupAction(documentShareVals) {
        const selection = this.env.model.root.selection;
        const documents = selection.length ? selection : this.env.model.root.records;
        if (
            this.env.model.useSampleModel ||
            documents.every((doc) => doc.data.handler !== "spreadsheet")
        ) {
            return documentShareVals;
        }
        const spreadsheetShares = [];
        for (const doc of documents) {
            if (doc.data.handler === "spreadsheet") {
                const resId = doc.resId;
                await loadBundle("spreadsheet.o_spreadsheet");
                const { fetchSpreadsheetModel, freezeOdooData } = odoo.loader.modules.get("@spreadsheet/helpers/model");
                const model = await fetchSpreadsheetModel(this.env, "documents.document", resId);
                const data = await freezeOdooData(model);
                spreadsheetShares.push({
                    spreadsheet_data: JSON.stringify(data),
                    excel_files: model.exportXLSX().files,
                    document_id: resId,
                });
            }
        }
        return {
            ...documentShareVals,
            spreadsheet_shares: spreadsheetShares,
        };
    },

    /**
     * @override
     */
    async _onOpenDocumentsPreview({ mainDocument }) {
        if (mainDocument.data.handler === "spreadsheet") {
            this.action.doAction({
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    spreadsheet_id: mainDocument.resId,
                },
            });
        } else if (XLSX_MIME_TYPES.includes(mainDocument.data.mimetype)) {
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
                        this.env.searchModel.toggleCategoryValue(1, mainDocument.data.folder_id[0]);
                    },
                    confirmLabel: _t("Restore"),
                });
            } else {
                this.dialogService.add(SpreadsheetCloneXlsxDialog, {
                    title: _t("Format issue"),
                    cancel: () => {},
                    cancelLabel: _t("Discard"),
                    documentId: mainDocument.resId,
                    confirmLabel: _t("Open with Odoo Spreadsheet"),
                });
            }
        } else {
            return this.baseOnOpenDocumentsPreview(...arguments);
        }
    },

    async onClickCreateSpreadsheet(ev) {
        this.dialogService.add(TemplateDialog, {
            folderId: this.env.searchModel.getSelectedFolderId() || undefined,
            context: this.props.context,
            folders: this.env.searchModel
                .getFolders()
                .filter((folder) => folder.id && folder.id !== "TRASH"),
        });
    },
});
