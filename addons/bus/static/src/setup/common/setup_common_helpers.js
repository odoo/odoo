/** @odoo-module **/

import { registry } from '@web/core/registry';

import { makeMultiTabToLegacyEnv } from '@bus/services/legacy/make_multi_tab_to_legacy_env';
import { setupCoreBus } from '@bus/setup/core/setup_core_helpers';

export function setupCommonBus() {
    setupCoreBus();
    registry.category('wowlToLegacyServiceMappers')
        .add('multi_tab_service_to_legacy_env', makeMultiTabToLegacyEnv);
}
