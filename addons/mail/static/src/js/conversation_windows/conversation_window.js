odoo.define('mail.widget.ConversationWindow', function (require) {
"use strict";

var composer = require('mail.composer');
var AbstractConversationWindow = require('mail.widget.AbstractConversationWindow');

var core = require('web.core');

var _t = core._t;

var ConversationWindow = AbstractConversationWindow.extend({
    template: 'mail.ConversationWindow',
    events: _.extend({}, AbstractConversationWindow.prototype.events, {
        'click .o_conversation_window_expand': '_onClickExpand',
    }),
    /**
     * Version of conversation window that supports {mail.model.Conversation}
     *
     * @override
     * @param {Widget}
     * @param {mail.model.Conversation} [conversation = null] if not set,
     *   this is a "new conversation" window. It lets us open a DM by
     *   providing the name of a chat.
     * @param {Object} options
     * @param {Object} [options.prefix] prefix of the title of the conversation window
     */
    init: function (parent, conversation, options) {
        this._super.apply(this, arguments);
        this._conversation = conversation || null;

        if (!this.hasConversation()) {
            this._folded = false; // internal fold state of conversation window without any conversation
        }
    },

    /**
     * @override
     */
    start: function () {
        var def;
        if (!this.hasConversation()) {
            this._startWithoutConversation();
        } else if (this._isInputless()) {
            var basicComposer = new composer.BasicComposer(this, {
                mentionPartnersRestricted: true,
                isMini: true
            });
            basicComposer.on('post_message', this, function (message) {
                this._conversation.postMessage(message);
            });
            basicComposer.once('input_focused', this, function () {
                var commands = this._conversation.getCommands();
                var partners = this._conversation.getMentionPartnerSuggestions();
                basicComposer.mentionSetEnabledCommands(commands);
                basicComposer.mentionSetPrefetchedPartners(partners);
            });
            def = basicComposer.replace(this.$('.o_conversation_composer'));
        }
        return $.when(this._super(), def);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Set the focus on the input of this conversation window
     */
    focusInput: function () {
        this._focusInput();
    },
    /**
     * Get the title of the conversation window, which is equivalent to
     * the name of related conversation, prefixed with "#" if
     * this is a chat (i.e. DM, backend livechat).
     *
     * If there is no conversation linked to this conversation window,
     * Display title of "new conversation" window
     *
     * @override
     * @return {string}
     */
    getTitle: function () {
        if (!this.hasConversation()) {
            return _t("New message");
        }
        var prefix = !this._conversation.isChat() ? "#" : "";
        return prefix + this._conversation.getName();
    },
    /**
     * Get the unread counter of the related conversation.
     * If there are no conversation linked to this conversation window,
     * returns 0.
     *
     * @override
     * @return {integer}
     */
    getUnreadCounter: function () {
        if (!this.hasConversation()) {
            return 0;
        }
        return this._conversation.getUnreadCounter();
    },
    /**
     * @override
     * @returns {boolean}
     */
    hasConversation: function () {
        return !!this._conversation;
    },
    /**
     * State whether the related conversation is folded or not.
     * If there are no conversation related to this conversation window,
     * It means this is the "new conversation" conversation window,
     * therefore we use the internal folded state.
     *
     * @override
     * @returns {boolean}
     */
    isFolded: function () {
        if (!this.hasConversation()) {
            return this._folded;
        }
        return this._conversation.isFolded();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @return {integer}
     */
    _getConversationID: function () {
        if (!this.hasConversation()) {
            return 0;
        }
        return this._conversation.getID();
    },
    /**
     * States whether the input of the conversation window should be displayed or not.
     * This is based on the type of the conversation:
     *
     * Do not display the input in the following cases:
     *
     *      - conversation window without any conversation
     *      - conversation window of a mailbox (temp: let us have mailboxes in window mode)
     *      - conversation window of a conversation with mass mailing
     *
     * Any other conversations show the input in the conversation window.
     *
     * @private
     * @returns {boolean}
     */
    _isInputless: function () {
        return this.hasConversation() &&
                (this._conversation.getType() !== 'mailbox') &&
                !this._conversation.isMassMailing();
    },
    /**
     * @private
     */
    _startWithoutConversation: function () {
        var self = this;
        this.$el.addClass('o_thread_less');
        this.$('.o_chat_search_input input')
            .autocomplete({
                source: function (request, response) {
                    self.call('chat_service', 'searchPartner', request.term, 10).done(response);
                },
                select: function (event, ui) {
                    self.trigger('open_dm_session', ui.item.id);
                },
            })
            .focus();
    },
    /**
     * @override
     * @private
     * @param {boolean} folded
     */
    _updateConversationFoldState: function (folded) {
        this._conversation.fold(folded);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
      * @private
      * @param {MouseEvent} ev
      */
    _onClickExpand: _.debounce(function (ev) {
        ev.preventDefault();
        this.do_action('mail.mail_channel_action_client_chat', {
            clear_breadcrumbs: false,
            active_id: this._conversation.getID(),
            on_reverse_breadcrumb: this.call('chat_service', 'getChatBus').trigger('discuss_open', false),
        });
    }, 1000, true),
    /**
     * @override
     * @private
     * @param {KeyboardEvent} ev
     *
     * Override _onKeydown to only prevent jquery's blockUI to cancel event, but without sending
     * the message on ENTER keydown as this is handled by the BasicComposer
     */
    _onKeydown: function (ev) {
        ev.stopPropagation();
    },

});

return ConversationWindow;

});
