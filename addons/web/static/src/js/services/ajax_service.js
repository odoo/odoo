odoo.define('web.AjaxService', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var core = require('web.core');
var session = require('web.session');

var AjaxService = AbstractService.extend({
    rpc: function (route, args, options, target) {
        var rpcPromise;
        var promise = new Promise(function (resolve, reject) {
            rpcPromise = session.rpc(route, args, options);
            rpcPromise.then(function (result) {
                if (!target.isDestroyed()) {
                    resolve(result);
                }
            }).guardedCatch(function (reason) {
                if (!target.isDestroyed()) {
                    reject(reason);
                }
            });
        });
        promise.abort = rpcPromise.abort.bind(rpcPromise);
        return promise;
    },
});

core.serviceRegistry.add('ajax', AjaxService);

return AjaxService;

});
