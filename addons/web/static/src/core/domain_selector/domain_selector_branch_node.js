/** @odoo-module **/

import { DomainSelectorBranchOperator } from "./domain_selector_branch_operator";
import { DomainSelectorControlPanel } from "./domain_selector_control_panel";
import { DomainSelectorLeafNode } from "./domain_selector_leaf_node";

import { Component, useRef } from "@odoo/owl";

export class DomainSelectorBranchNode extends Component {
    setup() {
        this.root = useRef("root");
    }
    onHoverDeleteNodeBtn(hovering) {
        this.root.el.classList.toggle("o_hover_btns", hovering);
    }
    onHoverInsertLeafNodeBtn(hovering) {
        this.root.el.classList.toggle("o_hover_add_node", hovering);
    }
    onHoverInsertBranchNodeBtn(hovering) {
        this.root.el.classList.toggle("o_hover_add_node", hovering);
        this.root.el.classList.toggle("o_hover_add_inset_node", hovering);
    }
}
DomainSelectorBranchNode.template = "web.DomainSelectorBranchNode";
DomainSelectorBranchNode.components = {
    DomainSelectorBranchNode,
    DomainSelectorBranchOperator,
    DomainSelectorControlPanel,
    DomainSelectorLeafNode,
};
