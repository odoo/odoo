/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class ListViewSwitcher extends Component {
    static template = "account_accountant.ListViewSwitcher";
    static props = standardFieldProps;

    setup() {
        this.action = useService("action");
    }

    /** Called when the Match/View button is clicked. **/
    switchView() {
        // Add a new search facet to restrict the results to the selected statement line.
        const searchItem = Object.values(this.env.searchModel.searchItems).find((i) => i.fieldName === "statement_line_id");
        const stLineId = this.props.record.resId;
        const autocompleteValue = {
            label: this.props.record.data.move_id[1],
            operator: "=",
            value: stLineId,
        }
        this.env.searchModel.addAutoCompletionValues(searchItem.id, autocompleteValue);

        // Switch to the kanban.
        this.action.switchView("kanban", { skipRestore: this.env.skipKanbanRestoreNeeded(stLineId) });
    }

    /** Give the button's label for the current record. **/
    get buttonLabel() {
        return this.props.record.data.is_reconciled ? _t("View") : _t("Match");
    }
}

registry.category("fields").add('bank_rec_list_view_switcher', {component: ListViewSwitcher});
