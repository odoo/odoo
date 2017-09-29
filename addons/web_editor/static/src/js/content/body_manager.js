odoo.define('web_editor.BodyManager', function (require) {
'use strict';

var mixins = require('web.mixins');
var session = require('web.session');
var rootWidget = require('web_editor.root_widget');

/**
 * Element which is designed to be unique and that will be the top-most element
 * in the widget hierarchy. So, all other widgets will be indirectly linked to
 * this Class instance. Its main role will be to retrieve RPC demands from its
 * children and handle them.
 */
var BodyManager = rootWidget.RootWidget.extend(mixins.ServiceProvider, {
    /**
     * @constructor
     */
    init: function () {
        mixins.ServiceProvider.init.call(this);
        this._super.apply(this, arguments);
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
