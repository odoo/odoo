/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { omit } from "@web/core/utils/objects";
import { useService } from "@web/core/utils/hooks";

import { useState } from "@odoo/owl";

export class SpreadsheetCloneXlsxDialog extends ConfirmationDialog {
    static template = "documents_spreadsheet.SpreadsheetCloneXlsxDialog";
    static props = {
        ...omit(ConfirmationDialog.props, "body", "confirm"),
        documentId: { type: Number },
    };

    setup() {
        super.setup();
        this.archiveDocumentState = useState({ willArchive: true });
        this.action = useService("action");
        this.orm = useService("orm");
    }
    /**
     * @override
     */
    async _confirm() {
        this.execButton(async () => {
            // Replacing call to a props-provided `confirm` method with the
            // archiving behavior makes a more unified component.
            const spreadsheetId = await this.orm.call(
                "documents.document",
                "clone_xlsx_into_spreadsheet",
                [this.props.documentId],
                { archive_source: this.archiveDocumentState.willArchive }
            );
            this.action.doAction({
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    spreadsheet_id: spreadsheetId,
                },
            });
        });
    }
}
