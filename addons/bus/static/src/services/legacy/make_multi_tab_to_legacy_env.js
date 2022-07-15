/** @odoo-module **/

import { registry } from '@web/core/registry';

export function makeMultiTabToLegacyEnv(legacyEnv) {
    return {
        dependencies: ['multiTab'],
        start(_, { multiTab }) {
            legacyEnv.services['multiTab'] = multiTab;
        },
    };
}

registry.category('wowlToLegacyServiceMappers').add('multi_tab_to_legacy_env', makeMultiTabToLegacyEnv);
