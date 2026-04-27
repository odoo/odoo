/** @odoo-module */

import { formView } from '@web/views/form/form_view';
import { registry } from "@web/core/registry";
import { KnowledgeArticleFormController } from './knowledge_controller.js';
import { KnowledgeArticleFormRenderer } from './knowledge_renderers.js';

export const knowledgeArticleFormView = {
    ...formView,
    Controller: KnowledgeArticleFormController,
    Renderer: KnowledgeArticleFormRenderer,
    display: {controlPanel: false}
};

registry.category('views').add('knowledge_article_view_form', knowledgeArticleFormView);
