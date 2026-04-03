/** @odoo-module **/

import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { BlockPalette } from "./BlockPalette";
import { DocumentCanvas } from "./DocumentCanvas";
import { PropertiesPanel } from "./PropertiesPanel";

export class DocumentBuilderRoot extends Component {
    static template = "gov_document_builder.DocumentBuilderRoot";
    static components = {
        BlockPalette,
        DocumentCanvas,
        PropertiesPanel,
    };
    static props = ["*"];

    setup() {
        this.store = useService("gov_document_builder_store");
        this.actionService = useService("action");

        onMounted(() => this.loadDocument());
    }

    get documentId() {
        return (
            this.props.documentId ||
            this.props.action?.context?.document_id ||
            this.props.action?.params?.document_id ||
            null
        );
    }

    async loadDocument() {
        if (!this.documentId) {
            return;
        }
        await this.store.loadDocument(this.documentId);
        await this.store.rebuildTypst();
    }

    closeBuilder() {
        if (!this.store.state.documentId) {
            window.history.back();
            return;
        }

        this.actionService.doAction({
            name: this.store.state.documentName,
            res_id: this.store.state.documentId,
            res_model: "gov.document.instance",
            target: "current",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        });
    }

    setMode(mode) {
        this.store.setMode(mode);
    }

    async saveLayout() {
        await this.store.saveLayout();
    }

    async exportTypst() {
        if (!this.store.state.typstSource) {
            await this.store.rebuildTypst();
        }

        const source = this.store.state.typstSource || "";
        const blob = new Blob([source], { type: "text/plain;charset=utf-8" });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        const fileName = `${(this.store.state.documentName || "documento")
            .trim()
            .replace(/\s+/g, "_")
            .toLowerCase()}.typ`;

        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }

    get processMeta() {
        const process = this.store.state.resolvedContext.process || {};
        const parts = [];
        if (process.number) {
            parts.push(`Processo ${process.number}`);
        }
        if (process.name) {
            parts.push(process.name);
        }
        if (process.objeto) {
            parts.push(process.objeto);
        }
        return parts.join(" · ") || "Sem processo vinculado";
    }

    get stateLabel() {
        const labels = {
            approved: "Aprovado",
            archived: "Arquivado",
            draft: "Rascunho",
            in_review: "Em Revisão",
        };
        return labels[this.store.state.documentState] || this.store.state.documentState;
    }
}

registry.category("actions").add("gov_document_builder", DocumentBuilderRoot);
