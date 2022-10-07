/** @odoo-module **/

import { DiscussContainer } from '@mail/components/discuss_container/discuss_container';
import { mainComponentsService } from '@mail/services/main_components_service';
import { messagingService } from '@mail/services/messaging_service';
import { systrayService } from '@mail/services/systray_service';
import { makeMessagingToLegacyEnv } from '@mail/utils/make_messaging_to_legacy_env';

import { registry } from '@web/core/registry';

const messagingValuesService = {
    start() {
        return {};
    },
};

const serviceRegistry = registry.category('services');
serviceRegistry.add('main_components_service', mainComponentsService);
serviceRegistry.add('messaging', messagingService);
serviceRegistry.add('messagingValues', messagingValuesService);
serviceRegistry.add('systray_service', systrayService);
serviceRegistry.add('messaging_service_to_legacy_env', makeMessagingToLegacyEnv(owl.Component.env));

registry.category('actions').add('mail.action_discuss', DiscussContainer);
