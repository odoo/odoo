/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { loadBundle } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import {
    inspectorFields,
    DocumentsInspector,
} from "@documents/views/inspector/documents_inspector";

import { XLSX_MIME_TYPES } from "@documents_spreadsheet/helpers";

inspectorFields.push("handler");

patch(DocumentsInspector.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    /**
     * @override
     */
    getRecordAdditionalData(record) {
        const result = super.getRecordAdditionalData(...arguments);
        result.isSheet = record.data.handler === "spreadsheet";
        result.isXlsx = XLSX_MIME_TYPES.includes(record.data.mimetype);
        return result;
    },

    /**
     * @override
     */
    getPreviewClasses(record, additionalData) {
        let result = super.getPreviewClasses(...arguments);
        if (additionalData.isSheet) {
            return result.replace("o_documents_preview_mimetype", "o_documents_preview_image");
        }
        if (additionalData.isXlsx) {
            result += " o_document_xlsx";
        }
        return result;
    },

    openSpreadsheet(record) {
        this.env.bus.trigger("documents-open-preview", {
            documents: [record],
            isPdfSplit: false,
            rules: [],
            hasPdfSplit: false,
        });
    },

    /**
     * @override
     */
    async onDownload() {
        const selection = this.props.documents || [];
        if (selection.some((record) => record.data.handler === "spreadsheet")) {
            if (selection.length === 1) {
                const record = await this.orm.call(
                    "documents.document",
                    "join_spreadsheet_session",
                    [selection[0].resId]
                );
                await this.action.doAction({
                    type: "ir.actions.client",
                    tag: "action_download_spreadsheet",
                    params: {
                        orm: this.orm,
                        name: record.name,
                        data: record.data,
                        stateUpdateMessages: record.revisions,
                    },
                });
            } else {
                this.notification.add(
                    _t(
                        "Spreadsheets mass download not yet supported.\n Download spreadsheets individually instead."
                    ),
                    {
                        sticky: false,
                        type: "danger",
                    }
                );
                const docs = selection.filter(
                    (doc) => doc.data.handler !== "spreadsheet" && doc.data.type !== "empty"
                );
                if (docs.length) {
                    this.download(selection.filter((rec) => rec.data.handler !== "spreadsheet"));
                }
            }
        } else {
            super.onDownload(...arguments);
        }
    },

    /**
     * @override
     */
    async createShareVals() {
        const selection = this.props.documents;
        const vals = await super.createShareVals();
        if (selection.every((doc) => doc.data.handler !== "spreadsheet")) {
            return vals;
        }
        await loadBundle("spreadsheet.o_spreadsheet");
        const spreadsheetShares = [];
        for (const document of selection) {
            if (document.data.handler === "spreadsheet") {
                const resId = document.resId;
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
            ...vals,
            spreadsheet_shares: spreadsheetShares,
        };
    },
});
