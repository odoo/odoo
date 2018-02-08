odoo.define('web_editor.BodyManager', function (require) {
'use strict';

var rootWidget = require('web_editor.root_widget');
var ServiceProviderMixin = require('web.ServiceProviderMixin');
var session = require('web.session');

/**
 * Element which is designed to be unique and that will be the top-most element
 * in the widget hierarchy. So, all other widgets will be indirectly linked to
 * this Class instance. Its main role will be to retrieve RPC demands from its
 * children and handle them.
 */
var BodyManager = rootWidget.RootWidget.extend(ServiceProviderMixin, {
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        ServiceProviderMixin.init.call(this);
    },
    /**
     * @override
     */
    willStart: function () {
        return $.when(
            this._super.apply(this, arguments),
            session.is_bound
        );
    },
});
return BodyManager;
});
