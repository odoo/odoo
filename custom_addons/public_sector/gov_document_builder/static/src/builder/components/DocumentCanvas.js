/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

import { DocumentNode } from "./DocumentNode";

class EmptyDropZone extends Component {
    static template = "gov_document_builder.EmptyDropZone";
}

export class DocumentCanvas extends Component {
    static template = "gov_document_builder.DocumentCanvas";
    static components = {
        DocumentNode,
        EmptyDropZone,
    };

    setup() {
        this.store = useService("gov_document_builder_store");
    }

    clearSelection() {
        this.store.selectNode(null);
    }

    selectNode(nodeId) {
        this.store.selectNode(nodeId);
    }

    moveNode(nodeId, direction) {
        this.store.moveNode(nodeId, direction);
    }

    deleteNode(nodeId) {
        this.store.deleteNode(nodeId);
    }

    onDragStart(ev, nodeId) {
        Object.assign(this.store.state.dragState, {
            draggingNodeId: nodeId,
            overNodeId: nodeId,
            placement: null,
        });

        if (ev.dataTransfer) {
            ev.dataTransfer.effectAllowed = "move";
            ev.dataTransfer.setData("text/plain", nodeId);
        }
    }

    onDragOver(ev, nodeId) {
        ev.preventDefault();
        const rect = ev.currentTarget.getBoundingClientRect();
        const placement = ev.clientY < rect.top + rect.height / 2 ? "before" : "after";

        Object.assign(this.store.state.dragState, {
            overNodeId: nodeId,
            placement,
        });

        if (ev.dataTransfer) {
            ev.dataTransfer.dropEffect = "move";
        }
    }

    onCanvasDragOver(ev) {
        ev.preventDefault();
        Object.assign(this.store.state.dragState, {
            overNodeId: null,
            placement: "after",
        });
    }

    onCanvasDrop(ev) {
        ev.preventDefault();
        if (!this.store.state.nodes.length) {
            this._resetDragState();
            return;
        }

        const draggingNodeId = this.store.state.dragState.draggingNodeId;
        const lastNode = this.store.state.nodes[this.store.state.nodes.length - 1];
        if (draggingNodeId && lastNode && draggingNodeId !== lastNode.id) {
            this._moveNodeToIndex(draggingNodeId, this.store.state.nodes.length - 1);
        }
        this._resetDragState();
    }

    onDrop(ev, nodeId) {
        ev.preventDefault();
        ev.stopPropagation();

        const draggingNodeId = this.store.state.dragState.draggingNodeId;
        if (!draggingNodeId || draggingNodeId === nodeId) {
            this._resetDragState();
            return;
        }

        const currentIndex = this.store.state.nodes.findIndex((node) => node.id === draggingNodeId);
        const targetIndex = this.store.state.nodes.findIndex((node) => node.id === nodeId);
        if (currentIndex < 0 || targetIndex < 0) {
            this._resetDragState();
            return;
        }

        const placement = this.store.state.dragState.placement || "after";
        let desiredIndex = targetIndex;
        if (currentIndex < targetIndex) {
            desiredIndex = placement === "before" ? targetIndex - 1 : targetIndex;
        } else if (currentIndex > targetIndex) {
            desiredIndex = placement === "before" ? targetIndex : targetIndex + 1;
        }

        desiredIndex = Math.max(0, Math.min(desiredIndex, this.store.state.nodes.length - 1));
        this._moveNodeToIndex(draggingNodeId, desiredIndex);
        this._resetDragState();
    }

    _moveNodeToIndex(nodeId, desiredIndex) {
        let currentIndex = this.store.state.nodes.findIndex((node) => node.id === nodeId);
        if (currentIndex < 0 || currentIndex === desiredIndex) {
            return;
        }

        const direction = currentIndex < desiredIndex ? 1 : -1;
        while (currentIndex !== desiredIndex) {
            this.store.moveNode(nodeId, direction);
            currentIndex += direction;
        }
    }

    _resetDragState() {
        Object.assign(this.store.state.dragState, {
            draggingNodeId: null,
            overNodeId: null,
            placement: null,
        });
    }
}
