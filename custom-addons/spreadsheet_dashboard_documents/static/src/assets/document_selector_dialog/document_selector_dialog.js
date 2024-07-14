/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { DocumentsSelectorPanel } from "@documents_spreadsheet/spreadsheet_selector_dialog/document_selector_panel";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class DocumentSelectorDialog extends Component {
    setup() {
        this.selectedSpreadsheet = null;
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.title = _t("Create a Dashboard or select a Spreadsheet");
    }

    onSpreadsheetSelected({ spreadsheet }) {
        this.selectedSpreadsheet = spreadsheet;
    }

    async _confirm() {
        if (this.selectedSpreadsheet) {
            await this.orm.call("spreadsheet.dashboard", "add_document_spreadsheet_to_dashboard", [
                this.props.dashboardGroupId,
                this.selectedSpreadsheet.id,
            ]);
            // Reload the view
            this.actionService.switchView("form", {
                resId: this.props.dashboardGroupId,
            });
        } else {
            const action = await this.orm.call(
                "spreadsheet.dashboard",
                "action_open_new_dashboard",
                [this.props.dashboardGroupId]
            );
            // open the new dashboard
            this.actionService.doAction(action, { clear_breadcrumbs: false });
        }
        this.props.close();
    }

    _cancel() {
        this.props.close();
    }
}

DocumentSelectorDialog.template = "spreadsheet_dashboard_documents.DocumentSelectorDialog";
DocumentSelectorDialog.components = { Dialog, DocumentsSelectorPanel };
DocumentSelectorDialog.props = {
    close: Function,
    dashboardGroupId: Number,
};
