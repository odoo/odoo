/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.testError = publicWidget.Widget.extend({
    selector: '.rpc_error',
    events: {
        'click a': '_onRpcErrorClick',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * make a rpc call with the href of the DOM element clicked
     * @private
     * @param {Event} ev
     * @returns {Promise}
     */
    _onRpcErrorClick: function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        return this.rpc($link.attr('href'));
    }
});
