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

    selectTemplate(previewMode, widgetValue, params) {
        // TODO remove in master, needed to fix broken masonry block in
        // avantgarde theme in outdated databases.
        if (!this.$target.find(this.containerSelector).length) {
            this.containerEl = this.$target[0].ownerDocument.createElement('div');
            this.containerEl.classList.add('container-fluid');
            this.$target[0].appendChild(this.containerEl);
            this.containerEl.appendChild(this.$target[0].querySelector(':scope > .row'));
        }
        return this._super(...arguments);
    },

    /**
     * Changes the container class according to the template.
     *
     * @see this.selectClass for parameters
     */
    selectContainerClass(previewMode, widgetValue, params) {
        const containerEl = this.$target[0].firstElementChild;
        const containerClasses = ["container", "container-fluid", "o_container_small"];
        if (!containerClasses.some(cls => containerEl.classList.contains(cls))) {
            return;
        }
        containerEl.classList.remove(...containerClasses);
        containerEl.classList.add(widgetValue);
    },
});
