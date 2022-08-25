/** @odoo-module **/

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
    start() {
        this.messaging.publicLivechatGlobal.livechatButtonView.start();
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
            channel_id: this.messaging.publicLivechatGlobal.channelId,
            anonymous_name: this.messaging.publicLivechatGlobal.livechatButtonView.defaultUsername,
            previous_operator_id: this._get_previous_operator_id(),
        };
    },
    /**
     * @private
     */
     _renderMessages() {
        const shouldScroll = !this.messaging.publicLivechatGlobal.publicLivechat.isFolded && this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.isAtBottom();
        this.messaging.publicLivechatGlobal.chatWindow.widget.render();
        if (shouldScroll) {
            this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.scrollToBottom();
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
        const isComposerDisabled = this.messaging.publicLivechatGlobal.chatWindow.widget.$('.o_thread_composer input').prop('disabled');
        const shouldAskFeedback = !isComposerDisabled && this.messaging.publicLivechatGlobal.messages.find(function (message) {
            return message.id !== '_welcome';
        });
        if (shouldAskFeedback) {
            this.messaging.publicLivechatGlobal.chatWindow.widget.toggleFold(false);
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
        utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(this.messaging.publicLivechatGlobal.publicLivechat.widget.toData()), true), 60 * 60);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedTypingPartners(ev) {
        ev.stopPropagation();
        this.messaging.publicLivechatGlobal.chatWindow.widget.renderHeader();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedUnreadCounter(ev) {
        ev.stopPropagation();
        this.messaging.publicLivechatGlobal.chatWindow.widget.renderHeader();
    },
});

export default LivechatButton;
