/** @odoo-module **/

import LivechatButton from '@im_livechat/legacy/widgets/livechat_button';

import rootWidget from 'root.widget';

export const publicLivechatService = {
    dependencies: ['messaging'],
    async start(env, { messaging: messagingService }) {
        let livechatButton;
        const messaging = await messagingService.get();
        if (messaging.isPublicLivechatAvailable) {
            livechatButton = new LivechatButton(
                rootWidget,
                messaging.publicLivechatServerUrl,
                messaging.publicLivechatOptions,
            );
            livechatButton.appendTo(document.body);
        }

        return { livechatButton };
    },
};
