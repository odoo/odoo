/** @odoo-module alias=web_editor.toolbar **/

import Widget from "web.Widget";
import config from "web.config";

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

export default Toolbar;
