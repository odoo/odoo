odoo.define('mail.model.ChatSession', function (require) {
"use strict";

var ConversationWindow = require('mail.widget.ConversationWindow');

var Class = require('web.Class');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');
var webClient = require('web.web_client');

var ChatSession = Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @param {mail.ChatWindowManager} parent
     * @param {mail.model.Conversation} conversation
     * @param {Object} options
     * @param {Object} options.windowOptions
     */
    init: function (parent, conversation, options) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);

        this._chatWindowManager = parent;
        this._chatManager = options.chatManager; // temporary (ugly)

        this._conversation = conversation;

        this.keepUnread = options.passively; // don't automatically mark unread messages as seen
        this.window = new ConversationWindow(
            webClient,
            conversation,
            options.windowOptions
        );

        this.window.on('close_chat_session', this, this._onCloseChatSession);
        this.window.on('toggle_star_status', this, this._onToggleStarStatus);
        this.window.on('post_message', this, this._onPostMessage);
        this.window.on('redirect', this, this._onRedirect);
        this.window.on('redirect_to_channel', this, this._onRedirectToChannel);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the ID of the chat window, which is equivalent to the ID of the
     * related conversation.
     *
     * @returns {integer}
     */
    getID: function () {
        return this._conversation.getID();
    },
    /**
     * @param {mail.model.Message[]} messages
     */
    render: function (messages) {
        this.window.render(messages);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------



    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {integer} channelID unused parameter
     */
    _onCloseChatSession: function (channelID) {
        this.window.destroy();
        this._chatWindowManager.removeChatSession(this.getID());
    },
    /**
     * @private
     * @param {Object} messageData
     * @param {integer} channelID unused parameter
     */
    _onPostMessage: function (messageData, channelID) {
        var self = this;
        var conversation = this._chatManager.getConversation(this.getID());
        conversation.postMessage(messageData)
            .then(function () {
                self.window.threadWidget.scrollToBottom();
            });
    },
    /**
     * @private
     * @param {string} resModel
     * @param {integer} resID
     */
    _onRedirect: function (resModel, resID) {
        this._chatManager.redirect(resModel, resID, this._chatWindowManager.openChat.bind(this));
    },
    /**
     * @private
     * @param {integer} channelID unused parameter
     */
    _onRedirectToChannel: function (channelID) {
        var session = this._getChatSession(this.getID());
        if (!session) {
            this._chatManager.joinChannel(this.getID()).then(function (channel) {
                channel.detach();
            });
        } else {
            this.window.toggleFold(false);
        }
    },
    /**
     * @private
     * @param {integer} messageID
     */
    _onToggleStarStatus: function (messageID) {
        var message = this._chatManager.getMessage(messageID);
        message.toggleStarStatus();
    },

});

return ChatSession;

});
