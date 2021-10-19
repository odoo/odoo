/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;
const favoriteMenuRegistry = registry.category("favoriteMenu");

/**
 * 'Add to Google spreadsheet' menu item
 *
 * Component consisting only of a button calling the server to add the current
 * view to the user's spreadsheet configuration.
 * This component is only available in actions of type 'ir.actions.act_window'.
 * @extends Component
 */
export class AddToGoogleSpreadsheet extends Component {
    setup() {
        this.orm = useService("orm");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    async addToGoogleSpreadsheet() {
        const { domain, groupBy, resModel, view } = this.env.searchModel;

        const result = await this.orm.call(
            "google.drive.config",
            "set_spreadsheet",
            [resModel, domain, groupBy, view.id]
        );

        if (result.url) {
            // According to MDN doc, one should not use _blank as title.
            // todo: find a good name for the new window
            window.open(result.url, "_blank");
        }
    }
}

AddToGoogleSpreadsheet.template = "google_spreadsheet.AddToGoogleSpreadsheet";

const addToGoogleSpreadsheetItem = {
    Component: AddToGoogleSpreadsheet,
    groupNumber: 4,
    isDisplayed: ({ config }) => config.actionType === "ir.actions.act_window",
};

favoriteMenuRegistry.add("add-to-google-spreadsheet", addToGoogleSpreadsheetItem, { sequence: 20 });
