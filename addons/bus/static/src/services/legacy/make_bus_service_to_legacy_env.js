/** @odoo-module **/

export function makeBusServiceToLegacyEnv(legacyEnv) {
    return {
        dependencies: ['bus_service'],
        start(_, { bus_service }) {
            legacyEnv.services['bus_service'] = bus_service;
        },
    };
}
