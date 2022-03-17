/** @odoo-module */

import FormView from 'web.FormView';
import viewRegistry from 'web.view_registry';
import { KnowledgeFormController } from './knowledge_controller.js';
import { KnowledgeFormRenderer } from './knowledge_renderers.js';
import { KnowledgeFormModel } from './knowledge_model.js'

const KnowledgeFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: KnowledgeFormController,
        Model: KnowledgeFormModel,
        Renderer: KnowledgeFormRenderer,
    }),
    /**
     * For the knowledge module, we want to display a headless layout.
     * To get a headless layout, the `init` function will deactivate the
     * control panel as well as the search bar and the default breadcrumb.
     * The form view will directly be open in the 'readonly' mode
     * to ensure that the user will not unintentionally edit the
     * document while doing a copy-past for instance.
     * @override
     * @param {Object} viewInfo
     * @param {Object} params
     */
    init: function (viewInfo, params) {
        params.withBreadcrumbs = false;
        params.withControlPanel = false;
        params.withSearchBar = false;
        params.mode = 'readonly';
        this._super.apply(this, arguments);
        this.rendererParams.breadcrumbs = params.breadcrumbs;
    },
});

viewRegistry.add('knowledge_view_form', KnowledgeFormView);

export {
    KnowledgeFormView,
};
