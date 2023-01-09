odoo.define('website_forum.test_error', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

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
        return this._rpc({
            route: $link.attr('href'),
        });
    }
});
});
