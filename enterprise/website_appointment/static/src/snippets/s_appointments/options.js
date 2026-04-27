/** @odoo-module **/

import options from '@web_editor/js/editor/snippets.options';
import dynamicSnippetOptions from '@website/snippets/s_dynamic_snippet/options';

const AppointmentsListSnippetOptions = dynamicSnippetOptions.extend({
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.modelNameFilter = 'appointment.type';
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'template_opt') {
            // By default, we only have one template (the "Cards layout"), so we hide this
            // option unless we get more than one choice (custom code, overrides, ...)
            return Object.keys(this.dynamicFilterTemplates).length > 1;
        } else if (widgetName === 'filter_resource') {
            return this.$target[0].dataset.filterType === 'resources';
        } else if (widgetName === 'filter_user') {
            return this.$target[0].dataset.filterType === 'users';
        }
        return this._super(...arguments);
    },
});

options.registry.appointments = AppointmentsListSnippetOptions;
