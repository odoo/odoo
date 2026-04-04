/** @odoo-module **/

import { Component, markup, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { BlockPalette } from "./BlockPalette";
import { DocumentCanvas } from "./DocumentCanvas";
import { PropertiesPanel } from "./PropertiesPanel";

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function highlightTypst(source) {
    const content = source || "// Nenhum Typst renderizado ainda.";
    const lines = content.split("\n").map((line) => {
        const escaped = escapeHtml(line);
        if (escaped.trim().startsWith("//")) {
            return `<span class="gdb-ty-comment">${escaped || "&nbsp;"}</span>`;
        }
        let rendered = escaped;
        rendered = rendered.replace(/(&quot;[^&]*?&quot;)/g, '<span class="gdb-ty-string">$1</span>');
        rendered = rendered.replace(/(^={1,3}.*$)/, '<span class="gdb-ty-heading">$1</span>');
        rendered = rendered.replace(/(#import|#show)/g, '<span class="gdb-ty-keyword">$1</span>');
        rendered = rendered.replace(/(#\w+)/g, '<span class="gdb-ty-fn">$1</span>');
        rendered = rendered.replace(
            /\b(title|process_no|unit|numero|objeto|modalidade|number)\b/g,
            '<span class="gdb-ty-value">$1</span>'
        );
        return rendered || "&nbsp;";
    });
    return markup(lines.map((line) => `<span class="gdb-typst-line">${line}</span>`).join(""));
}

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
        await this.store.resolveContext();
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
        if (mode === "typst" && !this.store.state.typstSource) {
            this.store.rebuildTypst();
        }
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
        const institution = this.store.state.resolvedContext.institution || {};
        const parts = [];
        if (institution.name) {
            parts.push(institution.name);
        }
        if (process.number) {
            parts.push(`Processo ${process.number}`);
        }
        parts.push("gov_document_builder");
        return parts.join(" · ");
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

    get processContext() {
        return this.store.state.resolvedContext.process || {};
    }

    get institutionContext() {
        return this.store.state.resolvedContext.institution || {};
    }

    get documentContext() {
        return this.store.state.resolvedContext.document || {};
    }

    get processBadge() {
        return this.processContext.number || "Sem processo";
    }

    get processTitle() {
        return (
            this.processContext.objeto ||
            this.processContext.name ||
            this.store.state.documentName ||
            "Documento administrativo"
        );
    }

    get processSubtitle() {
        const parts = [];
        if (this.institutionContext.name) {
            parts.push(this.institutionContext.name);
        }
        if (this.processContext.modalidade) {
            parts.push(this.processContext.modalidade);
        }
        if (!parts.length) {
            parts.push("Contexto processual será resolvido em runtime");
        }
        return parts.join(" · ");
    }

    get blockCountLabel() {
        const count = this.store.state.nodes.length;
        return `${count} bloco${count === 1 ? "" : "s"}`;
    }

    get processConnectionLabel() {
        return this.processContext.number ? "Conectado ao processo" : "Sem processo vinculado";
    }

    get documentTypeLabel() {
        return (this.store.state.documentTypeCode || this.store.state.documentTypeName || "-").toUpperCase();
    }

    get statusClass() {
        const classByState = {
            approved: "is-approved",
            archived: "is-archived",
            draft: "is-draft",
            in_review: "is-review",
        };
        return classByState[this.store.state.documentState] || "is-draft";
    }

    get highlightedTypstSource() {
        return highlightTypst(this.store.state.typstSource);
    }
}

registry.category("actions").add("gov_document_builder.instance", DocumentBuilderRoot);
