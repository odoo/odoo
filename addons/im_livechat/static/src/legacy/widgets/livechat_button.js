/** @odoo-module **/

import config from 'web.config';
import core from 'web.core';
import session from 'web.session';
import time from 'web.time';
import utils from 'web.utils';
import Widget from 'web.Widget';

import { clear, insertAndReplace } from '@mail/model/model_field_command';

const _t = core._t;

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
    },
    async willStart() {
        this.messaging.publicLivechatGlobal.livechatButtonView.update({ widget: this });
        const cookie = utils.get_cookie('im_livechat_session');
        if (cookie) {
            const channel = JSON.parse(cookie);
            const history = await session.rpc('/mail/chat_history', {uuid: channel.uuid, limit: 100});
            history.reverse();
            this.messaging.publicLivechatGlobal.livechatButtonView.update({ history });
            for (const message of this.messaging.publicLivechatGlobal.livechatButtonView.history) {
                message.body = utils.Markup(message.body);
            }
        } else {
            const result = await session.rpc('/im_livechat/init', {channel_id: this.messaging.publicLivechatGlobal.livechatButtonView.channelId});
            if (!result.available_for_me) {
                return Promise.reject();
            }
            this.messaging.publicLivechatGlobal.livechatButtonView.update({ rule: result.rule });
        }
        return this.messaging.publicLivechatGlobal.loadQWebTemplate();
    },
    start() {
        this.$el.text(this.messaging.publicLivechatGlobal.livechatButtonView.buttonText);
        if (this.messaging.publicLivechatGlobal.livechatButtonView.history) {
            for (const m of this.messaging.publicLivechatGlobal.livechatButtonView.history) {
                this.messaging.publicLivechatGlobal.livechatButtonView.addMessage(m);
            }
            this._openChat();
        } else if (!config.device.isMobile && this.messaging.publicLivechatGlobal.livechatButtonView.rule.action === 'auto_popup') {
            const autoPopupCookie = utils.get_cookie('im_livechat_auto_popup');
            if (!autoPopupCookie || JSON.parse(autoPopupCookie)) {
                this.messaging.publicLivechatGlobal.livechatButtonView.update({
                    autoOpenChatTimeout: setTimeout(this._openChat.bind(this), this.messaging.publicLivechatGlobal.livechatButtonView.rule.auto_popup_timer * 1000),
                });
            }
        }
        if (this.messaging.publicLivechatGlobal.livechatButtonView.buttonBackgroundColor) {
            this.$el.css('background-color', this.messaging.publicLivechatGlobal.livechatButtonView.buttonBackgroundColor);
        }
        if (this.messaging.publicLivechatGlobal.livechatButtonView.buttonTextColor) {
            this.$el.css('color', this.messaging.publicLivechatGlobal.livechatButtonView.buttonTextColor);
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
     */
    _askFeedback() {
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_thread_composer input').prop('disabled', true);
        this.messaging.publicLivechatGlobal.update({ feedbackView: insertAndReplace() });
    },
    /**
     * @private
     */
    _closeChat() {
        this.messaging.publicLivechatGlobal.livechatButtonView.update({ chatWindow: clear() });
        utils.set_cookie('im_livechat_session', "", -1); // remove cookie
    },
    /**
     * @private
     */
    _openChat: _.debounce(function () {
        if (this.messaging.publicLivechatGlobal.livechatButtonView.isOpeningChat) {
            return;
        }
        const cookie = utils.get_cookie('im_livechat_session');
        let def;
        this.messaging.publicLivechatGlobal.livechatButtonView.update({ isOpeningChat: true });
        clearTimeout(this.messaging.publicLivechatGlobal.livechatButtonView.autoOpenChatTimeout);
        if (cookie) {
            def = Promise.resolve(JSON.parse(cookie));
        } else {
            // re-initialize messages cache
            this.messaging.publicLivechatGlobal.livechatButtonView.update({ messages: clear() });
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
                this.messaging.publicLivechatGlobal.update({
                    publicLivechat: insertAndReplace({ data: livechatData }),
                });
                return this._openChatWindow().then(() => {
                    if (!this.messaging.publicLivechatGlobal.livechatButtonView.history) {
                        this._sendWelcomeMessage();
                    }
                    this._renderMessages();
                    this.messaging.publicLivechatGlobal.update({ notificationHandler: insertAndReplace() });

                    utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat.toData()), true), 60 * 60);
                    utils.set_cookie('im_livechat_auto_popup', JSON.stringify(false), 60 * 60);
                    if (this.messaging.publicLivechatGlobal.publicLivechat.operator) {
                        const operatorPidId = this.messaging.publicLivechatGlobal.publicLivechat.operator.id;
                        const oneWeek = 7 * 24 * 60 * 60;
                        utils.set_cookie('im_livechat_previous_operator_pid', operatorPidId, oneWeek);
                    }
                });
            }
        }).then(() => {
            this.messaging.publicLivechatGlobal.livechatButtonView.update({ isOpeningChat: false });
        }).guardedCatch(() => {
            this.messaging.publicLivechatGlobal.livechatButtonView.update({ isOpeningChat: false });
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
        this.messaging.publicLivechatGlobal.livechatButtonView.update({ chatWindow: insertAndReplace() });
        return this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.appendTo($('body')).then(() => {
            const cssProps = { bottom: 0 };
            cssProps[_t.database.parameters.direction === 'rtl' ? 'left' : 'right'] = 0;
            this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$el.css(cssProps);
            this.$el.hide();
        });
    },
    /**
     * @private
     */
    _prepareGetSessionParameters() {
        return {
            channel_id: this.messaging.publicLivechatGlobal.livechatButtonView.channelId,
            anonymous_name: this.messaging.publicLivechatGlobal.livechatButtonView.defaultUsername,
            previous_operator_id: this._get_previous_operator_id(),
        };
    },
    /**
     * @private
     */
     _renderMessages() {
        const shouldScroll = !this.messaging.publicLivechatGlobal.publicLivechat.isFolded && this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow._publicLivechatView.isAtBottom();
        this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat._messages = this.messaging.publicLivechatGlobal.livechatButtonView.messages.map(message => message.legacyPublicLivechatMessage);
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.render();
        if (shouldScroll) {
            this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow._publicLivechatView.scrollToBottom();
        }
    },
    /**
     * @private
     * @param {Object} message
     * @return {Promise}
     */
     _sendMessage(message) {
        this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat._notifyMyselfTyping({ typing: false });
        return session
            .rpc('/mail/chat_post', { uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid, message_content: message.content })
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
                this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow._publicLivechatView.scrollToBottom();
            });
    },
    /**
     * @private
     */
    _sendWelcomeMessage() {
        if (this.messaging.publicLivechatGlobal.livechatButtonView.defaultMessage) {
            this.messaging.publicLivechatGlobal.livechatButtonView.addMessage({
                id: '_welcome',
                attachment_ids: [],
                author_id: [
                    this.messaging.publicLivechatGlobal.publicLivechat.operator.id,
                    this.messaging.publicLivechatGlobal.publicLivechat.operator.name,
                ],
                body: this.messaging.publicLivechatGlobal.livechatButtonView.defaultMessage,
                date: time.datetime_to_str(new Date()),
                model: "mail.channel",
                res_id: this.messaging.publicLivechatGlobal.publicLivechat.id,
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
        const isComposerDisabled = this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_thread_composer input').prop('disabled');
        const shouldAskFeedback = !isComposerDisabled && this.messaging.publicLivechatGlobal.livechatButtonView.messages.find(function (message) {
            return message.id !== '_welcome';
        });
        if (shouldAskFeedback) {
            this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.toggleFold(false);
            this._askFeedback();
        } else {
            this._closeChat();
        }
        this._visitorLeaveSession();
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
        utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat.toData()), true), 60 * 60);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedTypingPartners(ev) {
        ev.stopPropagation();
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.renderHeader();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedUnreadCounter(ev) {
        ev.stopPropagation();
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.renderHeader();
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
