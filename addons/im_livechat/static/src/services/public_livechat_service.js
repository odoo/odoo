/** @odoo-module **/

import LivechatButton from '@im_livechat/legacy/widgets/livechat_button';

import rootWidget from 'root.widget';

export const publicLivechatService = {
    dependencies: ['messaging'],
    async start(env, { messaging: messagingService }) {
        const messaging = await messagingService.get();
        if (messaging.publicLivechatGlobal.livechatButtonView) {
            const livechatButton = new LivechatButton(rootWidget, messaging);
            livechatButton.appendTo(document.body);
        }
    },
};
