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
