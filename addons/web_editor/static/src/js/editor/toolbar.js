odoo.define('web_editor.toolbar', function (require) {
'use strict';

var Widget = require('web.Widget');

const Toolbar = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],

    /**
     * @constructor
     * @param {Widget} parent
     * @param {string} contents
     */
    init: function (parent, template = 'web_editor.toolbar') {
        this._super.apply(this, arguments);
        this.template = template;
    },
});

return Toolbar;

});
