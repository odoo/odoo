odoo.define('web_editor.toolbar', function (require) {
'use strict';

var Widget = require('web.Widget');
var config = require('web.config');

const Toolbar = Widget.extend({
    /**
     * @constructor
     * @param {Widget} parent
     * @param {string} contents
     */
    init: function (parent, template = 'web_editor.toolbar') {
        this._super.apply(this, arguments);
        this.template = template;
    },
    /**
     * States whether the current environment is in mobile or not. This is
     * useful in order to customize the template rendering for mobile view.
     *
     * @returns {boolean}
     */
    isMobile() {
        return config.device.isMobile;
    },
});

return Toolbar;

});
