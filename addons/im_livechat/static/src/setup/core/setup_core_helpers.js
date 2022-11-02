/** @odoo-module **/

import { isAvailable, options, serverUrl } from 'im_livechat.loaderData';

import { publicLivechatService } from '@im_livechat/services/public_livechat_service';

import { setupCoreMessaging } from '@mail/setup/core/setup_core_helpers';

import { registry } from '@web/core/registry';


export function setupCoreLivechat() {
    setupCoreMessaging({
        publicLivechatGlobal: { isAvailable, options, serverUrl },
    });
    registry.category('services')
        .add('public_livechat_service', publicLivechatService);
}
