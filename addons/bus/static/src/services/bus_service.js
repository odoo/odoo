/** @odoo-module **/

import { CrossTab } from '@bus/crosstab_bus';

import { registry } from '@web/core/registry';

export const busService = {
    dependencies: ['notification', 'presence', 'rpc', 'multi_tab'],
    start(env, services) {
        return new CrossTab(env, services);
    },
};
registry.category('services').add('bus_service', busService);
