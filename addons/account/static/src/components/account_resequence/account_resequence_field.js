/** @odoo-module */

import { registry } from "@web/core/registry";

const { Component, onWillUpdateProps } = owl;

class ChangeLine extends Component {}
ChangeLine.template = "account.ResequenceChangeLine";
ChangeLine.props = ["changeLine", "ordering"];

class ShowResequenceRenderer extends Component {
    setup() {
        this.formatData(this.props);
        onWillUpdateProps((nextProps) => this.formatData(nextProps));
    }

    formatData(props) {
        this.data = props.value ? JSON.parse(props.value) : { changeLines: [], ordering: "date" };
    }
}
ShowResequenceRenderer.template = "account.ResequenceRenderer";
ShowResequenceRenderer.components = { ChangeLine };

registry.category("fields").add("account_resequence_widget", ShowResequenceRenderer);
