/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const INITIAL_STATE = {
    documentId: null,
    documentName: "",
    documentTypeCode: "",
    documentTypeName: "",
    documentState: "draft",
    documentVersion: 1,
    templateId: null,
    mode: "visual", // 'visual' | 'typst'
    nodes: [], // lista de nós do layout
    selectedNodeId: null,
    dragState: {
        draggingNodeId: null,
        overNodeId: null,
        placement: null, // 'before' | 'after'
    },
    typstSource: "",
    dirty: false,
    saving: false,
    validationErrors: [],
    resolvedContext: {},
    blockCatalog: [],
    fieldDefinitions: [],
};

export class DocumentBuilderStore {
    constructor(env) {
        this.env = env;
        this.rpc = rpc;
        this.notification = env.services.notification;
        this.state = reactive({ ...INITIAL_STATE });
        this._debouncedRebuildTypst = this._debounce(() => this.rebuildTypst(), 800);
    }

    // ── INICIALIZAÇÃO ──────────────────────────────────────────

    async loadDocument(documentId) {
        const data = await this.rpc("/gov/document/load", { document_id: documentId });
        Object.assign(this.state, {
            documentId: data.id,
            documentName: data.name,
            documentTypeCode: data.document_type?.code || "",
            documentTypeName: data.document_type?.name || "",
            documentState: data.state || "draft",
            documentVersion: data.version || 1,
            nodes: JSON.parse(data.layout_json || "[]"),
            resolvedContext: data.resolved_context || {},
            typstSource: "",
            dirty: false,
        });
        await this.loadBlockCatalog(data.document_type?.code);
        await this.loadFieldDefinitions();
    }

    async resolveContext() {
        if (!this.state.documentId) {
            return {};
        }
        const context = await this.rpc("/gov/document/resolve_context", {
            document_id: this.state.documentId,
        });
        this.state.resolvedContext = context || {};
        return this.state.resolvedContext;
    }

    async loadBlockCatalog(documentTypeCode) {
        const catalog = await this.rpc("/gov/document/block_catalog", {
            document_type_code: documentTypeCode || null,
        });
        this.state.blockCatalog = catalog;
    }

    async loadFieldDefinitions() {
        const definitions = await this.rpc("/gov/document/field_definitions", {});
        this.state.fieldDefinitions = definitions || [];
    }

    resolveBindingPreview(binding) {
        const source = binding?.source || "";
        const path = binding?.path || "";
        if (!source || !path) {
            return "";
        }

        let value = this.state.resolvedContext?.[source];
        const keys = path.split(".").filter(Boolean);
        let missing = value === undefined || value === null;
        for (const key of keys) {
            if (missing || value === null || typeof value !== "object" || !(key in value)) {
                missing = true;
                break;
            }
            value = value[key];
        }

        if (missing || value === undefined || value === null) {
            return "[valor.em.runtime]";
        }

        const definition = this.state.fieldDefinitions.find(
            (field) => field.namespace === source && field.variable_key === path
        );
        const transformer =
            binding?.transform || definition?.default_transformer || "";

        return this._applyBindingTransformer(value, transformer);
    }

    // ── MUTAÇÕES DE NÓS ────────────────────────────────────────

    insertBlock(blockCode, targetIndex = null) {
        const def = this.state.blockCatalog.find((block) => block.code === blockCode);
        if (!def) {
            return;
        }
        const newNode = {
            id: `n_${Date.now().toString(36)}`,
            type: blockCode,
            sequence: 0,
            props: { ...(def.default_props || {}) },
            binding: {},
            locked: def.is_locked_by_default || false,
        };
        const idx = targetIndex !== null ? targetIndex : this.state.nodes.length;
        this.state.nodes.splice(idx, 0, newNode);
        this._recalcSequences();
        this.state.dirty = true;
        this.selectNode(newNode.id);
        this._debouncedRebuildTypst();
    }

    moveNode(nodeId, direction) {
        const idx = this.state.nodes.findIndex((node) => node.id === nodeId);
        if (idx < 0) {
            return;
        }
        const targetIdx = idx + direction;
        if (targetIdx < 0 || targetIdx >= this.state.nodes.length) {
            return;
        }
        const nodes = this.state.nodes;
        [nodes[idx], nodes[targetIdx]] = [nodes[targetIdx], nodes[idx]];
        this._recalcSequences();
        this.state.dirty = true;
        this._debouncedRebuildTypst();
    }

    deleteNode(nodeId) {
        const node = this.state.nodes.find((currentNode) => currentNode.id === nodeId);
        if (!node) {
            return;
        }
        if (node.locked) {
            this.notification.add("Este bloco é obrigatório e não pode ser removido.", {
                type: "warning",
            });
            return;
        }
        this.state.nodes = this.state.nodes.filter((currentNode) => currentNode.id !== nodeId);
        if (this.state.selectedNodeId === nodeId) {
            this.state.selectedNodeId = null;
        }
        this._recalcSequences();
        this.state.dirty = true;
        this._debouncedRebuildTypst();
    }

    updateNodeProps(nodeId, patch) {
        const node = this.state.nodes.find((currentNode) => currentNode.id === nodeId);
        if (!node) {
            return;
        }
        Object.assign(node.props, patch);
        this.state.dirty = true;
        this._debouncedRebuildTypst();
    }

    updateNodeBinding(nodeId, binding) {
        const node = this.state.nodes.find((currentNode) => currentNode.id === nodeId);
        if (!node) {
            return;
        }
        node.binding = binding;
        this.state.dirty = true;
        this._debouncedRebuildTypst();
    }

    duplicateNode(nodeId) {
        const idx = this.state.nodes.findIndex((node) => node.id === nodeId);
        if (idx < 0) {
            return;
        }
        const original = this.state.nodes[idx];
        const copy = JSON.parse(JSON.stringify(original));
        copy.id = `n_${Date.now().toString(36)}_copy`;
        copy.locked = false;
        this.state.nodes.splice(idx + 1, 0, copy);
        this._recalcSequences();
        this.state.dirty = true;
        this.selectNode(copy.id);
        this._debouncedRebuildTypst();
    }

    selectNode(nodeId) {
        this.state.selectedNodeId = nodeId;
    }

    // ── PERSISTÊNCIA ───────────────────────────────────────────

    async saveLayout() {
        if (!this.state.documentId) {
            return;
        }
        this.state.saving = true;
        try {
            const layoutJson = JSON.stringify(this.state.nodes);
            const result = await this.rpc("/gov/document/save_layout", {
                document_id: this.state.documentId,
                layout_json: layoutJson,
            });
            this.state.typstSource = result.typst_source || "";
            this.state.dirty = false;
            this.notification.add("Documento salvo com sucesso.", { type: "success" });
        } catch (error) {
            this.notification.add("Erro ao salvar documento.", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async rebuildTypst() {
        if (!this.state.documentId) {
            return;
        }
        try {
            const result = await this.rpc("/gov/document/render_typst", {
                document_id: this.state.documentId,
            });
            this.state.typstSource = result.typst_source || "";
        } catch (error) {
            console.warn("gov_document_builder: erro ao renderizar Typst", error);
        }
    }

    // ── HELPERS ────────────────────────────────────────────────

    setMode(mode) {
        this.state.mode = mode;
    }

    getSelectedNode() {
        return this.state.nodes.find((node) => node.id === this.state.selectedNodeId) || null;
    }

    _recalcSequences() {
        this.state.nodes.forEach((node, index) => {
            node.sequence = (index + 1) * 10;
        });
    }

    _debounce(fn, delay) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    _applyBindingTransformer(value, transformer) {
        if (!transformer) {
            return this._formatPreviewValue(value);
        }
        if (transformer === "date_br") {
            const date = value instanceof Date ? value : new Date(value);
            if (!Number.isNaN(date.getTime())) {
                return date.toLocaleDateString("pt-BR");
            }
            return this._formatPreviewValue(value);
        }
        if (transformer === "currency_br") {
            const numeric = this._coerceNumber(value);
            if (numeric !== null) {
                return new Intl.NumberFormat("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                }).format(numeric);
            }
            return this._formatPreviewValue(value);
        }
        if (transformer === "percentual") {
            const numeric = this._coerceNumber(value);
            if (numeric !== null) {
                return new Intl.NumberFormat("pt-BR", {
                    style: "percent",
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                }).format(numeric);
            }
            return this._formatPreviewValue(value);
        }
        if (transformer === "lista_br") {
            if (Array.isArray(value)) {
                const items = value.filter((item) => item !== null && item !== undefined && item !== "");
                if (!items.length) {
                    return "";
                }
                if (items.length === 1) {
                    return `${items[0]}`;
                }
                if (items.length === 2) {
                    return `${items[0]} e ${items[1]}`;
                }
                return `${items.slice(0, -1).join(", ")} e ${items[items.length - 1]}`;
            }
            return this._formatPreviewValue(value);
        }
        if (typeof value !== "string") {
            return this._formatPreviewValue(value);
        }
        const transformers = {
            strip: (current) => current.trim(),
            upper: (current) => current.toUpperCase(),
            lower: (current) => current.toLowerCase(),
            title: (current) =>
                current.replace(/\w\S*/g, (word) => {
                    return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
                }),
        };
        return (transformers[transformer] || ((current) => current))(value);
    }

    _formatPreviewValue(value) {
        if (Array.isArray(value)) {
            return value.join(", ");
        }
        if (typeof value === "boolean") {
            return value ? "Sim" : "Não";
        }
        if (value && typeof value === "object") {
            return JSON.stringify(value);
        }
        return `${value}`;
    }

    _coerceNumber(value) {
        if (typeof value === "number") {
            return Number.isFinite(value) ? value : null;
        }
        if (typeof value === "string" && value.trim()) {
            const normalized = value.includes(",") && value.includes(".")
                ? value.replace(/\./g, "").replace(",", ".")
                : value.replace(",", ".");
            const parsed = Number.parseFloat(normalized);
            return Number.isFinite(parsed) ? parsed : null;
        }
        return null;
    }
}

registry.category("services").add("gov_document_builder_store", {
    dependencies: ["notification"],
    start(env) {
        return new DocumentBuilderStore(env);
    },
});
