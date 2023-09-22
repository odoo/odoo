/** @odoo-module **/

import { SERVICES_METADATA } from "@web/env";
import {
    ConnectionAbortedError,
    ConnectionLostError,
    RPCError,
} from "@web/core/network/rpc_service";

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
                        if (reason instanceof RPCError || reason instanceof ConnectionLostError) {
                            // we do not reject an error here because we want to pass through
                            // the legacy guardedCatch code
                            reject({ message: reason, event: $.Event(), legacy: true });
                        } else if (reason instanceof ConnectionAbortedError) {
                            reject({ message: reason.message, event: $.Event("abort") });
                        } else {
                            reject(reason);
                        }
                    }
                });
        });
    };
}

var ServicesMixin = {
    bindService: function (serviceName) {
        const { services } = owl.Component.env;
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
    /**
     * Displays a notification.
     *
     * @param {Object} options
     * @param {string} [options.title]
     * @param {string} [options.subtitle]
     * @param {string} [options.message]
     * @param {string} [options.type='warning'] 'info', 'success', 'warning', 'danger' or ''
     * @param {boolean} [options.sticky=false]
     * @param {string} [options.className]
     */
    displayNotification: function (options) {
        return this.call('notification', 'notify', options);
    },
};

export default ServicesMixin;
