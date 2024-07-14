/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { SpreadsheetSelectorDialog } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_dialog";

import { Component } from "@odoo/owl";

/**
 * Insert a link to a view in spreadsheet
 * @extends Component
 */
export class InsertViewSpreadsheet extends Component {
    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.dialogManager = useService("dialog");
    }

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    linkInSpreadsheet() {
        const actionToLink = this.getViewDescription();
        // do action with action link
        const actionOptions = {
            preProcessingAction: "insertLink",
            preProcessingActionData: actionToLink,
        };

        this.dialogManager.add(SpreadsheetSelectorDialog, {
            type: "LINK",
            actionOptions,
            name: this.env.config.getDisplayName(),
        });
    }

    getViewDescription() {
        const { resModel } = this.env.searchModel;
        const { views = [] } = this.env.config;
        const { context } = this.env.searchModel.getIrFilterValues();
        const action = {
            domain: this.env.searchModel.domain,
            context,
            modelName: resModel,
            views: views.map(([, type]) => [false, type]),
        };
        return {
            viewType: this.env.config.viewType,
            action,
        };
    }
}

InsertViewSpreadsheet.props = {};
InsertViewSpreadsheet.template = "spreadsheet_edition.InsertActionSpreadsheet";
InsertViewSpreadsheet.components = { DropdownItem };
