/** @odoo-module **/

import config from 'web.config';
import time from 'web.time';
import utils from 'web.utils';
import Widget from 'web.Widget';

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
        'click': '_onClick'
    },
    init(parent, messaging) {
        this._super(parent);
        this.messaging = messaging;
    },
    async willStart() {
        this.messaging.publicLivechatGlobal.livechatButtonView.update({ widget: this });
        return this.messaging.publicLivechatGlobal.livechatButtonView.willStart();
    },
    start() {
        this.$el.text(this.messaging.publicLivechatGlobal.livechatButtonView.buttonText);
        if (this.messaging.publicLivechatGlobal.livechatButtonView.history) {
            for (const m of this.messaging.publicLivechatGlobal.livechatButtonView.history) {
                this.messaging.publicLivechatGlobal.livechatButtonView.addMessage(m);
            }
            this.messaging.publicLivechatGlobal.livechatButtonView.openChat();
        } else if (!config.device.isMobile && this.messaging.publicLivechatGlobal.livechatButtonView.rule.action === 'auto_popup') {
            const autoPopupCookie = utils.get_cookie('im_livechat_auto_popup');
            if (!autoPopupCookie || JSON.parse(autoPopupCookie)) {
                this.messaging.publicLivechatGlobal.livechatButtonView.update({
                    autoOpenChatTimeout: setTimeout(
                        this.messaging.publicLivechatGlobal.livechatButtonView.openChat,
                        this.messaging.publicLivechatGlobal.livechatButtonView.rule.auto_popup_timer * 1000,
                    ),
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
        const shouldScroll = !this.messaging.publicLivechatGlobal.publicLivechat.isFolded && this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.publicLivechatView.widget.isAtBottom();
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.render();
        if (shouldScroll) {
            this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.publicLivechatView.widget.scrollToBottom();
        }
    },
    /**
     * @private
     */
    _sendWelcomeMessage() {
        if (this.messaging.publicLivechatGlobal.livechatButtonView.defaultMessage) {
            this.messaging.publicLivechatGlobal.livechatButtonView.addMessage({
                id: '_welcome',
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
     */
    _onClick() {
        this.messaging.publicLivechatGlobal.livechatButtonView.openChat();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onCloseChatWindow(ev) {
        ev.stopPropagation();
        const isComposerDisabled = this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_thread_composer input').prop('disabled');
        const shouldAskFeedback = !isComposerDisabled && this.messaging.publicLivechatGlobal.messages.find(function (message) {
            return message.id !== '_welcome';
        });
        if (shouldAskFeedback) {
            this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.toggleFold(false);
            this.messaging.publicLivechatGlobal.livechatButtonView.askFeedback();
        } else {
            this.messaging.publicLivechatGlobal.livechatButtonView.closeChat();
        }
        this.messaging.publicLivechatGlobal.livechatButtonView.leaveSession();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data.messageData
     */
    async _onPostMessageChatWindow(ev) {
        ev.stopPropagation();
        const messageData = ev.data.messageData;
        try {
            await this.messaging.publicLivechatGlobal.livechatButtonView.sendMessage(messageData);
        } catch (reason) {
            reason.event.preventDefault();
            return this.messaging.publicLivechatGlobal.livechatButtonView.sendMessage(messageData); // try again just in case
        }
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
});

export default LivechatButton;
