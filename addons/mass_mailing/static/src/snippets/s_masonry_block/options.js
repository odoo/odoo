odoo.define('mass_mailing.masonryOptions', function (require) {
'use strict';

const options = require('web_editor.snippets.options');

options.registry.MasonryLayout = options.registry.SelectTemplate.extend({
    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this.containerSelector = '> .container, > .container-fluid, > .o_container_small';
        this.selectTemplateWidgetName = 'masonry_template_opt';
    },
});
});
