/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PropertiesPanel extends Component {
    static template = "gov_document_builder.PropertiesPanel";

    setup() {
        this.store = useService("gov_document_builder_store");
    }

    get selectedNode() {
        return this.store.getSelectedNode();
    }

    get blockDefinition() {
        if (!this.selectedNode) {
            return null;
        }
        return (
            this.store.state.blockCatalog.find((block) => block.code === this.selectedNode.type) || null
        );
    }

    get supportsBinding() {
        return Boolean(this.blockDefinition?.supports_binding);
    }

    get hasBinding() {
        const binding = this.selectedNode?.binding || {};
        return Boolean(binding.source || binding.path || binding.fallback || binding.transform);
    }

    updateText(ev) {
        if (!this.selectedNode) {
            return;
        }
        this.store.updateNodeProps(this.selectedNode.id, { text: ev.target.value });
    }

    updateLabel(ev) {
        if (!this.selectedNode) {
            return;
        }
        this.store.updateNodeProps(this.selectedNode.id, { label: ev.target.value });
    }

    updateContent(ev) {
        if (!this.selectedNode) {
            return;
        }
        this.store.updateNodeProps(this.selectedNode.id, { content: ev.target.value });
    }

    updateBulletItems(ev) {
        if (!this.selectedNode) {
            return;
        }
        const items = ev.target.value
            .split("\n")
            .map((item) => item.trim())
            .filter(Boolean);
        this.store.updateNodeProps(this.selectedNode.id, { items });
    }

    toggleBinding(ev) {
        if (!this.selectedNode) {
            return;
        }

        if (ev.target.checked) {
            this.store.updateNodeBinding(this.selectedNode.id, {
                source: "process",
                path: "",
                fallback: "",
                transform: "",
            });
            return;
        }

        this.store.updateNodeBinding(this.selectedNode.id, {});
    }

    updateBindingField(field, ev) {
        if (!this.selectedNode) {
            return;
        }
        const binding = {
            ...(this.selectedNode.binding || {}),
            [field]: ev.target.value,
        };
        this.store.updateNodeBinding(this.selectedNode.id, binding);
    }

    duplicateNode() {
        if (!this.selectedNode) {
            return;
        }
        this.store.duplicateNode(this.selectedNode.id);
    }

    deleteNode() {
        if (!this.selectedNode) {
            return;
        }
        this.store.deleteNode(this.selectedNode.id);
    }

    get bulletItemsText() {
        const items = this.selectedNode?.props?.items;
        return Array.isArray(items) ? items.join("\n") : "";
    }

    get blockName() {
        return this.blockDefinition ? this.blockDefinition.name : this.selectedNode?.type || "";
    }

    get nodeText() {
        return (this.selectedNode?.props || {}).text || "";
    }

    get nodeLabel() {
        return (this.selectedNode?.props || {}).label || "";
    }

    get nodeContent() {
        return (this.selectedNode?.props || {}).content || "";
    }

    get bindingSource() {
        return (this.selectedNode?.binding || {}).source || "";
    }

    get bindingPath() {
        return (this.selectedNode?.binding || {}).path || "";
    }

    get bindingFallback() {
        return (this.selectedNode?.binding || {}).fallback || "";
    }

    get bindingTransform() {
        return (this.selectedNode?.binding || {}).transform || "";
    }
}
