odoo.define('root.widget', function (require) {
"use strict";

var ServiceProviderMixin = require('web.ServiceProviderMixin');
var Widget = require('web.Widget');

/**
 * This is the root widget in the frontend bundle when website is not installed.
 *
 * This widget is important, because the tour manager needs a root widget in
 * order to work. The root widget must be a service provider with the ajax
 * service, so that the tour manager can let the server know when tours have
 * been consumed.
 */
var PublicRootWidget = Widget.extend(ServiceProviderMixin, {
    init: function () {
        this._super.apply(this, arguments);
        ServiceProviderMixin.init.call(this);
    }
});

return new PublicRootWidget();
});
