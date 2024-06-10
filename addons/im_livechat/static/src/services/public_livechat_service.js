/** @odoo-module **/

import LivechatButton from '@im_livechat/legacy/widgets/livechat_button';

import rootWidget from 'root.widget';

import {getCookie, deleteCookie} from 'web.utils.cookies';

export const publicLivechatService = {
    dependencies: ['messaging'],
    async start(env, { messaging: messagingService }) {
        const messaging = await messagingService.get();
        try {
            JSON.parse(decodeURIComponent(getCookie('im_livechat_session')));
        } catch {
            // Cookies are not supposed to contain non-ASCII characters.
            // However, some were set in the past. Let's clean them up.
            deleteCookie('im_livechat_session');
        }
        return {
            mountLivechatButton() {
                const livechatButton = new LivechatButton(rootWidget, messaging);
                livechatButton.appendTo(document.body).catch(error => {
                    console.info("Can't load 'LivechatButton' because:", error);
                });
                return livechatButton;
            },
        };
    },
};
