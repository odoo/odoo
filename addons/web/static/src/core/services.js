import { Plugin, Resource, types as t } from "@odoo/owl";

/**
 * Main resources for global plugins (aka 'services').
 * All services registered here will be started by the framework
 */
export const services = new Resource({
    name: "services",
    validation: t.constructor(Plugin),
});
