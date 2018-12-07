odoo.define('web_editor.BodyManager', function (require) {
'use strict';

var weContext = require('web_editor.context');
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Automatically add the web_editor context.
     *
     * @override
     */
    _call_service: function (event) {
        if (event.data.service === 'ajax' && event.data.method === 'rpc') {
            var route = event.data.args[0];
            if (_.str.startsWith(route, '/web/dataset/call_kw/')) {
                var params = event.data.args[1];
                var options = event.data.args[2];
                params.kwargs.context = _.extend({}, weContext.get(), params.kwargs.context || {});
                if (options) {
                    params.kwargs.context = _.omit(params.kwargs.context, options.noContextKeys);
                    event.data.args[2] = _.omit(options, 'noContextKeys');
                }
                params.kwargs.context = JSON.parse(JSON.stringify(params.kwargs.context));
            }
        }
        return ServiceProviderMixin._call_service.apply(this, arguments);
    },
});
return BodyManager;
});
