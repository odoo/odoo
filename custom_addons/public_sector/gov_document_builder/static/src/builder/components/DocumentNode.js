/** @odoo-module **/

import { Component } from "@odoo/owl";

export class DocumentNode extends Component {
    static template = "gov_document_builder.DocumentNode";
    static props = {
        index: Number,
        isSelected: Boolean,
        node: Object,
        onDelete: Function,
        onMove: Function,
        onSelect: Function,
    };

    selectNode() {
        this.props.onSelect();
    }

    moveUp(ev) {
        ev.stopPropagation();
        this.props.onMove(-1);
    }

    moveDown(ev) {
        ev.stopPropagation();
        this.props.onMove(1);
    }

    deleteNode(ev) {
        ev.stopPropagation();
        this.props.onDelete();
    }

    get bulletItems() {
        const items = this.props.node.props?.items;
        return Array.isArray(items) ? items.filter(Boolean) : [];
    }

    get bindingLabel() {
        const binding = this.props.node.binding || {};
        if (!binding.source || !binding.path) {
            return "Sem binding configurado";
        }
        return `${binding.source}.${binding.path}`;
    }

    get headingText() {
        return (this.props.node.props || {}).text || "Título";
    }

    get nodeLabel() {
        return (this.props.node.props || {}).label || "Campo do Processo";
    }

    get nodeContent() {
        return (this.props.node.props || {}).content || "[texto livre]";
    }
}
