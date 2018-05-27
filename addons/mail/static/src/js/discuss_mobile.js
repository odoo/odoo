odoo.define('mail.DiscussMobile', function (require) {
"use strict";

var Discuss = require('mail.Discuss');

var config = require('web.config');
var core = require('web.core');

var QWeb = core.qweb;

if (!config.device.isMobile) {
    return;
}

Discuss.include({
    template: 'mail.discuss_mobile',
    events: _.extend(Discuss.prototype.events, {
        'click .o_mail_mobile_tab': '_onMobileTabClicked',
        'click .o_mailbox_inbox_item': '_onMobileInboxButtonClicked',
        'click .o_mail_conversation_preview': '_onMobileConversationClicked',
    }),

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.currentState = this._defaultConversationID;
    },
    /**
     * @override
     */
    start: function () {
        this._$mainContent = this.$('.o_mail_conversation_content');
        return this._super.apply(this, arguments)
            .then(this._updateControlPanel.bind(this));
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        if (this._conversation && this._isInInboxTab()) {
            this._threadWidget.scrollToPosition(this._conversationsScrolltop[this._conversation.getID()]);
        }
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        if (this._isInInboxTab()) {
            this._conversationsScrolltop[this._conversation.getID()] = this._threadWidget.getScrolltop();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Boolean} true iff we currently are in the Inbox tab
     */
    _isInInboxTab: function () {
        return _.contains(['mailbox_inbox', 'mailbox_starred'], this.currentState);
    },
    /**
     * @override
     * @private
     */
    _renderButtons: function () {
        var self = this;
        this._super.apply(this, arguments);
        _.each(['dm', 'public', 'private'], function (type) {
            var selector = '.o_mail_conversation_button_' + type;
            self.$buttons.on('click', selector, self._onAddChannel.bind(self));
        });
    },
    /**
     * Overrides to only store the conversation state if we are in the Inbox tab, as
     * this is the only tab in which we actually have a displayed conversation
     *
     * @override
     * @private
     */
    _restoreConversationState: function () {
        if (this._isInInboxTab()) {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to toggle the visibility of the tabs when a message is selected
     *
     * @override
     * @private
     */
    _selectMessage: function () {
        this._super.apply(this, arguments);
        this.$('.o_mail_mobile_tabs').addClass('o_hidden');
    },
    /**
     * @override
     * @private
     * @param {mail.model.Conversation} conversation
     */
    _setConversation: function (conversation) {
        if (conversation.getType() !== 'mailbox') {
            conversation.detach();
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to only store the channel state if we are in the Inbox tab, as
     * this is the only tab in which we actually have a displayed channel
     *
     * @override
     * @private
     */
    _storeConversationState: function () {
        if (this._conversation && this._isInInboxTab()) {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to toggle the visibility of the tabs when a message is unselected
     *
     * @override
     * @private
     */
    _unselectMessage: function () {
        this._super.apply(this, arguments);
        this.$('.o_mail_mobile_tabs').removeClass('o_hidden');
    },
    /**
     * @override
     * @private
     */
    _updateConversations: function () {
        return this._updateContent(this.currentState);
    },
    /**
     * Redraws the content of the client action according to its current state.
     *
     * @private
     * @param {string} type the channel's type to display (e.g. 'mailbox_inbox',
     *   'mailbox_starred', 'dm'...).
     */
    _updateContent: function (type) {
        var self = this;
        var inMailbox = type === 'mailbox_inbox' || type === 'mailbox_starred';
        if (!inMailbox && this._isInInboxTab()) {
            // we're leaving the inbox, so store the conversation scrolltop
            this._storeConversationState();
        }
        var previouslyInInbox = this._isInInboxTab();
        this.currentState = type;

        // fetch content to display
        var def;
        if (inMailbox) {
            def = this._fetchAndRenderThread();
        } else {
            var allChannels = this.call('chat_service', 'getChannels');
            var channels = _.filter(allChannels, function (channel) {
                return channel.getType() === type;
            });
            def = this.call('chat_service', 'getChannelPreviews', channels);
        }
        return $.when(def).then(function (channelPreviews) {
            // update content
            if (inMailbox) {
                if (!previouslyInInbox) {
                    self.$('.o_mail_chat_tab_pane').remove();
                    self._$mainContent.append(self._threadWidget.$el);
                    self._$mainContent.append(self._extendedComposer.$el);
                }
                self._restoreConversationState();
            } else {
                self._threadWidget.$el.detach();
                self._extendedComposer.$el.detach();
                var $content = $(QWeb.render('mail.conversation.MobileTabPane', {
                    conversationPreviews: channelPreviews,
                    type: type,
                }));
                self._prepareAddChannelInput($content.find('.o_mail_add_channel input'), type);
                self._$mainContent.html($content);
            }

            // update control panel
            self.$buttons.find('button').addClass('o_hidden');
            self.$buttons.find('.o_mail_conversation_button_' + type).removeClass('o_hidden');
            self.$buttons.find('.o_mail_conversation_button_mark_read').toggleClass('o_hidden', type !== 'mailbox_inbox');
            self.$buttons.find('.o_mail_conversation_button_unstar_all').toggleClass('o_hidden', type !== 'mailbox_starred');

            // update Mailbox page buttons
            if (inMailbox) {
                self.$('.o_mail_chat_mobile_mailboxes_buttons').removeClass('o_hidden');
                self.$('.o_mailbox_inbox_item').removeClass('btn-primary').addClass('btn-default');
                self.$('.o_mailbox_inbox_item[data-type=' + type + ']').removeClass('btn-default').addClass('btn-primary');
            } else {
                self.$('.o_mail_chat_mobile_mailboxes_buttons').addClass('o_hidden');
            }

            // update bottom buttons
            self.$('.o_mail_mobile_tab').removeClass('active');
            // mailbox_inbox and mailbox_starred share the same tab
            type = type === 'mailbox_starred' ? 'mailbox_inbox' : type;
            self.$('.o_mail_mobile_tab[data-type=' + type + ']').addClass('active');
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAddChannel: function () {
        this.$('.o_mail_add_channel').show().find('input').focus();
    },
    /**
     * Switches to the clicked channel in the Inbox page (Inbox or Starred).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMobileInboxButtonClicked: function (ev) {
        var inbox = this.call('chat_service', 'getMailbox', $(ev.currentTarget).data('type'));
        this._setConversation(inbox);
        this._updateContent(this._conversation.getID());
    },
    /**
     * Switches to another tab.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMobileTabClicked: function (ev) {
        var type = $(ev.currentTarget).data('type');
        if (type === 'mailbox') {
            var inbox = this.call('chat_service', 'getMailbox', 'inbox');
            this._setConversation(inbox);
        }
        this._updateContent(type);
    },
    /**
     * Opens a conversation in a chat windown (full screen in mobile).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMobileConversationClicked: function (ev) {
        var conversationID = $(ev.currentTarget).data('conversation_id');
        var conversation = this.call('chat_service', 'getConversation', conversationID);
        conversation.detach();
    },
});

});
