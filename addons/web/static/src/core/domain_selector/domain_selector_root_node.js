/** @odoo-module **/

import { DomainSelectorBranchNode } from "./domain_selector_branch_node";
import { DomainSelectorBranchOperator } from "./domain_selector_branch_operator";
import { DomainSelectorLeafNode } from "./domain_selector_leaf_node";

import { Component } from "@odoo/owl";

export class DomainSelectorRootNode extends Component {
    get hasNode() {
        return this.props.node.operands.length > 0;
    }
    get node() {
        return this.props.node.operands[0];
    }

    insertNode(newNodeType) {
        this.props.node.insert(newNodeType);
    }

    onOperatorSelected(ev) {
        this.props.node.update(ev.detail.payload.operator);
    }
    onChange(ev) {
        this.props.node.update(ev.target.value, true);
    }
}
DomainSelectorRootNode.template = "web.DomainSelectorRootNode";
DomainSelectorRootNode.components = {
    DomainSelectorBranchNode,
    DomainSelectorBranchOperator,
    DomainSelectorLeafNode,
};
