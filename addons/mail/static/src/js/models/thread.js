odoo.define('mail.model.Thread', function (require) {
"use strict";

var Class = require('web.Class');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');

var Thread = Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @param {mail.ChatManager} parent
     */
    init: function (parent) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);

        this._chatManager = parent;

        this._FETCH_LIMIT = 30; // max number of fetched messages from the server
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

});

return Thread;

});
