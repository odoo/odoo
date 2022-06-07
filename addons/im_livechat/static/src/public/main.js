/** @odoo-module **/

import LivechatButton from '@im_livechat/legacy/widgets/livechat_button';
import { isAvailable, options, serverUrl } from 'im_livechat.loaderData';

import { messagingService } from '@mail/services/messaging_service';
import { makeMessagingToLegacyEnv } from '@mail/utils/make_messaging_to_legacy_env';

import { registry } from '@web/core/registry';
import rootWidget from 'root.widget';

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

if (isAvailable) {
    const button = new LivechatButton(
        rootWidget,
        serverUrl,
        options,
    );
    button.appendTo(document.body);
    window.livechat_button = button;
}
