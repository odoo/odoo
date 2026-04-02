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
import {
    DEFAULT_SLASH_COMMANDS,
    applySlashCommandToHtml,
    createBlockFromDefinition,
    detectSlashCommand,
    enrichBlocks,
    getProcessHeaderRows,
    getSummaryRows,
    renderBlocksToTypst,
    resolveBlockContent,
} from "./gov_document_builder_typst";

// ─── Sub-componentes inline ──────────────────────────────────────────────────
class GovBlockPreview extends Component {
    static template = "gov_processos.GovBlockPreview";
    static props = { block: Object, bindings: Object };

    get resolvedContent() {
        return resolveBlockContent(this.props.block, this.props.bindings);
    }

    get headerRows() {
        return getProcessHeaderRows(this.props.bindings);
    }

    get summaryRows() {
        return getSummaryRows(this.props.block, this.props.bindings);
    }
}

class GovBlockEditor extends Component {
    static template = "gov_processos.GovBlockEditor";
    static props = {
        block: Object,
        bindings: Object,
        slashState: Object,
        slashCommands: Array,
        onUpdate: Function,
        onRichTextInput: Function,
        onRichTextKeydown: Function,
        onSlashCommandSelect: Function,
    };

    get resolvedContent() {
        return resolveBlockContent(this.props.block, this.props.bindings);
    }

    get summaryRowsText() {
        return this.resolvedContent.linhas || "";
    }

    get summaryLines() {
        return this.summaryRowsText
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean);
    }

    get isSlashMenuOpen() {
        return this.props.slashState?.open && this.props.slashState.blockId === this.props.block.id;
    }
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
        defaultContent: { linhas: "" },
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
        this.typstEditorRef = useRef("typstEditor");

        this.docId = this.props.action?.params?.doc_id;
        this.initialMode = this.props.action?.params?.initial_mode;
        this.returnAction = this.props.action?.params?.return_action;
        this.catalog = BLOCK_CATALOG;
        this.catalogMap = new Map(this.catalog.map((item) => [item.type, item]));
        this.lastSavedLayoutJson = JSON.stringify([]);
        this.lastSavedTypstSource = "";

        this.state = useState({
            loading: true,
            saving: false,
            doc: null,
            builderTemplate: null,
            recordContext: {},
            blocks: [],           // blocos na prancheta (ordenados)
            activeBlockId: null,  // ID do bloco sendo editado
            dragOverIndex: null,  // índice do drop target
            previewMode: false,
            searchQuery: "",
            editMode: "visual",
            typstSource: "",
            slashMenu: {
                open: false,
                blockId: null,
                query: "",
                commands: [],
            },
            typstValidation: null,
            validatingTypst: false,
            assistantBusy: false,
            assistantInfo: null,
            assistantPrompt: "",
            assistantMode: "",
            assistantResult: "",
            assistantApplyText: "",
            assistantProvider: "",
            assistantModel: "",
            assistantDurationMs: 0,
            assistantValidation: null,
            assistantSelectionStart: 0,
            assistantSelectionEnd: 0,
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
            const bootstrap = await this.orm.call(
                "gov.processo.doc",
                "action_builder_bootstrap",
                [[this.docId]]
            );
            const doc = bootstrap?.doc || {};
            this.state.doc = doc;
            this.state.recordContext = bootstrap?.record_context || {};
            this.state.builderTemplate = bootstrap?.builder_template || null;
            this.state.assistantInfo = bootstrap?.assistant_info || null;
            const initialBlocks = enrichBlocks(
                bootstrap?.initial_blocks || [],
                this.catalogMap,
                this.state.recordContext
            );
            this.state.blocks = initialBlocks;
            this.lastSavedLayoutJson = doc.layout_json || JSON.stringify([]);
            const generatedTypst =
                doc.typst_source ||
                (initialBlocks.length
                    ? renderBlocksToTypst(initialBlocks, this.state.recordContext)
                    : "");
            this.state.typstSource = generatedTypst;
            this.lastSavedTypstSource = doc.typst_source || "";
            this.state.editMode =
                this.initialMode ||
                ((doc.typst_source || "").trim() && initialBlocks.length === 0
                    ? "typst"
                    : "visual");
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
        const newBlock = createBlockFromDefinition(def, this.catalogMap, this.state.recordContext);
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
        if (this.state.slashMenu.blockId === blockId) {
            this.closeSlashMenu();
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
        if (this.state.slashMenu.blockId && this.state.slashMenu.blockId !== blockId) {
            this.closeSlashMenu();
        }
    }

    updateBlockContent(blockId, field, value) {
        const block = this.state.blocks.find((b) => b.id === blockId);
        if (block) {
            block.content[field] = value;
        }
    }

    setEditMode(mode) {
        const previousMode = this.state.editMode;
        this.state.editMode = mode;
        if (mode === "typst" && !this.state.assistantInfo) {
            this._loadTypstAssistantInfo();
        }
        if (mode === "typst" && previousMode === "visual" && this.state.blocks.length) {
            this.syncTypstFromVisual();
        }
    }

    onTypstInput(ev) {
        this.state.typstSource = ev.target.value;
        this._resetTypstValidation();
    }

    onAssistantPromptInput(ev) {
        this.state.assistantPrompt = ev.target.value;
    }

    syncTypstFromVisual() {
        const generated = renderBlocksToTypst(this.state.blocks, this.state.recordContext);
        this.state.typstSource = generated;
        this._resetTypstValidation();
        return generated;
    }

    openSlashMenu(blockId, query) {
        const normalizedQuery = (query || "").toLowerCase();
        const commands = DEFAULT_SLASH_COMMANDS.filter((command) =>
            !normalizedQuery || command.name.includes(normalizedQuery)
        );
        this.state.slashMenu = {
            open: !!commands.length,
            blockId,
            query: normalizedQuery,
            commands,
        };
    }

    closeSlashMenu() {
        this.state.slashMenu = {
            open: false,
            blockId: null,
            query: "",
            commands: [],
        };
    }

    _resetTypstValidation() {
        this.state.typstValidation = null;
        this.state.assistantValidation = null;
    }

    _applyValidationPayload(validation) {
        this.state.typstValidation = validation || null;
    }

    async _loadTypstAssistantInfo() {
        if (!this.docId) {
            return;
        }
        try {
            const info = await this.orm.call(
                "gov.processo.doc",
                "action_typst_assistant_status",
                [[this.docId]]
            );
            this.state.assistantInfo = info || null;
        } catch (e) {
            this.state.assistantInfo = null;
            this.notification.add(
                _t("Não foi possível carregar o assistente Typst: ") +
                    this._getErrorMessage(e, _t("Odoo Server Error")),
                { type: "warning" }
            );
        }
    }

    _getEditorSelection() {
        const editor = this.typstEditorRef.el;
        if (!editor) {
            const length = this.state.typstSource.length;
            return {
                cursorPosition: length,
                selectionStart: length,
                selectionEnd: length,
            };
        }
        return {
            cursorPosition: editor.selectionStart ?? 0,
            selectionStart: editor.selectionStart ?? 0,
            selectionEnd: editor.selectionEnd ?? 0,
        };
    }

    onRichTextInput(blockId, field, ev) {
        this.updateBlockContent(blockId, field, ev.target.innerHTML);
        const block = this.state.blocks.find((item) => item.id === blockId);
        if (block?.type === "texto_livre") {
            const slashInfo = detectSlashCommand(ev.target);
            if (slashInfo) {
                this.openSlashMenu(blockId, slashInfo.query);
            } else if (this.state.slashMenu.blockId === blockId) {
                this.closeSlashMenu();
            }
        } else if (this.state.slashMenu.blockId === blockId) {
            this.closeSlashMenu();
        }
    }

    onRichTextKeydown(blockId, ev) {
        if (!(this.state.slashMenu.open && this.state.slashMenu.blockId === blockId)) {
            return;
        }
        if (ev.key === "Escape") {
            ev.preventDefault();
            this.closeSlashMenu();
            return;
        }
        if (ev.key === "Enter") {
            ev.preventDefault();
            const [command] = this.state.slashMenu.commands;
            if (command) {
                this.onSlashCommandSelect(blockId, command);
            }
        }
    }

    onSlashCommandSelect(blockId, command) {
        const block = this.state.blocks.find((item) => item.id === blockId);
        if (!block) {
            return;
        }
        const updatedHtml = applySlashCommandToHtml(block.content.html || "", command);
        this.updateBlockContent(blockId, "html", updatedHtml);
        this.closeSlashMenu();
        this.notification.add(
            _t("Comando preparado: ") + command.label,
            { type: "info" }
        );
    }

    _collectErrorMessages(error) {
        const queue = [error];
        const messages = [];
        const seen = new Set();
        while (queue.length) {
            const current = queue.shift();
            if (!current || seen.has(current)) {
                continue;
            }
            if (typeof current === "object") {
                seen.add(current);
            }
            if (typeof current === "string") {
                messages.push(current.trim());
                continue;
            }
            if (current.message) {
                messages.push(String(current.message).trim());
            }
            if (current.data?.message) {
                messages.push(String(current.data.message).trim());
            }
            if (current.data?.debug) {
                messages.push(String(current.data.debug).trim());
            }
            if (current.cause) {
                queue.push(current.cause);
            }
            if (current.data) {
                queue.push(current.data);
            }
        }
        return messages.filter(Boolean);
    }

    _getErrorMessage(error, fallbackMessage) {
        const messages = this._collectErrorMessages(error);
        const preferredMessage = messages.find(
            (message) =>
                !["Odoo Server Error", "RPC_ERROR"].includes(message) &&
                !message.startsWith("Traceback")
        );
        if (preferredMessage) {
            return preferredMessage;
        }
        return fallbackMessage;
    }

    _buildViewsFromMode(viewMode) {
        const modes = String(viewMode || "form")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);
        return modes.length ? modes.map((mode) => [false, mode]) : [[false, "form"]];
    }

    onTypstPaste(ev) {
        const previousLength = this.state.typstSource.length;
        const pastedText = ev.clipboardData?.getData("text/plain") || "";
        if (previousLength <= 32 && pastedText.length > 256) {
            requestAnimationFrame(() => {
                if (this.typstEditorRef.el) {
                    this.typstEditorRef.el.scrollTop = 0;
                }
            });
        }
    }

    onQuickEscapeCurrency() {
        let replacements = 0;
        const updatedSource = (this.state.typstSource || "").replace(
            /(^|[^\\])(R\$)/gm,
            (match, prefix) => {
                replacements += 1;
                return `${prefix}R\\$`;
            }
        );
        if (!replacements) {
            this.notification.add(_t("Nenhum 'R$' sem escape foi encontrado."), {
                type: "info",
            });
            return;
        }
        this.state.typstSource = updatedSource;
        this._resetTypstValidation();
        this.notification.add(
            _t("Correção rápida aplicada em ") + `${replacements} ` + _t("ocorrência(s) de R$."),
            { type: "success" }
        );
        requestAnimationFrame(() => this.typstEditorRef.el?.focus());
    }

    scrollTypstToTop() {
        if (this.typstEditorRef.el) {
            this.typstEditorRef.el.scrollTo({ top: 0, behavior: "smooth" });
            this.typstEditorRef.el.focus();
        }
    }

    async onValidateTypst() {
        if (!this.docId || this.state.validatingTypst) {
            return;
        }
        this.state.validatingTypst = true;
        try {
            const validation = await this.orm.call(
                "gov.processo.doc",
                "action_typst_validate_source",
                [[this.docId], this.state.typstSource]
            );
            this._applyValidationPayload(validation);
            this.notification.add(
                validation?.compile_ok
                    ? _t("Validação Typst concluída.")
                    : _t("Validação concluída com erros de compilação."),
                { type: validation?.compile_ok ? "success" : "warning" }
            );
        } catch (e) {
            this.notification.add(
                _t("Erro ao validar Typst: ") +
                    this._getErrorMessage(e, _t("Odoo Server Error")),
                { type: "danger" }
            );
        } finally {
            this.state.validatingTypst = false;
        }
    }

    async onRunTypstAssistant(mode) {
        if (!this.docId || this.state.assistantBusy) {
            return;
        }
        this.state.assistantBusy = true;
        this.state.assistantMode = mode;
        this.state.assistantResult = "";
        this.state.assistantApplyText = "";
        this.state.assistantProvider = "";
        this.state.assistantModel = "";
        this.state.assistantDurationMs = 0;
        this.state.assistantValidation = null;
        this.state.assistantSelectionStart = 0;
        this.state.assistantSelectionEnd = 0;
        try {
            const selection = this._getEditorSelection();
            const result = await this.orm.call(
                "gov.processo.doc",
                "action_typst_ai_assist",
                [
                    [this.docId],
                    this.state.typstSource,
                    mode,
                    this.state.assistantPrompt,
                    selection.cursorPosition,
                    selection.selectionStart,
                    selection.selectionEnd,
                ]
            );
            this.state.assistantResult = result?.output_text || "";
            this.state.assistantApplyText = result?.apply_text || "";
            this.state.assistantProvider = result?.provider || "";
            this.state.assistantModel = result?.model_name || "";
            this.state.assistantDurationMs = result?.duration_ms || 0;
            this.state.assistantValidation = result?.result_validation || null;
            this.state.assistantSelectionStart = result?.selection_start ?? 0;
            this.state.assistantSelectionEnd = result?.selection_end ?? 0;
            this._applyValidationPayload(result?.source_validation || null);
            this.notification.add(
                mode === "debug"
                    ? _t("Diagnóstico IA concluído.")
                    : _t("Sugestão IA pronta para revisão."),
                { type: "success" }
            );
        } catch (e) {
            this.notification.add(
                _t("Erro no assistente Typst: ") +
                    this._getErrorMessage(e, _t("Odoo Server Error")),
                { type: "danger" }
            );
        } finally {
            this.state.assistantBusy = false;
        }
    }

    applyAssistantSuggestion() {
        if (!this.state.assistantApplyText || this.isLocked) {
            return;
        }
        const editor = this.typstEditorRef.el;
        if (this.state.assistantMode === "fix") {
            this.state.typstSource = this.state.assistantApplyText;
            this._applyValidationPayload(this.state.assistantValidation);
            this.notification.add(_t("Correção completa aplicada ao editor."), {
                type: "success",
            });
            requestAnimationFrame(() => {
                editor?.focus();
                if (editor) {
                    editor.selectionStart = 0;
                    editor.selectionEnd = 0;
                    editor.scrollTop = 0;
                }
            });
            return;
        }

        if (this.state.assistantMode === "autocomplete") {
            const start = this.state.assistantSelectionStart ?? this._getEditorSelection().selectionStart;
            const end = this.state.assistantSelectionEnd ?? this._getEditorSelection().selectionEnd;
            this.state.typstSource =
                this.state.typstSource.slice(0, start) +
                this.state.assistantApplyText +
                this.state.typstSource.slice(end);
            this._applyValidationPayload(this.state.assistantValidation);
            this.notification.add(_t("Snippet inserido no cursor."), {
                type: "success",
            });
            requestAnimationFrame(() => {
                editor?.focus();
                if (editor) {
                    const caret = start + this.state.assistantApplyText.length;
                    editor.selectionStart = caret;
                    editor.selectionEnd = caret;
                }
            });
        }
    }

    clearAssistantResult() {
        this.state.assistantMode = "";
        this.state.assistantResult = "";
        this.state.assistantApplyText = "";
        this.state.assistantProvider = "";
        this.state.assistantModel = "";
        this.state.assistantDurationMs = 0;
        this.state.assistantValidation = null;
        this.state.assistantSelectionStart = 0;
        this.state.assistantSelectionEnd = 0;
    }

    scrollTypstToBottom() {
        if (this.typstEditorRef.el) {
            this.typstEditorRef.el.scrollTo({
                top: this.typstEditorRef.el.scrollHeight,
                behavior: "smooth",
            });
            this.typstEditorRef.el.focus();
        }
    }

    // ── Salvar ──────────────────────────────────────────────────────────────-
    async onSave(silent = false) {
        if (!this.docId || this.state.saving) return;
        this.state.saving = true;
        try {
            const typstSource =
                this.state.editMode === "visual"
                    ? this.syncTypstFromVisual()
                    : this.state.typstSource;
            const layoutJson = JSON.stringify(this.state.blocks);
            if (
                layoutJson === this.lastSavedLayoutJson &&
                typstSource === this.lastSavedTypstSource &&
                this.state.doc?.is_visual_builder
            ) {
                if (!silent) {
                    this.notification.add(_t("Nenhuma alteração pendente para salvar."), {
                        type: "info",
                    });
                }
                return true;
            }
            const response = await this.orm.call(
                "gov.processo.doc",
                "action_builder_save_payload",
                [[this.docId], this.state.blocks, typstSource]
            );
            this.lastSavedLayoutJson = layoutJson;
            this.lastSavedTypstSource = response?.typst_source || typstSource;
            this.state.typstSource = response?.typst_source || typstSource;
            if (response?.record_context) {
                this.state.recordContext = response.record_context;
            }
            this.state.doc = {
                ...(this.state.doc || {}),
                is_visual_builder: true,
                name: response?.doc_name || this.state.doc?.name || "",
            };
            if (!silent) {
                this.notification.add(_t("Documento salvo com sucesso!"), {
                    type: "success",
                });
            }
            return true;
        } catch (e) {
            this.notification.add(
                _t("Erro ao salvar: ") + this._getErrorMessage(e, _t("Odoo Server Error")),
                { type: "danger" }
            );
            return false;
        } finally {
            this.state.saving = false;
        }
    }

    // ── Gerar PDF via backend ────────────────────────────────────────────────
    async onGeneratePdf() {
        const saved = await this.onSave(true);
        if (!saved) return;
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
                _t("Erro ao gerar PDF: ") + this._getErrorMessage(e, _t("Odoo Server Error")),
                { type: "danger" }
            );
        }
    }

    // ── Voltar ao documento ─────────────────────────────────────────────────-
    onBack() {
        if (this.returnAction) {
            const action = { ...this.returnAction };
            if (action.type === "ir.actions.act_window" && !action.views) {
                action.views = this._buildViewsFromMode(action.view_mode);
            }
            this.action.doAction(action);
            return;
        }
        if (this.docId) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "gov.processo.doc",
                res_id: this.docId,
                view_mode: "form",
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    get blockCount() {
        return this.state.blocks.length;
    }

    get builderBadge() {
        if (this.state.editMode === "typst") {
            return _t("Modo Typst");
        }
        return `${this.blockCount} blocos`;
    }

    get isLocked() {
        return this.state.doc?.state === "assinado";
    }

    get backLabel() {
        return this.returnAction ? _t("Voltar ao Wizard") : _t("Voltar");
    }

    get typstDiagnostics() {
        return this.state.typstValidation?.diagnostics || [];
    }

    get typstStatusClass() {
        const status = this.state.typstValidation?.status;
        if (status === "error") {
            return "gov-typst-status-badge gov-typst-status-badge--error";
        }
        if (status === "warning") {
            return "gov-typst-status-badge gov-typst-status-badge--warning";
        }
        if (status === "success") {
            return "gov-typst-status-badge gov-typst-status-badge--success";
        }
        return "gov-typst-status-badge";
    }

    get typstStatusLabel() {
        const status = this.state.typstValidation?.status;
        if (status === "error") {
            return _t("Erros encontrados");
        }
        if (status === "warning") {
            return _t("Compila, mas há alertas");
        }
        if (status === "success") {
            return _t("Pronto para PDF");
        }
        if (status === "empty") {
            return _t("Sem conteúdo");
        }
        return _t("Sem validação");
    }

    get typstStatsLabel() {
        const stats = this.state.typstValidation?.stats;
        if (!stats) {
            return _t("Valide para ver linhas e caracteres.");
        }
        return `${stats.lines} ${_t("linhas")} · ${stats.chars} ${_t("caracteres")}`;
    }

    get assistantBadge() {
        const provider = this.state.assistantInfo?.provider || "ollama";
        const model = this.state.assistantInfo?.model_name || "";
        return model ? `${provider} · ${model}` : provider;
    }

    get assistantCanApply() {
        return (
            !this.isLocked &&
            !!this.state.assistantApplyText &&
            ["fix", "autocomplete"].includes(this.state.assistantMode)
        );
    }

    get assistantApplyLabel() {
        return this.state.assistantMode === "autocomplete"
            ? _t("Inserir no cursor")
            : _t("Aplicar correção");
    }

    get hasCurrencyRisk() {
        return /(^|[^\\])R\$/m.test(this.state.typstSource || "");
    }
}

registry.category("actions").add("gov_document_builder", GovDocumentBuilder);
