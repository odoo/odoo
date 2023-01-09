/** @odoo-module **/

import { registry } from '@web/core/registry';

export function makeBusServiceToLegacyEnv(legacyEnv) {
    return {
        dependencies: ['bus_service'],
        start(_, { bus_service }) {
            legacyEnv.services['bus_service'] = bus_service;
        },
    };
}

registry.category('wowlToLegacyServiceMappers').add('bus_service_to_legacy_env', makeBusServiceToLegacyEnv);
