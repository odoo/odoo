/** @odoo-module **/

import { messagingService } from '@mail/services/messaging_service';
import { makeMessagingToLegacyEnv } from '@mail/utils/make_messaging_to_legacy_env';

import { registry } from '@web/core/registry';

// Wait for legacyEnv being set on `owl.Component.env`
import '@web/legacy/js/public/public_root_instance';

const messagingValuesService = {
    start() {
        return {
            isInPublicLivechat: true,
        };
    }
};

const serviceRegistry = registry.category('services');
serviceRegistry.add('messaging', messagingService);
serviceRegistry.add('messagingValues', messagingValuesService);
serviceRegistry.add('messaging_service_to_legacy_env', makeMessagingToLegacyEnv(owl.Component.env));
