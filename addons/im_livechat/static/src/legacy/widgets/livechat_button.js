/** @odoo-module **/

import config from 'web.config';
import core from 'web.core';
import session from 'web.session';
import time from 'web.time';
import utils from 'web.utils';
import Widget from 'web.Widget';

import { LIVECHAT_COOKIE_HISTORY } from 'im_livechat.legacy.im_livechat.Constants';
import Feedback from '@im_livechat/legacy/widgets/feedback/feedback';
import PublicLivechatMessage from '@im_livechat/legacy/models/public_livechat_message';

import { clear, insertAndReplace } from '@mail/model/model_field_command';

const _t = core._t;
const QWeb = core.qweb;

const LivechatButton = Widget.extend({
    className: 'openerp o_livechat_button d-print-none',
    custom_events: {
        'close_chat_window': '_onCloseChatWindow',
        'post_message_chat_window': '_onPostMessageChatWindow',
        'save_chat_window': '_onSaveChatWindow',
        'updated_typing_partners': '_onUpdatedTypingPartners',
        'updated_unread_counter': '_onUpdatedUnreadCounter',
    },
    events: {
        'click': '_openChat'
    },
    init(parent, messaging) {
        this._super(parent);
        this.messaging = messaging;
        this.options = _.defaults(this.messaging.publicLivechatOptions || {});
    },
    async willStart() {
        this.messaging.livechatButtonView.update({ widget: this });
        const cookie = utils.get_cookie('im_livechat_session');
        if (cookie) {
            const channel = JSON.parse(cookie);
            const history = await session.rpc('/mail/chat_history', {uuid: channel.uuid, limit: 100});
            history.reverse();
            this.messaging.livechatButtonView.update({ history });
            for (const message of this.messaging.livechatButtonView.history) {
                message.body = utils.Markup(message.body);
            }
        } else {
            const result = await session.rpc('/im_livechat/init', {channel_id: this.messaging.livechatButtonView.channelId});
            if (!result.available_for_me) {
                return Promise.reject();
            }
            this.messaging.livechatButtonView.update({ rule: result.rule });
        }
        return this._loadQWebTemplate();
    },
    start() {
        this.$el.text(this.messaging.livechatButtonView.buttonText);
        if (this.messaging.livechatButtonView.history) {
            for (const m of this.messaging.livechatButtonView.history) {
                this._addMessage(m);
            }
            this._openChat();
        } else if (!config.device.isMobile && this.messaging.livechatButtonView.rule.action === 'auto_popup') {
            const autoPopupCookie = utils.get_cookie('im_livechat_auto_popup');
            if (!autoPopupCookie || JSON.parse(autoPopupCookie)) {
                this.messaging.livechatButtonView.update({
                    autoOpenChatTimeout: setTimeout(this._openChat.bind(this), this.messaging.livechatButtonView.rule.auto_popup_timer * 1000),
                });
            }
        }
        this.call('bus_service', 'onNotification', this._onNotification.bind(this));
        if (this.messaging.livechatButtonView.buttonBackgroundColor) {
            this.$el.css('background-color', this.messaging.livechatButtonView.buttonBackgroundColor);
        }
        if (this.messaging.livechatButtonView.buttonTextColor) {
            this.$el.css('color', this.messaging.livechatButtonView.buttonTextColor);
        }

        // If website_event_track installed, put the livechat banner above the PWA banner.
        const pwaBannerHeight = $('.o_pwa_install_banner').outerHeight(true);
        if (pwaBannerHeight) {
            this.$el.css('bottom', pwaBannerHeight + 'px');
        }

        return this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------


    /**
     * @private
     * @param {Object} data
     * @param {Object} [options={}]
     */
    _addMessage(data, options) {
        options = Object.assign({}, this.options, options, {
            serverURL: this.messaging.livechatButtonView.serverUrl,
        });
        const message = new PublicLivechatMessage(this, data, options);

        const hasAlreadyMessage = _.some(this.messaging.livechatButtonView.messages, function (msg) {
            return message.getID() === msg.getID();
        });
        if (hasAlreadyMessage) {
            return;
        }

        if (this.messaging.livechatButtonView.publicLivechat && this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat) {
            this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat.addMessage(message);
        }

        if (options && options.prepend) {
            this.messaging.livechatButtonView.update({
                messages: [message, ...this.messaging.livechatButtonView.messages],
            });
        } else {
            this.messaging.livechatButtonView.update({
                messages: [...this.messaging.livechatButtonView.messages, message],
            });
        }
    },
    /**
     * @private
     */
    _askFeedback() {
        this.messaging.livechatButtonView.chatWindow.legacyChatWindow.$('.o_thread_composer input').prop('disabled', true);

        const feedback = new Feedback(this, this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat);
        this.messaging.livechatButtonView.chatWindow.legacyChatWindow.replaceContentWith(feedback);

        feedback.on('send_message', this, this._sendMessage);
        feedback.on('feedback_sent', this, this._closeChat);
    },
    /**
     * @private
     */
    _closeChat() {
        this.messaging.livechatButtonView.update({ chatWindow: clear() });
        utils.set_cookie('im_livechat_session', "", -1); // remove cookie
    },
    /**
     * @private
     * @param {Object} notification
     * @param {Object} notification.payload
     * @param {string} notification.type
     */
    _handleNotification({ payload, type }) {
        switch (type) {
            case 'im_livechat.history_command': {
                if (payload.id !== this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._id) {
                    return;
                }
                const cookie = utils.get_cookie(LIVECHAT_COOKIE_HISTORY);
                const history = cookie ? JSON.parse(cookie) : [];
                session.rpc('/im_livechat/history', {
                    pid: this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._operatorPID[0],
                    channel_uuid: this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._uuid,
                    page_history: history,
                });
                return;
            }
            case 'mail.channel.member/typing_status': {
                if (payload.channel_id !== this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._id) {
                    return;
                }
                const partnerID = payload.partner_id;
                if (partnerID === this.messaging.livechatButtonView.currentPartnerId) {
                    // ignore typing display of current partner.
                    return;
                }
                if (payload.is_typing) {
                    this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat.registerTyping({ partnerID });
                } else {
                    this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat.unregisterTyping({ partnerID });
                }
                return;
            }
            case 'mail.channel/new_message': {
                if (payload.id !== this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._id) {
                    return;
                }
                const notificationData = payload.message;
                // If message from notif is already in chatter messages, stop handling
                if (this.messaging.livechatButtonView.messages.some(message => message.getID() === notificationData.id)) {
                    return;
                }
                notificationData.body = utils.Markup(notificationData.body);
                this._addMessage(notificationData);
                if (this.messaging.livechatButtonView.chatWindow.legacyChatWindow.isFolded() || !this.messaging.livechatButtonView.chatWindow.legacyChatWindow.isAtBottom()) {
                    this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._unreadCounter++;
                }
                this._renderMessages();
                return;
            }
            case 'mail.message/insert': {
                const message = this.messaging.livechatButtonView.messages.find(message => message._id === payload.id);
                if (!message) {
                    return;
                }
                message._body = utils.Markup(payload.body);
                this._renderMessages();
                return;
            }
        }
    },
    /**
     * @private
     */
    _loadQWebTemplate() {
        return session.rpc('/im_livechat/load_templates').then(function (templates) {
            for (let template of templates) {
                QWeb.add_template(template);
            }
        });
    },
    /**
     * @private
     */
    _openChat: _.debounce(function () {
        if (this.messaging.livechatButtonView.isOpeningChat) {
            return;
        }
        const cookie = utils.get_cookie('im_livechat_session');
        let def;
        this.messaging.livechatButtonView.update({ isOpeningChat: true });
        clearTimeout(this.messaging.livechatButtonView.autoOpenChatTimeout);
        if (cookie) {
            def = Promise.resolve(JSON.parse(cookie));
        } else {
            // re-initialize messages cache
            this.messaging.livechatButtonView.update({ messages: clear() });
            def = session.rpc(
                '/im_livechat/get_session',
                this._prepareGetSessionParameters(),
                { shadow: true },
            );
        }
        def.then((livechatData) => {
            if (!livechatData || !livechatData.operator_pid) {
                try {
                    this.displayNotification({
                        message: _t("No available collaborator, please try again later."),
                        sticky: true,
                    });
                } catch (_err) {
                    /**
                     * Failure in displaying notification happens when
                     * notification service doesn't exist, which is the case in
                     * external lib. We don't want notifications in external
                     * lib at the moment because they use bootstrap toast and
                     * we don't want to include boostrap in external lib.
                     */
                    console.warn(_t("No available collaborator, please try again later."));
                }
            } else {
                this.messaging.livechatButtonView.update({
                    publicLivechat: insertAndReplace({ data: livechatData }),
                });
                return this._openChatWindow().then(() => {
                    if (!this.messaging.livechatButtonView.history) {
                        this._sendWelcomeMessage();
                    }
                    this._renderMessages();
                    this.call('bus_service', 'addChannel', this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._uuid);
                    this.call('bus_service', 'startPolling');

                    utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat.toData()), true), 60 * 60);
                    utils.set_cookie('im_livechat_auto_popup', JSON.stringify(false), 60 * 60);
                    if (livechatData.operator_pid[0]) {
                        // livechatData.operator_pid contains a tuple (id, name)
                        // we are only interested in the id
                        const operatorPidId = livechatData.operator_pid[0];
                        const oneWeek = 7 * 24 * 60 * 60;
                        utils.set_cookie('im_livechat_previous_operator_pid', operatorPidId, oneWeek);
                    }
                });
            }
        }).then(() => {
            this.messaging.livechatButtonView.update({ isOpeningChat: false });
        }).guardedCatch(() => {
            this.messaging.livechatButtonView.update({ isOpeningChat: false });
        });
    }, 200, true),
    /**
     * Will try to get a previous operator for this visitor.
     * If the visitor already had visitor A, it's better for his user experience
     * to get operator A again.
     *
     * The information is stored in the 'im_livechat_previous_operator_pid' cookie.
     *
     * @private
     * @return {integer} operator_id.partner_id.id if the cookie is set
     */
     _get_previous_operator_id() {
        const cookie = utils.get_cookie('im_livechat_previous_operator_pid');
        if (cookie) {
            return cookie;
        }

        return null;
    },
    /**
     * @private
     * @return {Promise}
     */
     _openChatWindow() {
        this.messaging.livechatButtonView.update({ chatWindow: insertAndReplace() });
        return this.messaging.livechatButtonView.chatWindow.legacyChatWindow.appendTo($('body')).then(() => {
            const cssProps = { bottom: 0 };
            cssProps[_t.database.parameters.direction === 'rtl' ? 'left' : 'right'] = 0;
            this.messaging.livechatButtonView.chatWindow.legacyChatWindow.$el.css(cssProps);
            this.$el.hide();
        });
    },
    /**
     * @private
     */
    _prepareGetSessionParameters() {
        return {
            channel_id: this.messaging.livechatButtonView.channelId,
            anonymous_name: this.messaging.livechatButtonView.defaultUsername,
            previous_operator_id: this._get_previous_operator_id(),
        };
    },
    /**
     * @private
     */
     _renderMessages() {
        const shouldScroll = !this.messaging.livechatButtonView.chatWindow.legacyChatWindow.isFolded() && this.messaging.livechatButtonView.chatWindow.legacyChatWindow.isAtBottom();
        this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._messages = this.messaging.livechatButtonView.messages;
        this.messaging.livechatButtonView.chatWindow.legacyChatWindow.render();
        if (shouldScroll) {
            this.messaging.livechatButtonView.chatWindow.legacyChatWindow.scrollToBottom();
        }
    },
    /**
     * @private
     * @param {Object} message
     * @return {Promise}
     */
     _sendMessage(message) {
        this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._notifyMyselfTyping({ typing: false });
        return session
            .rpc('/mail/chat_post', { uuid: this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._uuid, message_content: message.content })
            .then((messageId) => {
                if (!messageId) {
                    try {
                        this.displayNotification({
                            message: _t("Session expired... Please refresh and try again."),
                            sticky: true,
                        });
                    } catch (_err) {
                        /**
                         * Failure in displaying notification happens when
                         * notification service doesn't exist, which is the case
                         * in external lib. We don't want notifications in
                         * external lib at the moment because they use bootstrap
                         * toast and we don't want to include boostrap in
                         * external lib.
                         */
                        console.warn(_t("Session expired... Please refresh and try again."));
                    }
                    this._closeChat();
                }
                this.messaging.livechatButtonView.chatWindow.legacyChatWindow.scrollToBottom();
            });
    },
    /**
     * @private
     */
    _sendWelcomeMessage() {
        if (this.messaging.livechatButtonView.defaultMessage) {
            this._addMessage({
                id: '_welcome',
                attachment_ids: [],
                author_id: this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._operatorPID,
                body: this.messaging.livechatButtonView.defaultMessage,
                date: time.datetime_to_str(new Date()),
                model: "mail.channel",
                res_id: this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat._id,
            }, { prepend: true });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onCloseChatWindow(ev) {
        ev.stopPropagation();
        const isComposerDisabled = this.messaging.livechatButtonView.chatWindow.legacyChatWindow.$('.o_thread_composer input').prop('disabled');
        const shouldAskFeedback = !isComposerDisabled && this.messaging.livechatButtonView.messages.find(function (message) {
            return message.getID() !== '_welcome';
        });
        if (shouldAskFeedback) {
            this.messaging.livechatButtonView.chatWindow.legacyChatWindow.toggleFold(false);
            this._askFeedback();
        } else {
            this._closeChat();
        }
        this._visitorLeaveSession();
    },
    /**
     * @private
     * @param {Array[]} notifications
     */
     _onNotification(notifications) {
        for (let notification of notifications) {
            this._handleNotification(notification);
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data.messageData
     */
    _onPostMessageChatWindow(ev) {
        ev.stopPropagation();
        const messageData = ev.data.messageData;
        this._sendMessage(messageData).guardedCatch((reason) => {
            reason.event.preventDefault();
            return this._sendMessage(messageData); // try again just in case
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSaveChatWindow(ev) {
        ev.stopPropagation();
        utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(this.messaging.livechatButtonView.publicLivechat.legacyPublicLivechat.toData()), true), 60 * 60);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedTypingPartners(ev) {
        ev.stopPropagation();
        this.messaging.livechatButtonView.chatWindow.legacyChatWindow.renderHeader();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedUnreadCounter(ev) {
        ev.stopPropagation();
        this.messaging.livechatButtonView.chatWindow.legacyChatWindow.renderHeader();
    },
    /**
     * @private
     * Called when the visitor leaves the livechat chatter the first time (first click on X button)
     * this will deactivate the mail_channel, notify operator that visitor has left the channel.
     */
     _visitorLeaveSession() {
        const cookie = utils.get_cookie('im_livechat_session');
        if (cookie) {
            const channel = JSON.parse(cookie);
            session.rpc('/im_livechat/visitor_leave_session', {uuid: channel.uuid});
            utils.set_cookie('im_livechat_session', "", -1); // remove cookie
        }
    },
});

export default LivechatButton;
