/** @odoo-module **/

const { Component } = owl;

export class DomainSelectorBranchOperator extends Component {
    onOperatorSelected(ev) {
        this.props.node.update(ev.detail.payload.operator);
    }
}
DomainSelectorBranchOperator.template = "web.DomainSelectorBranchOperator";
DomainSelectorBranchOperator.props = {
    node: Object,
    readonly: Boolean,
};
