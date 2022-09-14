/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { increment } from '@mail/model/model_field_command';

import session from 'web.session';
import utils from 'web.utils';
import {getCookie} from 'web.utils.cookies';

registerModel({
    name: 'PublicLivechatGlobalNotificationHandler',
    lifecycleHooks: {
        _created() {
            this.env.services['bus_service'].addChannel(this.global.PublicLivechatGlobal.publicLivechat.uuid);
            this.env.services['bus_service'].addEventListener('notification', this._onNotification);
        },
    },
    recordMethods: {
        /**
         * @private
         * @param {Object} notification
         * @param {Object} notification.payload
         * @param {string} notification.type
         */
        _handleNotification({ payload, type }) {
            switch (type) {
                case 'im_livechat.history_command': {
                    if (payload.id !== this.global.PublicLivechatGlobal.publicLivechat.id) {
                        return;
                    }
                    const cookie = getCookie(this.global.PublicLivechatGlobal.LIVECHAT_COOKIE_HISTORY);
                    const history = cookie ? JSON.parse(cookie) : [];
                    session.rpc('/im_livechat/history', {
                        pid: this.global.PublicLivechatGlobal.publicLivechat.operator.id,
                        channel_uuid: this.global.PublicLivechatGlobal.publicLivechat.uuid,
                        page_history: history,
                    });
                    return;
                }
                case 'mail.channel.member/typing_status': {
                    const channelMemberData = payload;
                    if (channelMemberData.channel.id !== this.global.PublicLivechatGlobal.publicLivechat.id) {
                        return;
                    }
                    if (!channelMemberData.persona.partner) {
                        return;
                    }
                    if (channelMemberData.persona.partner.id === this.global.PublicLivechatGlobal.livechatButtonView.currentPartnerId) {
                        // ignore typing display of current partner.
                        return;
                    }
                    if (channelMemberData.isTyping) {
                        this.global.PublicLivechatGlobal.publicLivechat.widget.registerTyping({ partnerID: channelMemberData.persona.partner.id });
                    } else {
                        this.global.PublicLivechatGlobal.publicLivechat.widget.unregisterTyping({ partnerID: channelMemberData.persona.partner.id });
                    }
                    return;
                }
                case 'mail.channel/new_message': {
                    if (payload.id !== this.global.PublicLivechatGlobal.publicLivechat.id) {
                        return;
                    }
                    const notificationData = payload.message;
                    // If message from notif is already in chatter messages, stop handling
                    if (this.global.PublicLivechatGlobal.messages.some(message => message.id === notificationData.id)) {
                        return;
                    }
                    notificationData.body = utils.Markup(notificationData.body);
                    this.global.PublicLivechatGlobal.livechatButtonView.addMessage(notificationData);
                    if (this.global.PublicLivechatGlobal.publicLivechat.isFolded || !this.global.PublicLivechatGlobal.chatWindow.publicLivechatView.widget.isAtBottom()) {
                        this.global.PublicLivechatGlobal.publicLivechat.update({ unreadCounter: increment() });
                    }
                    this.global.PublicLivechatGlobal.chatWindow.renderMessages();
                    return;
                }
                case 'mail.message/insert': {
                    const message = this.global.PublicLivechatGlobal.messages.find(message => message.id === payload.id);
                    if (!message) {
                        return;
                    }
                    message.widget._body = utils.Markup(payload.body);
                    this.global.PublicLivechatGlobal.chatWindow.renderMessages();
                    return;
                }
            }
        },
        /**
         * @private
         * @param {CustomEvent} ev
         * @param {Array[]} [ev.detail] Notifications coming from the bus.
         */
        _onNotification({ detail: notifications }) {
            for (const notification of notifications) {
                this._handleNotification(notification);
            }
        },
    },
    fields: {
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'notificationHandler',
        }),
    },
});
