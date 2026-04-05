/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

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

    setup() {
        this.store = useService("gov_document_builder_store");
    }

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
        const items = (this.props.node.props || {}).items;
        return Array.isArray(items) ? items.filter(Boolean) : [];
    }

    get isToc() {
        return this.props.node.type === "sumario";
    }

    get isPageHeader() {
        return this.props.node.type === "page_header";
    }

    get isPageFooter() {
        return this.props.node.type === "page_footer";
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

    get blockTypeLabel() {
        const block = this.store.state.blockCatalog.find((item) => item.code === this.props.node.type);
        return block ? block.name : this.props.node.type;
    }

    get processRows() {
        const process = (this.store.state.resolvedContext || {}).process || {};
        const rows = [
            { label: "Processo", value: process.number || "—", binding: "process.number" },
            { label: "Objeto", value: process.objeto || process.name || "Sem objeto vinculado", binding: "process.objeto" },
            { label: "Modalidade", value: process.modalidade || "Não informada", binding: "process.modalidade" },
        ];
        return rows;
    }

    get summaryRows() {
        const process = (this.store.state.resolvedContext || {}).process || {};
        const summaryMap = [
            ["Número do Processo", process.number || "—"],
            ["Objeto", process.objeto || process.name || "—"],
            ["Modalidade", process.modalidade || "—"],
            ["Valor Estimado", process.valor_estimado || "—"],
        ];
        return summaryMap;
    }

    get metadataText() {
        const institution = (this.store.state.resolvedContext || {}).institution || {};
        const document = (this.store.state.resolvedContext || {}).document || {};
        const city = institution.city || "Manaus";
        const state = institution.state || "AM";
        const date = document.date || "";
        return `${city}/${state}, ${date}`.trim();
    }

    get tocTitle() {
        return (this.props.node.props || {}).titulo || "Sumário";
    }

    get tocDepth() {
        const depth = Number.parseInt((this.props.node.props || {}).profundidade, 10);
        if (Number.isNaN(depth)) {
            return 2;
        }
        return Math.min(Math.max(depth, 1), 2);
    }

    get tocEntries() {
        return (this.store.state.nodes || []).filter((candidate) => {
            if (candidate.type === "heading1") {
                return true;
            }
            return this.tocDepth >= 2 && candidate.type === "heading2";
        });
    }

    get timbreContext() {
        return (this.store.state.resolvedContext || {}).timbre || {};
    }

    get pageHeaderUsesImage() {
        return (this.props.node.props || {}).usar_imagem !== false;
    }

    get pageFooterUsesImage() {
        return (this.props.node.props || {}).usar_imagem !== false;
    }

    get pageFooterShowsNumber() {
        return (this.props.node.props || {}).mostrar_numero_pagina !== false;
    }

    get pageHeaderPreviewText() {
        if (this.pageHeaderUsesImage) {
            return "Cabeçalho — usa timbre institucional";
        }
        return (
            (this.props.node.props || {}).fallback_texto ||
            this.timbreContext.orgao_nome ||
            this.timbreContext.secretaria_nome ||
            "Cabeçalho textual configurado manualmente"
        );
    }

    get pageFooterPreviewText() {
        if (this.pageFooterUsesImage) {
            return "Rodapé — usa timbre institucional";
        }
        return (
            this.timbreContext.orgao_nome ||
            this.timbreContext.secretaria_nome ||
            "Rodapé textual do documento"
        );
    }

    get pageFooterNumberLabel() {
        return this.pageFooterShowsNumber ? "Número de página ativo" : "Número de página inativo";
    }

    get signatureBlocks() {
        return [
            {
                name: "Responsável pela Elaboração",
                role: "Documento administrativo",
            },
            {
                name: "Autoridade Competente",
                role: "Aprovação e assinatura",
            },
        ];
    }
}
