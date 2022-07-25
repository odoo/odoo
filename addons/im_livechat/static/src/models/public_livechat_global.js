/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

import utils from 'web.utils';

registerModel({
    name: 'PublicLivechatGlobal',
    identifyingFields: ['messaging'],
    lifecycleHooks: {
        _created() {
            // History tracking
            const page = window.location.href.replace(/^.*\/\/[^/]+/, '');
            const pageHistory = utils.get_cookie(this.LIVECHAT_COOKIE_HISTORY);
            let urlHistory = [];
            if (pageHistory) {
                urlHistory = JSON.parse(pageHistory) || [];
            }
            if (!_.contains(urlHistory, page)) {
                urlHistory.push(page);
                while (urlHistory.length > this.HISTORY_LIMIT) {
                    urlHistory.shift();
                }
                utils.set_cookie(this.LIVECHAT_COOKIE_HISTORY, JSON.stringify(urlHistory), 60 * 60 * 24); // 1 day cookie
            }
        },
    },
    fields: {
        HISTORY_LIMIT: attr({
            default: 15,
        }),
        LIVECHAT_COOKIE_HISTORY: attr({
            default: 'im_livechat_history',
        }),
        RATING_TO_EMOJI: attr({
            default: {
                5: "😊",
                3: "😐",
                1: "😞",
            },
        }),
        chatbotServerUrl: attr(),
        isAvailable: attr({
            default: false,
        }),
        notificationHandler: one('PublicLivechatGlobalNotificationHandler', {
            inverse: 'publicLivechatGlobalOwner',
            isCausal: true,
        }),
        options: attr({
            default: {},
        }),
        serverUrl: attr({
            default: '',
        }),
    },
});
