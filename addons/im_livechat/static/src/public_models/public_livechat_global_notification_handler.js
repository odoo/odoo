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
            this.env.services['bus_service'].addChannel(this.messaging.publicLivechatGlobal.publicLivechat.uuid);
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
                    if (payload.id !== this.messaging.publicLivechatGlobal.publicLivechat.id) {
                        return;
                    }
                    const cookie = getCookie(this.messaging.publicLivechatGlobal.LIVECHAT_COOKIE_HISTORY);
                    const history = cookie ? JSON.parse(cookie) : [];
                    session.rpc('/im_livechat/history', {
                        pid: this.messaging.publicLivechatGlobal.publicLivechat.operator.id,
                        channel_uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
                        page_history: history,
                    });
                    return;
                }
                case 'mail.channel.member/typing_status': {
                    if (!this.messaging.publicLivechatGlobal.chatWindow || !this.messaging.publicLivechatGlobal.chatWindow.exists()) {
                        return;
                    }
                    const channelMemberData = payload;
                    if (channelMemberData.channel.id !== this.messaging.publicLivechatGlobal.publicLivechat.id) {
                        return;
                    }
                    if (!channelMemberData.persona.partner) {
                        return;
                    }
                    if (channelMemberData.persona.partner.id === this.messaging.publicLivechatGlobal.livechatButtonView.currentPartnerId) {
                        // ignore typing display of current partner.
                        return;
                    }
                    if (channelMemberData.isTyping) {
                        this.messaging.publicLivechatGlobal.publicLivechat.widget.registerTyping({ partnerID: channelMemberData.persona.partner.id });
                    } else {
                        this.messaging.publicLivechatGlobal.publicLivechat.widget.unregisterTyping({ partnerID: channelMemberData.persona.partner.id });
                    }
                    return;
                }
                case 'mail.channel/new_message': {
                    if (!this.messaging.publicLivechatGlobal.chatWindow || !this.messaging.publicLivechatGlobal.chatWindow.exists()) {
                        return;
                    }
                    if (payload.id !== this.messaging.publicLivechatGlobal.publicLivechat.id) {
                        return;
                    }
                    const notificationData = payload.message;
                    // If message from notif is already in chatter messages, stop handling
                    if (this.messaging.publicLivechatGlobal.messages.some(message => message.id === notificationData.id)) {
                        return;
                    }
                    notificationData.body = utils.Markup(notificationData.body);
                    this.messaging.publicLivechatGlobal.livechatButtonView.addMessage(notificationData);
                    if (this.messaging.publicLivechatGlobal.publicLivechat.isFolded || !this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.isAtBottom()) {
                        this.messaging.publicLivechatGlobal.publicLivechat.update({ unreadCounter: increment() });
                    }
                    this.messaging.publicLivechatGlobal.chatWindow.renderMessages();
                    return;
                }
                case 'mail.message/insert': {
                    if (!this.messaging.publicLivechatGlobal.chatWindow || !this.messaging.publicLivechatGlobal.chatWindow.exists()) {
                        return;
                    }
                    const message = this.messaging.publicLivechatGlobal.messages.find(message => message.id === payload.id);
                    if (!message) {
                        return;
                    }
                    message.widget._body = utils.Markup(payload.body);
                    this.messaging.publicLivechatGlobal.chatWindow.renderMessages();
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
