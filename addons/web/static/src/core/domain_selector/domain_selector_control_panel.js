/** @odoo-module **/

const { Component } = owl;

export class DomainSelectorControlPanel extends Component {
    deleteNode() {
        this.props.node.delete();
    }

    insertNode(newNodeType) {
        this.props.node.insert(newNodeType);
    }
}
DomainSelectorControlPanel.template = "web.DomainSelectorControlPanel";
DomainSelectorControlPanel.props = {
    node: Object,
};
