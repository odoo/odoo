/** @odoo-module **/

import options from '@web_editor/js/editor/snippets.options';

options.registry.NewsletterLayout = options.registry.SelectTemplate.extend({
    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this.containerSelector = '> .container, > .container-fluid, > .o_container_small';
        this.selectTemplateWidgetName = 'newsletter_template_opt';
    },
});
