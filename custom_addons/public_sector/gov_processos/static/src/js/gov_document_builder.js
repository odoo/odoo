/** @odoo-module **/

import {
    Component,
    useState,
    onWillStart,
    useRef,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// ─── Sub-componentes inline ──────────────────────────────────────────────────
class GovBlockPreview extends Component {
    static template = "gov_processos.GovBlockPreview";
    static props = { block: Object };
}

class GovBlockEditor extends Component {
    static template = "gov_processos.GovBlockEditor";
    static props = { block: Object, onUpdate: Function };
}

const BLOCK_CATALOG = [
    {
        type: "titulo",
        label: "📄 Título Principal",
        icon: "fa-heading",
        description: "Título e subtítulo do documento",
        defaultContent: { titulo: "", subtitulo: "" },
        editable: true,
    },
    {
        type: "cabecalho_processo",
        label: "📋 Cabeçalho do Processo",
        icon: "fa-info-circle",
        description: "Número, objeto e dados do processo",
        defaultContent: { texto: "" },
        editable: false,  // preenchido automaticamente
    },
    {
        type: "texto_livre",
        label: "📝 Texto Livre",
        icon: "fa-align-left",
        description: "Parágrafo com editor rico (suporte a /comandos)",
        defaultContent: { html: "<p>Digite aqui o conteúdo...</p>" },
        editable: true,
    },
    {
        type: "objeto",
        label: "🎯 Objeto",
        icon: "fa-bullseye",
        description: "Descrição do objeto da contratação",
        defaultContent: { html: "" },
        editable: true,
    },
    {
        type: "justificativa",
        label: "⚖️ Justificativa",
        icon: "fa-balance-scale",
        description: "Justificativa da necessidade administrativa",
        defaultContent: { html: "" },
        editable: true,
    },
    {
        type: "base_legal",
        label: "📜 Base Legal",
        icon: "fa-gavel",
        description: "Fundamentos legais aplicáveis",
        defaultContent: { html: "" },
        editable: true,
    },
    {
        type: "quadro_resumo",
        label: "📊 Quadro Resumo",
        icon: "fa-table",
        description: "Tabela de dados no formato 'Rótulo: Valor'",
        defaultContent: { linhas: "Valor estimado: R$ 0,00\nFonte: Tesouro Municipal" },
        editable: true,
    },
    {
        type: "pontos_chave",
        label: "🔑 Pontos-Chave",
        icon: "fa-list-ul",
        description: "Lista de conclusões ou pontos importantes",
        defaultContent: { texto: "Ponto 1\nPonto 2\nPonto 3" },
        editable: true,
    },
    {
        type: "encaminhamento",
        label: "🚀 Encaminhamento",
        icon: "fa-paper-plane",
        description: "Instrução de encaminhamento e providências",
        defaultContent: { html: "" },
        editable: true,
    },
    {
        type: "assinatura",
        label: "✍️ Assinatura",
        icon: "fa-signature",
        description: "Bloco de assinatura do responsável",
        defaultContent: { nome: "", cargo: "" },
        editable: true,
    },
];

// ─── Componente principal ────────────────────────────────────────────────────
export class GovDocumentBuilder extends Component {
    static template = "gov_processos.GovDocumentBuilder";
    static components = { GovBlockPreview, GovBlockEditor };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.canvasRef = useRef("canvas");

        this.docId = this.props.action?.params?.doc_id;
        this.catalog = BLOCK_CATALOG;

        this.state = useState({
            loading: true,
            saving: false,
            doc: null,
            blocks: [],           // blocos na prancheta (ordenados)
            activeBlockId: null,  // ID do bloco sendo editado
            dragOverIndex: null,  // índice do drop target
            previewMode: false,
            searchQuery: "",
        });

        onWillStart(() => this._loadDocument());
    }

    // ── Carregamento ─────────────────────────────────────────────────────────
    async _loadDocument() {
        if (!this.docId) {
            this.state.loading = false;
            return;
        }
        try {
            const [doc] = await this.orm.read(
                "gov.processo.doc",
                [this.docId],
                ["name", "layout_json", "processo_id", "doc_type", "state"]
            );
            this.state.doc = doc;
            // Restaurar blocos salvos ou iniciar vazio
            if (doc.layout_json) {
                try {
                    this.state.blocks = JSON.parse(doc.layout_json);
                } catch {
                    this.state.blocks = [];
                }
            }
        } catch (e) {
            this.notification.add(
                _t("Erro ao carregar documento: ") + e.message,
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    // ── Catálogo filtrado ─────────────────────────────────────────────────────
    get filteredCatalog() {
        const q = (this.state.searchQuery || "").toLowerCase();
        if (!q) return this.catalog;
        return this.catalog.filter(
            (b) =>
                b.label.toLowerCase().includes(q) ||
                b.description.toLowerCase().includes(q)
        );
    }

    // ── Drag & Drop – Catálogo ─── ─────────────────────────────────────────-
    onCatalogDragStart(ev, blockDef) {
        ev.dataTransfer.setData("catalog_type", blockDef.type);
        ev.dataTransfer.effectAllowed = "copy";
    }

    onCanvasDragOver(ev, index) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "copy";
        this.state.dragOverIndex = index;
    }

    onCanvasDragLeave() {
        this.state.dragOverIndex = null;
    }

    onCanvasDrop(ev, targetIndex) {
        ev.preventDefault();
        this.state.dragOverIndex = null;

        // Arrastar do catálogo → criar novo bloco
        const catalogType = ev.dataTransfer.getData("catalog_type");
        if (catalogType) {
            this._insertBlock(catalogType, targetIndex);
            return;
        }

        // Reordenar bloco existente na prancheta
        const fromIndex = parseInt(
            ev.dataTransfer.getData("canvas_index"),
            10
        );
        if (!isNaN(fromIndex)) {
            this._reorderBlock(fromIndex, targetIndex);
        }
    }

    // ── Drag & Drop – Prancheta ───────────────────────────────────────────────
    onBlockDragStart(ev, index) {
        ev.dataTransfer.setData("canvas_index", String(index));
        ev.dataTransfer.effectAllowed = "move";
    }

    // ── Criação e manipulação de blocos ───────────────────────────────────────
    _insertBlock(type, atIndex) {
        const def = this.catalog.find((b) => b.type === type);
        if (!def) return;
        const newBlock = {
            id: `block_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
            type: def.type,
            label: def.label,
            editable: def.editable,
            content: JSON.parse(JSON.stringify(def.defaultContent)),
        };
        const blocks = [...this.state.blocks];
        const insertAt =
            atIndex !== undefined ? atIndex : blocks.length;
        blocks.splice(insertAt, 0, newBlock);
        this.state.blocks = blocks;
        this.state.activeBlockId = newBlock.id;
    }

    _reorderBlock(fromIndex, toIndex) {
        const blocks = [...this.state.blocks];
        const [moved] = blocks.splice(fromIndex, 1);
        const dest = toIndex > fromIndex ? toIndex - 1 : toIndex;
        blocks.splice(dest, 0, moved);
        this.state.blocks = blocks;
    }

    addBlock(type) {
        this._insertBlock(type, undefined);
    }

    removeBlock(blockId) {
        this.state.blocks = this.state.blocks.filter((b) => b.id !== blockId);
        if (this.state.activeBlockId === blockId) {
            this.state.activeBlockId = null;
        }
    }

    moveUp(index) {
        if (index <= 0) return;
        this._reorderBlock(index, index - 1);
    }

    moveDown(index) {
        if (index >= this.state.blocks.length - 1) return;
        this._reorderBlock(index, index + 2);
    }

    toggleEdit(blockId) {
        this.state.activeBlockId =
            this.state.activeBlockId === blockId ? null : blockId;
    }

    updateBlockContent(blockId, field, value) {
        const block = this.state.blocks.find((b) => b.id === blockId);
        if (block) {
            block.content[field] = value;
        }
    }

    // ── Salvar ──────────────────────────────────────────────────────────────-
    async onSave() {
        if (!this.docId || this.state.saving) return;
        this.state.saving = true;
        try {
            const layoutJson = JSON.stringify(this.state.blocks);
            await this.orm.write("gov.processo.doc", [this.docId], {
                layout_json: layoutJson,
                is_visual_builder: true,
            });
            this.notification.add(_t("Layout salvo com sucesso!"), {
                type: "success",
            });
        } catch (e) {
            this.notification.add(
                _t("Erro ao salvar: ") + e.message,
                { type: "danger" }
            );
        } finally {
            this.state.saving = false;
        }
    }

    // ── Gerar PDF via backend ────────────────────────────────────────────────
    async onGeneratePdf() {
        await this.onSave();
        if (!this.docId) return;
        try {
            await this.orm.call(
                "gov.processo.doc",
                "action_gerar_pdf",
                [[this.docId]]
            );
            this.notification.add(_t("PDF gerado com sucesso!"), {
                type: "success",
            });
        } catch (e) {
            this.notification.add(
                _t("Erro ao gerar PDF: ") + e.message,
                { type: "danger" }
            );
        }
    }

    // ── Voltar ao documento ─────────────────────────────────────────────────-
    onBack() {
        if (this.docId) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "gov.processo.doc",
                res_id: this.docId,
                view_mode: "form",
                target: "current",
            });
        }
    }

    get blockCount() {
        return this.state.blocks.length;
    }
}

registry.category("actions").add("gov_document_builder", GovDocumentBuilder);
