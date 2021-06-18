/** @odoo-module **/

import { SERVICES_METADATA } from "../env";

const { useComponent } = owl.hooks;

/**
 * Import a service into a component
 *
 * @param {string} serviceName
 * @returns {any}
 */
export function useService(serviceName) {
    const component = useComponent();
    const { services } = component.env;
    if (!(serviceName in services)) {
        throw new Error(`Service ${serviceName} is not available`);
    }
    const service = services[serviceName];
    if (serviceName in SERVICES_METADATA) {
        if (service instanceof Function) {
            return protectMethod(component, null, service);
        } else {
            const methods = SERVICES_METADATA[serviceName];
            const result = Object.create(service);
            for (let method of methods) {
                result[method] = protectMethod(component, service, service[method]);
            }
            return result;
        }
    }
    return service;
}

function protectMethod(component, caller, fn) {
    return async (...args) => {
        if (component.__owl__.status === 5 /* DESTROYED */) {
            throw new Error("Component is destroyed");
        }
        const result = await fn.call(caller, ...args);
        return component.__owl__.status === 5 ? new Promise(() => {}) : result;
    };
}
