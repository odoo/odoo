odoo.define('mail.model.AbstractThread', function (require) {
"use strict";

var Class = require('web.Class');
var Mixins = require('web.mixins');

/**
 * Abstract thread is the super class of all threads, either backend threads
 * (which are compatible with mail service) or website livechats.
 *
 * Abstract threads contain abstract messages
 */
var AbstractThread = Class.extend(Mixins.EventDispatcherMixin, {
    /**
     * @param {Object} params
     * @param {Object} params.data
     * @param {integer|string} params.data.id the ID of this thread
     * @param {string} params.data.name the name of this thread
     * @param {string} [params.data.status=''] the status of this thread
     * @param {Object} params.parent Object with the event-dispatcher mixin
     *   (@see {web.mixins.EventDispatcherMixin})
     */
    init: function (params) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(params.parent);

        this._folded = false; // threads are unfolded by default
        this._id = params.data.id;
        this._name = params.data.name;
        this._status = params.data.status || '';
        this._unreadCounter = 0; // amount of messages not yet been read
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a message to this thread.
     *
     * @param {mail.model.AbstractMessage} message
     */
    addMessage: function (message) {
        this._addMessage.apply(this, arguments);
        this.trigger('message_added', message);
    },
    /**
     * Updates the folded state of the thread
     *
     * @param {boolean} folded
     */
    fold: function (folded) {
        this._folded = folded;
    },
    /**
     * Get the ID of this thread
     *
     * @returns {integer|string}
     */
    getID: function () {
        return this._id;
    },
    /**
     * @abstract
     * @returns {mail.model.AbstractMessage[]}
     */
    getMessages: function () {},
    /**
     * Get the name of this thread. If the name of the thread has been created
     * by the user from an input, it may be escaped.
     *
     * @returns {string}
     */
    getName: function () {
        return this._name;
    },
    /**
     * Get the status of the thread (e.g. 'online', 'offline', etc.)
     *
     * @returns {string}
     */
    getStatus: function () {
        return this._status;
    },
    /**
     * Returns the title to display in thread window's headers.
     *
     * @returns {string} the name of the thread by default (see @getName)
     */
    getTitle: function () {
        return this.getName();
    },
    /**
     * @returns {integer}
     */
    getUnreadCounter: function () {
        return this._unreadCounter;
    },
    /**
     * @returns {boolean}
     */
    hasMessages: function () {
        return !_.isEmpty(this.getMessages());
    },
    /**
     * States whether this thread is compatible with the 'is typing...' feature.
     * By default, threads do not have this feature active.
     * @see {mail.model.ThreadTypingMixin} to enable this feature on a thread.
     *
     * @returns {boolean}
     */
    hasTypingNotification: function () {
        return false;
    },
    /**
     * States whether this thread is folded or not.
     *
     * @return {boolean}
     */
    isFolded: function () {
        return this._folded;
    },
    /**
     * Mark the thread as read, which resets the unread counter to 0. This is
     * only performed if the unread counter is not 0.
     *
     * @returns {$.Promise}
     */
    markAsRead: function () {
        if (this._unreadCounter > 0) {
            return this._markAsRead();
        }
        return $.when();
    },
    /**
     * Post a message on this thread
     *
     * @returns {$.Promise} resolved with the message object to be sent to the
     *   server
     */
    postMessage: function () {
        return this._postMessage.apply(this, arguments)
                                .then(this.trigger.bind(this, 'message_posted'));
    },
    /**
     * Resets the unread counter of this thread to 0.
     */
    resetUnreadCounter: function () {
        this._unreadCounter = 0;
        this._warnUpdatedUnreadCounter();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a message to this thread.
     *
     * @abstract
     * @private
     * @param {mail.model.AbstractMessage} message
     */
    _addMessage: function (message) {},
    /**
     * Increments the unread counter of this thread by 1 unit.
     *
     * @private
     */
    _incrementUnreadCounter: function () {
        this._unreadCounter++;
    },
    /**
     * Mark the thread as read
     *
     * @private
     * @returns {$.Promise}
     */
    _markAsRead: function () {
        this.resetUnreadCounter();
        return $.when();
    },
    /**
     * Post a message on this thread
     *
     * @abstract
     * @private
     * @returns {$.Promise} resolved with the message object to be sent to the
     *   server
     */
    _postMessage: function () {
        return $.when();
    },
    /**
     * Warn views (e.g. discuss app, thread window, etc.) to update visually
     * the unread counter of this thread.
     *
     * @abstract
     * @private
     */
    _warnUpdatedUnreadCounter: function () {},
});

return AbstractThread;

});
