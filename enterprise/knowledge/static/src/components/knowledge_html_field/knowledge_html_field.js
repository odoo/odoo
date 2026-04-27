import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import {
    KNOWLEDGE_EMBEDDINGS,
    KNOWLEDGE_READONLY_EMBEDDINGS,
} from "@knowledge/editor/embedded_components/embedding_sets";
import {
    KNOWLEDGE_EMBEDDED_COMPONENT_PLUGINS,
    KNOWLEDGE_PLUGINS,
} from "@knowledge/editor/plugin_sets";
import { registry } from "@web/core/registry";
import { useState, useSubEnv } from "@odoo/owl";
import { KnowledgeHtmlViewer } from "../knowledge_html_viewer/knowledge_html_viewer";
import { KnowledgeWysiwyg } from "../knowledge_wysiwyg/knowledge_wysiwyg";
import { CallbackRecorder } from "@web/search/action_hook";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { useService } from "@web/core/utils/hooks";

export class KnowledgeHtmlField extends HtmlField {
    static components = {
        ...HtmlField.components,
        Wysiwyg: KnowledgeWysiwyg,
        HtmlViewer: KnowledgeHtmlViewer,
    };
    setup() {
        super.setup();
        useSubEnv({
            __onLayoutGeometryChange__: new CallbackRecorder(),
        });
        this.commentsService = useService("knowledge.comments");
        this.commentsState = useState(this.commentsService.getCommentsState());
        useRecordObserver((record) => {
            if (record.resId !== this.commentsState.articleId) {
                this.commentsService.setArticleId(record.resId);
                this.commentsService.loadRecords(record.resId, {
                    ignoreBatch: true,
                    includeLoaded: true,
                });
            }
        });
    }

    getConfig() {
        const config = super.getConfig();
        // TODO @engagement: fill this array with knowledge components
        if (this.props.embeddedComponents) {
            config.resources.embedded_components = [
                ...(config.resources.embedded_components || []),
                ...KNOWLEDGE_EMBEDDINGS,
            ];
            // Replace the file plugin with the embedded file plugin
            config.Plugins = config.Plugins.filter((P) => P.id !== "file");
            config.Plugins.push(...KNOWLEDGE_EMBEDDED_COMPONENT_PLUGINS);
        }
        config.Plugins.push(...KNOWLEDGE_PLUGINS);
        config.onLayoutGeometryChange = () => this.onLayoutGeometryChange();
        return config;
    }

    getReadonlyConfig() {
        const config = super.getReadonlyConfig();
        if (this.props.embeddedComponents) {
            config.embeddedComponents = [
                ...(config.embeddedComponents || []),
                ...KNOWLEDGE_READONLY_EMBEDDINGS,
            ];
        }
        config.onLayoutGeometryChange = () => this.onLayoutGeometryChange();
        return config;
    }

    onLayoutGeometryChange() {
        for (const cb of this.env.__onLayoutGeometryChange__.callbacks) {
            cb();
        }
    }
}

export const knowledgeHtmlField = {
    ...htmlField,
    component: KnowledgeHtmlField,
};

registry.category("fields").add("knowledge_html", knowledgeHtmlField);
