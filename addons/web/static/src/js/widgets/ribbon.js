odoo.define('web.ribbon', function (require) {
    'use strict';

    /**
     * This widget adds a ribbon on the top right side of the form
     *
     *      - You can specify the text with the text attribute.
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

        init: function (parent, data, options) {
            this._super.apply(this, arguments);
            this.text = options.attrs.text;
            this.bgColor = options.attrs.bg_color;
        }

    });

    widgetRegistry.add('web_ribbon', RibbonWidget);

    return RibbonWidget;
});