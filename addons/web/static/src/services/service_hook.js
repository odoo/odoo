/** @odoo-module **/

import { SPECIAL_METHOD } from "./launcher";

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
  if (service && SPECIAL_METHOD in service) {
    return service[SPECIAL_METHOD](component, service);
  }
  return service;
}
