/** @odoo-module **/

const { Component } = owl;

export class DomainSelectorBranchOperator extends Component {
    onOperatorSelected(operator) {
        this.props.node.update(operator);
    }
}
DomainSelectorBranchOperator.template = "web.DomainSelectorBranchOperator";
DomainSelectorBranchOperator.props = {
    node: Object,
    readonly: Boolean,
};
