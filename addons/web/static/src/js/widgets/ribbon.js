odoo.define('web.ribbon', function (require) {
    'use strict';

    /**
     * This widget adds a ribbon on the top right side of the form
     *
     *      - You can specify the text with the title attribute.
     *      - You can specify the tooltip with the tooltip attribute.
     *      - You can specify a background color for the ribbon with the bg_color attribute
     *        using bootstrap classes :
     *        (bg-primary, bg-secondary, bg-success, bg-danger, bg-warning, bg-info,
     *        bg-light, bg-dark, bg-white)
     *
     *        If you don't specify the bg_color attribute the bg-success class will be used
     *        by default.
     */

    var widgetRegistry = require('web.widget_registry');
    var Widget = require('web.Widget');

    var RibbonWidget = Widget.extend({
        template: 'web.ribbon',
        xmlDependencies: ['/web/static/src/xml/ribbon.xml'],

        /**
         * @param {Object} options
         * @param {string} options.attrs.title
         * @param {string} options.attrs.text same as title
         * @param {string} options.attrs.tooltip
         * @param {string} options.attrs.bg_color
         */
        init: function (parent, data, options) {
            this._super.apply(this, arguments);
            this.text = options.attrs.title || options.attrs.text;
            this.tooltip = options.attrs.tooltip;
            this.className = options.attrs.bg_color ? options.attrs.bg_color : 'bg-success';
            if (this.text.length > 15) {
                this.className += ' o_small';
            } else if (this.text.length > 10) {
                this.className += ' o_medium';
            }
        },
    });

    widgetRegistry.add('web_ribbon', RibbonWidget);

    return RibbonWidget;
});
