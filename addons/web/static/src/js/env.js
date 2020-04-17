odoo.define("web.env", function (require) {
    "use strict";

    const { jsonRpc } = require('web.ajax');
    const { device, isDebug } = require("web.config");
    const { _lt, _t, bus, serviceRegistry } = require("web.core");
    const dataManager = require('web.data_manager');
    const { blockUI, unblockUI } = require("web.framework");
    const rpc = require("web.rpc");
    const session = require("web.session");
    const utils = require("web.utils");

    const qweb = new owl.QWeb({ translateFn: _t });

    const env = {};

    function ajaxJsonRPC() {
        return jsonRpc(...arguments);
    }

    function getCookie() {
        return utils.get_cookie(...arguments);
    }

    function httpRequest(route, params = {}, readMethod = 'json') {
        const formData = new FormData();
        for (const key in params) {
            if (key === 'method') {
                continue;
            }
            const value = params[key];
            if (Array.isArray(value) && value.length) {
                for (const val of value) {
                    formData.append(key, val);
                }
            } else {
                formData.append(key, value);
            }
        }

        return fetch(route, {
            method: params.method || 'POST',
            body: formData,
        }).then(response => response[readMethod]());
    }

    function navigate(url, params) {
        window.location = $.param.querystring(url, params);
    }

    function performRPC(params, options) {
        const query = rpc.buildQuery(params);
        return session.rpc(query.route, query.params, options);
    }

    function reloadPage() {
        window.location.reload();
    }

    function setCookie() {
        utils.set_cookie(...arguments);
    }

    // There should be as much dependencies as possible in the env object.
    // This will allow an easier testing of components.
    // See https://github.com/odoo/owl/blob/master/doc/reference/environment.md#content-of-an-environment
    // for more information on environments.
    Object.assign(env, {
        _lt,
        _t,
        bus,
        dataManager,
        device,
        isDebug,
        qweb,
        services: {
            ajaxJsonRPC,
            blockUI,
            getCookie,
            httpRequest,
            navigate,
            reloadPage,
            rpc: performRPC,
            setCookie,
            unblockUI,
        },
        session,
    });

    // ServiceProvider
    const UndeployedServices = {}; // dict containing classes of undeployed services
    function _deployServices() {
        let done = false;
        while (!done) {
            const serviceName = _.findKey(UndeployedServices, Service => {
                // no missing dependency
                return !_.some(Service.prototype.dependencies, depName => {
                    return !env.services[depName];
                });
            });
            if (serviceName) {
                const Service = UndeployedServices[serviceName];
                const service = new Service(env);
                env.services[serviceName] = service;
                delete UndeployedServices[serviceName];
                service.start();
            } else {
                done = true;
            }
        }
    }
    _.each(serviceRegistry.map, (Service, serviceName) => {
        if (serviceName in UndeployedServices) {
            throw new Error(`Service ${serviceName} is already loaded.`);
        }
        UndeployedServices[serviceName] = Service;
    });
    serviceRegistry.onAdd((serviceName, Service) => {
        if (serviceName in env.services || serviceName in UndeployedServices) {
            throw new Error(`Service ${serviceName} is already loaded.`);
        }
        UndeployedServices[serviceName] = Service;
        _deployServices();
    });
    _deployServices();

    return env;
});
