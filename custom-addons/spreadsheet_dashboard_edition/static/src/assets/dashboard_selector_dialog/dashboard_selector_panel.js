/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { SpreadsheetSelectorDialog } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_dialog";
import { SpreadsheetSelectorPanel } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_panel";

class DashboardSelectorPanel extends SpreadsheetSelectorPanel {

    /**
     * Fetch spreadsheets according to the search domain and the pager
     * offset given as parameter.
     * @override
     * @returns {Promise<void>}
     */
    async _fetchSpreadsheets() {
        const { offset, limit } = this.state.pagerProps;
        this.state.spreadsheets = await this.keepLast.add(
            this.orm.searchRead("spreadsheet.dashboard", this.domain, ["name", "thumbnail"], {
                offset,
                limit,
            })
        );
        this._selectItem(this.state.spreadsheets.length && this.state.spreadsheets[0].id);
    }

    /**
     * @override
     * @returns {Promise<number>}
     */
    async _fetchPagerTotal() {
        return this.orm.searchCount("spreadsheet.dashboard", this.domain);
    }

    /**
     * @override
     */
    _getOpenSpreadsheetAction() {
        return {
            type: "ir.actions.client",
            tag: "action_edit_dashboard",
            params: {
                spreadsheet_id: this.state.selectedSpreadsheetId,
            }
        }
    }
}

patch(SpreadsheetSelectorDialog, {
    components: { ...SpreadsheetSelectorDialog.components, DashboardSelectorPanel },
});
