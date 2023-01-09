/** @odoo-module **/

import { registry } from '@web/core/registry';

export function makeMultiTabToLegacyEnv(legacyEnv) {
    return {
        dependencies: ['multi_tab'],
        start(_, { multi_tab }) {
            legacyEnv.services['multi_tab'] = multi_tab;
        },
    };
}

registry.category('wowlToLegacyServiceMappers').add('multi_tab_to_legacy_env', makeMultiTabToLegacyEnv);
