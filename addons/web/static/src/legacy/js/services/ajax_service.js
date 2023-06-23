/** @odoo-module **/

import AbstractService from "@web/legacy/js/core/abstract_service";
import core from "@web/legacy/js/services/core";
import session from "web.session";

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

export default AjaxService;
