/** @odoo-module **/

import { SERVICES_METADATA } from "@web/env";
import { Component } from "@odoo/owl";

function protectMethod(widget, fn) {
    return function (...args) {
        return new Promise((resolve, reject) => {
            Promise.resolve(fn.call(this, ...args))
                .then((result) => {
                    if (!widget.isDestroyed()) {
                        resolve(result);
                    }
                })
                .catch((reason) => {
                    if (!widget.isDestroyed()) {
                        reject(reason);
                    }
                });
        });
    };
}

var ServicesMixin = {
    bindService: function (serviceName) {
        const { services } = Component.env;
        const service = services[serviceName];
        if (!service) {
            throw new Error(`Service ${serviceName} is not available`);
        }
        if (serviceName in SERVICES_METADATA) {
            if (service instanceof Function) {
                return protectMethod(this, service);
            } else {
                const methods = SERVICES_METADATA[serviceName];
                const result = Object.create(service);
                for (const method of methods) {
                    result[method] = protectMethod(this, service[method]);
                }
                return result;
            }
        }
        return service;
    },
    /**
     * @param  {string} service
     * @param  {string} method
     * @return {any} result of the service called
     */
    call: function (service, method) {
        var args = Array.prototype.slice.call(arguments, 2);
        var result;
        this.trigger_up('call_service', {
            service: service,
            method: method,
            args: args,
            callback: function (r) {
                result = r;
            },
        });
        return result;
    },
};

export default ServicesMixin;
