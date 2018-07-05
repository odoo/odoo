odoo.define('im_livechat.WebsiteLivechatWindow', function (require) {
"use strict";

var AbstractThreadWindow = require('mail.AbstractThreadWindow');

/**
 * This is the widget that represent windows of livechat in the frontend.
 *
 * @see mail.AbstractThreadWindow for more information
 */
var LivechatWindow = AbstractThreadWindow.extend({
    /**
     * @override
     * @param {?} parent
     * @param {im_livechat.model.WebsiteLivechat} thread
     */
    init: function (parent, thread) {
        this._super.apply(this, arguments);

        this._thread = thread;
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
        return this._thread.getTitle();
    },
    /**
     * @override
     * @returns {integer}
     */
    getUnreadCounter: function () {
        return this._thread.getUnreadCounter();
    },
    /**
     * @override
     * @returns {boolean}
     */
    hasThread: function () {
        return !!this._thread;
    },
    /**
     * Increment the unread counter of this thread window, which is equivalent
     * to incrementing the unread counter of the related channel
     */
    incrementUnreadCounter: function () {
        this._thread.incrementUnreadCounter();
    },
    /**
     * @override
     * @returns {boolean}
     */
    isFolded: function () {
        return this._thread.isFolded();
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
        this._thread.resetUnreadCounter();
        this._renderHeader();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * AKU: TODO drop this method when there's the website livechat thread
     * model linked to this website livechat window.
     *
     * @override
     * @returns {integer}
     */
    _getThreadID: function () {
        return this._thread.getID();
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
        this._thread.updateFoldState(folded);
        this.updateVisualFoldState();
    },
});

return LivechatWindow;

});
