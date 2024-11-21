/** @odoo-module */

import options from '@web_editor/js/editor/snippets.options';

options.registry.MasonryLayout = options.registry.SelectTemplate.extend({
    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this.containerSelector = '> .container, > .container-fluid, > .o_container_small';
        this.selectTemplateWidgetName = 'masonry_template_opt';
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the container class according to the template.
     *
     * @see this.selectClass for parameters
     */
    selectContainerClass(previewMode, widgetValue, params) {
        const containerEl = this.$target[0].firstElementChild;
        const containerClasses = ["container", "container-fluid", "o_container_small"];
        containerEl.classList.remove(...containerClasses);
        containerEl.classList.add(widgetValue);
    },
});
