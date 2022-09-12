/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";

const { Component } = owl;
const favoriteMenuRegistry = registry.category("favoriteMenu");
import { Dialog } from '@web/core/dialog/dialog';

export class GoogleSpreadsheetDialog extends Dialog {}
GoogleSpreadsheetDialog.bodyTemplate = 'google_spreadsheet.FormulaDialogOwl';

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
        this.dialog = useService("dialog");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    async addToGoogleSpreadsheet() {
        const { domain, groupBy, resModel, view } = this.env.searchModel;
        const viewId = view ? view.id : false;
        const domainAsString = (new Domain(domain)).toString();

        const result = await this.env.services.orm.call(
            "google.drive.config",
            "set_spreadsheet",
            [resModel, domainAsString, groupBy, viewId]
        );

        if (result.deprecated) {
            this.dialog.add(GoogleSpreadsheetDialog, {
                url: result.url,
                formula: result.formula,
            });
            return;
        }
        if (result.url) {
            // According to MDN doc, one should not use _blank as title.
            // todo: find a good name for the new window
            window.open(result.url, "_blank");
        }
    }
}

AddToGoogleSpreadsheet.template = "google_spreadsheet.AddToGoogleSpreadsheet";
AddToGoogleSpreadsheet.components = { DropdownItem };

const addToGoogleSpreadsheetItem = {
    Component: AddToGoogleSpreadsheet,
    groupNumber: 4,
    isDisplayed: ({ config }) => config.actionType === "ir.actions.act_window",
};

favoriteMenuRegistry.add("add-to-google-spreadsheet", addToGoogleSpreadsheetItem, { sequence: 20 });
