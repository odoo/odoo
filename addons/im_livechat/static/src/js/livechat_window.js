odoo.define('im_livechat.LivechatWindow', function (require) {
"use strict";

var AbstractThreadWindow = require('mail.AbstractThreadWindow');

/**
 * This is the widget that represent windows of livechat in the frontend.
 *
 * @see mail.AbstractThreadWindow for more information
 */
var LivechatWindow = AbstractThreadWindow.extend({
    /**
     * The thread of a live chat window is just an object containing some
     * server data of the livechat
     *
     * @override
     * @param {mail.Manager} parent
     * @param {Object} data
     * @param {integer} data.id
     * @param {string} data.name
     * @param {string} data.state
     * @param {integer} [data.message_unread_counter=0]
     */
    init: function (parent, data) {
        this._super.apply(this, arguments);

        this._data = data;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    close: function () {
        this.trigger('close');
    },
    /**
     * @override
     * @returns {string}
     */
    getTitle: function () {
        return this._data.name;
    },
    /**
     * @override
     * @returns {integer}
     */
    getUnreadCounter: function () {
        return this._data.message_unread_counter;
    },
    /**
     * @override
     * @returns {boolean}
     */
    hasThread: function () {
        return !!this._data;
    },
    /**
     * Increment the unread counter of this thread window, which is equivalent
     * to incrementing the unread counter of the related channel
     */
    incrementUnreadCounter: function () {
        this._data.message_unread_counter++;
    },
    /**
     * @override
     * @returns {boolean}
     */
    isFolded: function () {
        return (this._data.state === 'folded');
    },
    /**
     * Warn the parent widget (LivechatButton)
     *
     * @override
     * @param {boolean} folded
     */
    toggleFold: function () {
        this._super.apply(this, arguments);
        this.trigger('save_chat');
    },
    /**
     * Reset the unread counter of the livechat window
     */
    resetUnreadCounter: function () {
        this._data.message_unread_counter = 0;
        this._renderHeader();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * If there are no chat linked to this livechat window, returns null.
     *
     * @override
     * @returns {integer|null}
     */
    _getThreadID: function () {
        if (!this.hasThread()) {
            return null;
        }
        return this._data.id;
    },
    /**
     * @override
     * @private
     * @param {Object} messageData
     */
    _postMessage: function (messageData) {
        this.trigger('post_message', messageData);
    },
    /**
     * @override
     * @private
     * @param {boolean} folded
     */
    _updateThreadFoldState: function (folded) {
        this._data.state = folded ? 'folded' : 'open';
        this.updateVisualFoldState();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

});

return LivechatWindow;

});
