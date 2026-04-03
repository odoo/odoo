/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

const INITIAL_STATE = {
    documentId: null,
    documentName: "",
    documentTypeCode: "",
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
};

export class DocumentBuilderStore {
    constructor(env) {
        this.env = env;
        this.rpc = env.services.rpc;
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
            documentState: data.state || "draft",
            documentVersion: data.version || 1,
            nodes: JSON.parse(data.layout_json || "[]"),
            resolvedContext: data.resolved_context || {},
            typstSource: "",
            dirty: false,
        });
        await this.loadBlockCatalog(data.document_type?.code);
    }

    async loadBlockCatalog(documentTypeCode) {
        const catalog = await this.rpc("/gov/document/block_catalog", {
            document_type_code: documentTypeCode || null,
        });
        this.state.blockCatalog = catalog;
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
}

registry.category("services").add("gov_document_builder_store", {
    dependencies: ["rpc", "notification"],
    start(env) {
        return new DocumentBuilderStore(env);
    },
});
