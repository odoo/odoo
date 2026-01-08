/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class ChangeLine extends Component {}
ChangeLine.template = "account.ResequenceChangeLine";
ChangeLine.props = ["changeLine", "ordering"];

class ShowResequenceRenderer extends Component {
    getValue() {
        const value = this.props.record.data[this.props.name];
        return value ? JSON.parse(value) : { changeLines: [], ordering: "date" };
    }
}
ShowResequenceRenderer.template = "account.ResequenceRenderer";
ShowResequenceRenderer.components = { ChangeLine };

registry.category("fields").add("account_resequence_widget", {
    component: ShowResequenceRenderer,
});
