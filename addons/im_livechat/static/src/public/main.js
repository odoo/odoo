/** @odoo-module **/

import { publicLivechatService } from '@im_livechat/services/public_livechat_service';
import { isAvailable, options, serverUrl } from 'im_livechat.loaderData';

import { insertAndReplace } from '@mail/model/model_field_command';
import { messagingService } from '@mail/services/messaging_service';
import { makeMessagingToLegacyEnv } from '@mail/utils/make_messaging_to_legacy_env';

import { registry } from '@web/core/registry';

const messagingValuesService = {
    start() {
        return {
            publicLivechatGlobal: insertAndReplace({ isAvailable, options, serverUrl }),
        };
    }
};

const serviceRegistry = registry.category('services');
serviceRegistry.add('messaging', messagingService);
serviceRegistry.add('messagingValues', messagingValuesService);
serviceRegistry.add('public_livechat_service', publicLivechatService);

registry.category('wowlToLegacyServiceMappers').add('make_messaging_to_legacy_env', makeMessagingToLegacyEnv);
