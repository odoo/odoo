odoo.define('mail.widget.LiveChatWindow', function (require) {
"use strict";

var AbstractConversationWindow = require('mail.widget.AbstractConversationWindow');

var LiveChatWindow = AbstractConversationWindow.extend({
    /**
     * The conversation of a live chat window is a channel
     * with server format.
     *
     * @override
     * @param {Widget}
     * @param {Object} serverChannel
     * @param {integer} serverChannel.id
     * @param {string} serverChannel.name
     * @param {string} serverChannel.state
     * @param {integer} [serverChannel.message_unread_counter = 0]
     * @param {Object} options
     */
    init: function (parent, serverChannel, options) {
        this._super.apply(this, arguments);

        /**
         * @param {Object} serverChannel
         * @param {integer} serverChannel.id
         * @param {string} serverChannel.name
         * @param {string} serverChannel.state
         * @param {integer} [serverChannel.message_unread_counter = 0]
         */
        this._serverChannel = serverChannel;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {string}
     */
    getTitle: function () {
        return this._serverChannel.name;
    },
    /**
     * @override
     * @returns {integer}
     */
    getUnreadCounter: function () {
        return this._serverChannel.message_unread_counter;
    },
    /**
     * @override
     * @returns {boolean}
     */
    hasConversation: function () {
        return !!this._serverChannel;
    },
    /**
     * Increment the unread counter of this conversation window, which is equivalent to
     * incrementing the unread counter of the related channel
     */
    incrementUnreadCounter: function () {
        this._serverChannel.message_unread_counter++;
    },
    /**
     * @override
     * @returns {boolean}
     */
    isFolded: function () {
        return (this._serverChannel.state === 'folded');
    },
    /**
     * @param {integer} counter
     */
    updateUnreadCounter: function (counter) {
        this._serverChannel.message_unread_counter = counter;
        this._renderHeader();
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
        return this._serverChannel.id;
    },
    /**
     * @override
     * @private
     * @param {boolean} folded
     */
    _updateConversationFoldState: function (folded) {
        this._serverChannel.state = folded ? 'folded' : 'open';
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Warn the parent widget {im_livechat.im_livechat}.LiveChatButton
     *
     * @override
     * @private
     * @param {boolean} folded
     */
    _toggleFold: function () {
        this._super.apply(this, arguments);
        this.trigger_up('save_conversation');
    },

});

return LiveChatWindow;

});
