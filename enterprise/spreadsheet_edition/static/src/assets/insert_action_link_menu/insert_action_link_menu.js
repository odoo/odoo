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
    static props = {};
    static template = "spreadsheet_edition.InsertActionSpreadsheet";
    static components = { DropdownItem };

    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.dialogManager = useService("dialog");
    }

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    async linkInSpreadsheet() {
        const actionToLink = await this.getViewDescription();
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

    async getViewDescription() {
        const { resModel } = this.env.searchModel;
        const { views = [], actionId, viewType } = this.env.config;
        const { xml_id } = actionId
            ? await this.actionService.loadAction(actionId, this.env.searchModel.context)
            : {};
        const { context } = this.env.searchModel.getIrFilterValues();
        const action = {
            xmlId: xml_id,
            domain: this.env.searchModel.domain,
            context,
            modelName: resModel,
            // prevent navigation to other views as we have a dedicated domain/context
            views: views.map(([, type]) => [false, type]),
        };
        return {
            viewType,
            action,
        };
    }
}
