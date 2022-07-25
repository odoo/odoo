/** @odoo-module **/
import { registry } from '@web/core/registry';

import { messagingService } from '@mail/services/messaging_service';
import { makeMessagingToLegacyEnv } from '@mail/utils/make_messaging_to_legacy_env';

/**
 * Setup the messaging service and its dependencies.
 */
export function prepareMessaging() {
    registry.category('services').add('messaging', messagingService);
    registry.category('services').add('messagingValues', {
        start() {
            return {};
        },
    });
    registry.category('services').add('messaging_to_legacy_env', makeMessagingToLegacyEnv(owl.Component.env));
}
