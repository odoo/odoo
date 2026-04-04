/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const TRANSFORMER_OPTIONS = [
    { value: "", label: "Sem transformação" },
    { value: "strip", label: "strip" },
    { value: "upper", label: "upper" },
    { value: "lower", label: "lower" },
    { value: "title", label: "title" },
    { value: "date_br", label: "date_br" },
    { value: "currency_br", label: "currency_br" },
    { value: "percentual", label: "percentual" },
    { value: "lista_br", label: "lista_br" },
];

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
        return Boolean(this.blockDefinition && this.blockDefinition.supports_binding);
    }

    get hasBinding() {
        const binding = (this.selectedNode && this.selectedNode.binding) || {};
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
        const items = ((this.selectedNode && this.selectedNode.props) || {}).items;
        return Array.isArray(items) ? items.join("\n") : "";
    }

    get blockName() {
        return this.blockDefinition ? this.blockDefinition.name : (this.selectedNode && this.selectedNode.type) || "";
    }

    get nodeText() {
        return ((this.selectedNode && this.selectedNode.props) || {}).text || "";
    }

    get nodeLabel() {
        return ((this.selectedNode && this.selectedNode.props) || {}).label || "";
    }

    get nodeContent() {
        return ((this.selectedNode && this.selectedNode.props) || {}).content || "";
    }

    get bindingSource() {
        return ((this.selectedNode && this.selectedNode.binding) || {}).source || "";
    }

    get bindingPath() {
        return ((this.selectedNode && this.selectedNode.binding) || {}).path || "";
    }

    get bindingFallback() {
        return ((this.selectedNode && this.selectedNode.binding) || {}).fallback || "";
    }

    get bindingTransform() {
        const binding = (this.selectedNode && this.selectedNode.binding) || {};
        if (Object.prototype.hasOwnProperty.call(binding, "transform")) {
            return binding.transform || "";
        }
        return (this.selectedFieldDefinition && this.selectedFieldDefinition.default_transformer) || "";
    }

    get bindingDisplayPath() {
        if (!this.hasBinding) {
            return "binding inativo";
        }
        const source = this.bindingSource || "source";
        const path = this.bindingPath || "*";
        return `${source}.${path}`;
    }

    get transformerOptions() {
        return TRANSFORMER_OPTIONS;
    }

    get availableNamespaces() {
        const namespaces = new Set(
            (this.store.state.fieldDefinitions || []).map((field) => field.namespace)
        );
        return Array.from(namespaces).sort();
    }

    get fieldsForSelectedNamespace() {
        if (!this.bindingSource) {
            return [];
        }
        return (this.store.state.fieldDefinitions || []).filter(
            (field) => field.namespace === this.bindingSource
        );
    }

    get selectedFieldDefinition() {
        if (!this.bindingSource || !this.bindingPath) {
            return null;
        }
        return (
            (this.store.state.fieldDefinitions || []).find(
                (field) =>
                    field.namespace === this.bindingSource &&
                    field.variable_key === this.bindingPath
            ) || null
        );
    }

    get mutabilityBadge() {
        if (!this.selectedFieldDefinition) {
            return null;
        }
        const badgeByPolicy = {
            immutable: { label: "Imutável", class: "gdb-badge-success" },
            snapshot: { label: "Snapshot", class: "gdb-badge-info" },
            dynamic: { label: "Dinâmico", class: "gdb-badge-warning" },
        };
        return badgeByPolicy[this.selectedFieldDefinition.mutability_policy] || null;
    }

    get bindingPreview() {
        if (!this.hasBinding) {
            return "";
        }
        return this.store.resolveBindingPreview(this.selectedNode.binding || {});
    }

    get isRuntimePreview() {
        return this.bindingPreview === "[valor.em.runtime]";
    }

    selectNamespace(ev) {
        if (!this.selectedNode) {
            return;
        }
        const namespace = ev.target.value;
        const currentBinding = this.selectedNode.binding || {};
        const { transform, ...bindingWithoutTransform } = currentBinding;
        this.store.updateNodeBinding(this.selectedNode.id, {
            ...bindingWithoutTransform,
            source: namespace,
            path: "",
        });
    }

    selectField(ev) {
        if (!this.selectedNode) {
            return;
        }
        const variableKey = ev.target.value;
        const definition = this.fieldsForSelectedNamespace.find(
            (field) => field.variable_key === variableKey
        );
        const currentBinding = this.selectedNode.binding || {};
        const nextBinding = {
            ...currentBinding,
            source: this.bindingSource,
            path: variableKey,
        };
        if (definition?.default_transformer) {
            nextBinding.transform = definition.default_transformer;
        } else if (!Object.prototype.hasOwnProperty.call(currentBinding, "transform")) {
            delete nextBinding.transform;
        }
        this.store.updateNodeBinding(this.selectedNode.id, nextBinding);
    }
}
