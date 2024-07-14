/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

import { SpreadsheetComponent } from "@spreadsheet_edition/bundle/actions/spreadsheet_component";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { DocumentsSpreadsheetControlPanel } from "@documents_spreadsheet/bundle/components/control_panel/spreadsheet_control_panel";
import { useSubEnv } from "@odoo/owl";

export class SpreadsheetTemplateAction extends AbstractSpreadsheetAction {
    resModel = "spreadsheet.template";

    setup() {
        super.setup();
        this.notificationMessage = _t("New spreadsheet template created");
        useSubEnv({
            newSpreadsheet: this.createNewSpreadsheet.bind(this),
            makeCopy: this.makeCopy.bind(this),
        });
    }

    createModel() {
        super.createModel();
        this.model.dispatch("SET_FORMULA_VISIBILITY", { show: true });
    }

    /**
     * Create a new empty spreadsheet template
     * @returns {number} id of the newly created spreadsheet template
     */
    async createNewSpreadsheet() {
        const data = {
            name: _t("Untitled spreadsheet template"),
        };
        const id = await this.orm.create("spreadsheet.template", [data]);
        this._openSpreadsheet(id);
        return id;
    }

    /**
     * Save a new name for the given template
     * @param {Object} detail
     * @param {string} detail.name
     */
    async _onSpreadSheetNameChanged(detail) {
        await super._onSpreadSheetNameChanged(detail);
        const { name } = detail;
        await this.orm.write("spreadsheet.template", [this.resId], {
            name,
        });
    }
}

SpreadsheetTemplateAction.template = "documents_spreadsheet.SpreadsheetTemplateAction";
SpreadsheetTemplateAction.components = {
    SpreadsheetComponent,
    DocumentsSpreadsheetControlPanel,
};

registry
    .category("actions")
    .add("action_open_template", SpreadsheetTemplateAction, { force: true });
