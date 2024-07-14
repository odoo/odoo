/** @odoo-module */
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { registry } from "@web/core/registry";
import {SpreadsheetComponent} from "@spreadsheet_edition/bundle/actions/spreadsheet_component";
import { SpreadsheetControlPanel } from "@spreadsheet_edition/bundle/actions/control_panel/spreadsheet_control_panel";

import { useSubEnv } from "@odoo/owl";

export class SpreadsheetTestAction extends AbstractSpreadsheetAction {
    resModel = "spreadsheet.test";

    setup() {
        super.setup();
        useSubEnv({
            showHistory: this.showHistory.bind(this),
        });
    }
}

SpreadsheetTestAction.template = "test_spreadsheet_edition.SpreadsheetTestAction";
SpreadsheetTestAction.components = {
    SpreadsheetControlPanel,
    SpreadsheetComponent,
};

registry.category("actions").add("spreadsheet_test_action", SpreadsheetTestAction, { force: true });
