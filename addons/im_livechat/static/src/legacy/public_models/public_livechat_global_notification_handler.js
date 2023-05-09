/** @odoo-module **/

import { increment, one, Model } from "@im_livechat/legacy/model";

import session from "web.session";
import utils from "web.utils";
import { getCookie } from "web.utils.cookies";

Model({
    name: "PublicLivechatGlobalNotificationHandler",
    lifecycleHooks: {
        _created() {
            this.env.services["bus_service"].addChannel(
                this.messaging.publicLivechatGlobal.publicLivechat.uuid
            );
            this.env.services["bus_service"].subscribe(
                "im_livechat.history_command",
                this._handleLivechatHistoryCommand
            );
            this.env.services["bus_service"].subscribe(
                "discuss.channel.member/typing_status",
                this._handleTypingStatus
            );
            this.env.services["bus_service"].subscribe(
                "discuss.channel/new_message",
                this._handleNewMessage
            );
        },
    },
    recordMethods: {
        _handleLivechatHistoryCommand(notifPayload) {
            if (notifPayload.id !== this.messaging.publicLivechatGlobal.publicLivechat.id) {
                return;
            }
            const cookie = getCookie(this.messaging.publicLivechatGlobal.LIVECHAT_COOKIE_HISTORY);
            const history = cookie ? JSON.parse(cookie) : [];
            session.rpc("/im_livechat/history", {
                pid: this.messaging.publicLivechatGlobal.publicLivechat.operator.id,
                channel_uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
                page_history: history,
            });
        },
        _handleTypingStatus(channelMemberData) {
            if (
                !this.messaging.publicLivechatGlobal.chatWindow ||
                !this.messaging.publicLivechatGlobal.chatWindow.exists()
            ) {
                return;
            }
            if (
                channelMemberData.channel.id !==
                this.messaging.publicLivechatGlobal.publicLivechat.id
            ) {
                return;
            }
            if (!channelMemberData.persona.partner) {
                return;
            }
            if (
                channelMemberData.persona.partner.id ===
                this.messaging.publicLivechatGlobal.livechatButtonView.currentPartnerId
            ) {
                // ignore typing display of current partner.
                return;
            }
            if (channelMemberData.isTyping) {
                this.messaging.publicLivechatGlobal.publicLivechat.widget.registerTyping({
                    partnerID: channelMemberData.persona.partner.id,
                });
            } else {
                this.messaging.publicLivechatGlobal.publicLivechat.widget.unregisterTyping({
                    partnerID: channelMemberData.persona.partner.id,
                });
            }
        },
        _handleNewMessage(notifPayload) {
            if (
                !this.messaging.publicLivechatGlobal.chatWindow ||
                !this.messaging.publicLivechatGlobal.chatWindow.exists()
            ) {
                return;
            }
            if (notifPayload.id !== this.messaging.publicLivechatGlobal.publicLivechat.id) {
                return;
            }
            const notificationData = notifPayload.message;
            // If message from notif is already in chatter messages, stop handling
            if (
                this.messaging.publicLivechatGlobal.messages.some(
                    (message) => message.id === notificationData.id
                )
            ) {
                return;
            }
            notificationData.body = utils.Markup(notificationData.body);
            this.messaging.publicLivechatGlobal.livechatButtonView.addMessage(notificationData);
            if (
                this.messaging.publicLivechatGlobal.publicLivechat.isFolded ||
                !this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.isAtBottom()
            ) {
                this.messaging.publicLivechatGlobal.publicLivechat.update({
                    unreadCounter: increment(),
                });
            }
            this.messaging.publicLivechatGlobal.chatWindow.renderMessages();
        },
        _handleRecordInsert(notifPayload) {
            const { Message: payload } = notifPayload;
            if (!payload) {
                return;
            }
            if (
                !this.messaging.publicLivechatGlobal.chatWindow ||
                !this.messaging.publicLivechatGlobal.chatWindow.exists()
            ) {
                return;
            }
            const message = this.messaging.publicLivechatGlobal.messages.find(
                (message) => message.id === payload.id
            );
            if (!message) {
                return;
            }
            message.widget._body = utils.Markup(payload.body);
            this.messaging.publicLivechatGlobal.chatWindow.renderMessages();
        },
    },
    fields: {
        publicLivechatGlobalOwner: one("PublicLivechatGlobal", {
            identifying: true,
            inverse: "notificationHandler",
        }),
    },
});
