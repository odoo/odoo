import { SpreadsheetSelectorPanel } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_panel";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class DocumentSelectorDialog extends Component {
    static template = "spreadsheet_dashboard_documents.DocumentSelectorDialog";
    static components = { Dialog, SpreadsheetSelectorPanel };
    static props = {
        close: Function,
        dashboardGroupId: Number,
    };

    setup() {
        this.selectedSpreadsheet = null;
        this.orm = useService("orm");
        this.actionService = useService("action");
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
