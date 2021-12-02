/** @odoo-module **/

import { DomainSelectorBranchOperator } from "./domain_selector_branch_operator";
import { DomainSelectorControlPanel } from "./domain_selector_control_panel";
import { DomainSelectorLeafNode } from "./domain_selector_leaf_node";

const { Component } = owl;

export class DomainSelectorBranchNode extends Component {}
DomainSelectorBranchNode.template = "web.DomainSelectorBranchNode";
DomainSelectorBranchNode.components = {
    DomainSelectorBranchNode,
    DomainSelectorBranchOperator,
    DomainSelectorControlPanel,
    DomainSelectorLeafNode,
};
