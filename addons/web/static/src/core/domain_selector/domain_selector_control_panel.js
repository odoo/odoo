/** @odoo-module **/

const { Component } = owl;

export class DomainSelectorControlPanel extends Component {
    deleteNode() {
        this.props.node.delete();
    }

    insertNode(newNodeType) {
        this.props.node.insert(newNodeType);
    }

    onEnterDeleteNodeBtn() {
        this.props.onHoverDeleteNodeBtn(true);
    }
    onLeaveDeleteNodeBtn() {
        this.props.onHoverDeleteNodeBtn(false);
    }
    onEnterInsertLeafNodeBtn() {
        this.props.onHoverInsertLeafNodeBtn(true);
    }
    onLeaveInsertLeafNodeBtn() {
        this.props.onHoverInsertLeafNodeBtn(false);
    }
    onEnterInsertBranchNodeBtn() {
        this.props.onHoverInsertBranchNodeBtn(true);
    }
    onLeaveInsertBranchNodeBtn() {
        this.props.onHoverInsertBranchNodeBtn(false);
    }
}
DomainSelectorControlPanel.template = "web.DomainSelectorControlPanel";
DomainSelectorControlPanel.props = {
    node: Object,
    onHoverDeleteNodeBtn: Function,
    onHoverInsertLeafNodeBtn: Function,
    onHoverInsertBranchNodeBtn: Function,
};
