/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.testError = publicWidget.Widget.extend({
    selector: '.rpc_error',
    events: {
        'click a': '_onRpcErrorClick',
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
        return rpc($link.attr('href'));
    }
});
