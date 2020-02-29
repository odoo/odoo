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

    // ServiceProvider
    const services = {}; // dict containing deployed service instances
    const UndeployedServices = {}; // dict containing classes of undeployed services
    function _deployServices() {
        let done = false;
        while (!done) {
            const serviceName = _.findKey(UndeployedServices, Service => {
                // no missing dependency
                return !_.some(Service.prototype.dependencies, depName => {
                    return !services[depName];
                });
            });
            if (serviceName) {
                const Service = UndeployedServices[serviceName];
                // we created a patched version of the Service in which the 'trigger_up'
                // function directly calls the requested service, instead of triggering
                // a 'call_service' event up, which wouldn't work as services have
                // no parent
                const PatchedService = Service.extend({
                    _trigger_up: function (ev) {
                        this._super(...arguments);
                        if (!ev.is_stopped() && ev.name === 'call_service') {
                            const payload = ev.data;
                            let args = payload.args || [];
                            if (payload.service === 'ajax' && payload.method === 'rpc') {
                                // ajax service uses an extra 'target' argument for rpc
                                args = args.concat(ev.target);
                            }
                            const service = services[payload.service];
                            const result = service[payload.method].apply(service, args);
                            payload.callback(result);
                        } else {
                            // historically, some services could reach the webclient
                            // by triggering events up, as the webclient was their
                            // parent. Since services have been moved to the env,
                            // this is no longer the case, so we re-trigger those
                            // events on the bus for now. Eventually, services
                            // should stop triggering events up (they can still
                            // communicate with other services through the env).
                            bus.trigger('legacy_webclient_request', ev);
                        }
                    },
                });
                const service = new PatchedService();
                services[serviceName] = service;
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
        if (serviceName in services || serviceName in UndeployedServices) {
            throw new Error(`Service ${serviceName} is already loaded.`);
        }
        UndeployedServices[serviceName] = Service;
        _deployServices();
    });
    _deployServices();

    // There should be as much dependencies as possible in the env object.
    // This will allow an easier testing of components.
    // See https://github.com/odoo/owl/blob/master/doc/reference/environment.md#content-of-an-environment
    // for more information on environments.
    return {
        _lt,
        _t,
        bus,
        dataManager,
        device,
        isDebug,
        qweb,
        services: Object.assign(services, {
            ajaxJsonRPC,
            blockUI,
            getCookie,
            httpRequest,
            navigate,
            reloadPage,
            rpc: performRPC,
            setCookie,
            unblockUI,
        }),
        session,
    };
});
