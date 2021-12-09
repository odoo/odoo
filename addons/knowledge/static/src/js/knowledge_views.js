/** @odoo-module */

import FormView from 'web.FormView';
import viewRegistry from 'web.view_registry';
import { KnowledgeArticleFormController } from './knowledge_controller.js';
import { KnowledgeArticleFormRenderer } from './knowledge_renderers.js';

const KnowledgeArticleFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: KnowledgeArticleFormController,
        Renderer: KnowledgeArticleFormRenderer,
    }),
    /**
     * For the knowledge module, we want to display a headless layout.
     * To get a headless layout, the `init` function will deactivate the
     * control panel as well as the search bar and the default breadcrumb.
     * @override
     * @param {Object} viewInfo
     * @param {Object} params
     */
    init: function (viewInfo, params) {
        params.withBreadcrumbs = false;
        params.withControlPanel = false;
        params.withSearchBar = false;
        this._super.apply(this, arguments);
        this.rendererParams.breadcrumbs = params.breadcrumbs;
    },
});

viewRegistry.add('knowledge_article_view_form', KnowledgeArticleFormView);

export {
    KnowledgeArticleFormView,
};
