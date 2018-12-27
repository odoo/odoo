odoo.define('web.AjaxService', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var core = require('web.core');
var session = require('web.session');

var AjaxService = AbstractService.extend({
    rpc: function (route, args, options, target) {
        var def = $.Deferred();
        var promise = def.promise();
        var xhrDef = session.rpc(route, args, options);
        promise.abort = xhrDef.abort.bind(xhrDef);
        xhrDef.then(function () {
            if (!target.isDestroyed()) {
                def.resolve.apply(def, arguments);
            }
        }).fail(function () {
            if (!target.isDestroyed()) {
                def.reject.apply(def, arguments);
            }
        });
        return promise;
    },
});

core.serviceRegistry.add('ajax', AjaxService);

return AjaxService;

});
