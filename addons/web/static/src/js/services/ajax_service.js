odoo.define('web.AjaxService', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var ajax = require('web.ajax');
var core = require('web.core');
var session = require('web.session');

var AjaxService = AbstractService.extend({
    loadFile: ajax.loadFile,
    loadOwlXML: function(urls) {
        this.globalProms = this.globalProms || {};
        if (!urls) {
            return Promise.all(Object.values(this.globalProms));
        }
        const currentProms = [];
        for (const url of urls) {
            let urlProm = this.globalProms[url];
            if (!urlProm) {
                urlProm = this.loadFile(url);
                this.globalProms[url] = urlProm;
            }
            currentProms.push(urlProm);
        }
        return Promise.all(currentProms);
    },
    /**
     * @param {Object} libs - @see ajax.loadLibs
     * @param {Object} [context] - @see ajax.loadLibs
     */
    loadLibs: function (libs, context) {
        return ajax.loadLibs(libs, context);
    },
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
