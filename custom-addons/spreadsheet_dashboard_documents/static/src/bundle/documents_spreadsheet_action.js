/** @odoo-module **/

import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
const { topbarMenuRegistry } = spreadsheet.registries;
import { useSubEnv } from "@odoo/owl";

topbarMenuRegistry.addChild("add_document_to_dashboard", ["file"], {
    name: _t("Add to dashboard"),
    sequence: 200,
    isVisible: (env) => env.canAddToDashboard?.(),
    execute: (env) => env.createDashboardFromDocument(env.model),
    icon: "o-spreadsheet-Icon.ADD_TO_DASHBOARD",
});

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

patch(SpreadsheetAction.prototype, {
    setup() {
        super.setup();
        useSubEnv({
            canAddToDashboard: () => this.canAddToDashboard,
            createDashboardFromDocument: this._createDashboardFromDocument.bind(this),
        });
    },

    /**
     * @override
     */
    _initializeWith(record) {
        super._initializeWith(record);
        this.canAddToDashboard = record.can_add_to_dashboard;
    },

    /**
     * @param {Model} model
     * @private
     */
    async _createDashboardFromDocument(model) {
        const resId = this.resId;
        const name = this.state.spreadsheetName;
        await this.env.services.orm.call("documents.document", "save_spreadsheet_snapshot", [
            resId,
            model.exportData(),
        ]);
        this.env.services.action.doAction(
            {
                name: _t("Name your dashboard and select its section"),
                type: "ir.actions.act_window",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                res_model: "spreadsheet.document.to.dashboard",
            },
            {
                additionalContext: {
                    default_document_id: resId,
                    default_name: name,
                },
            }
        );
    },
});
