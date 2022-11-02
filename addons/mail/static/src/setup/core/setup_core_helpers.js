/** @odoo-module **/

import { registry } from '@web/core/registry';

import { messagingService } from '@mail/services/messaging_service';
import { makeMessagingToLegacyEnv } from '@mail/utils/make_messaging_to_legacy_env';

export function setupCoreMessaging(messagingValues = {}) {
    const messagingValuesService = {
        dependencies: [],
        start() {
            return messagingValues;
        }
    };
    registry.category('services')
        .add('messaging', messagingService)
        .add('messagingValues', messagingValuesService);
    registry.category('wowlToLegacyServiceMappers')
        .add('make_messaging_to_legacy_env', makeMessagingToLegacyEnv);
}
