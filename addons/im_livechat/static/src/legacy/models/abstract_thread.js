/** @odoo-module **/

import Class from 'web.Class';
import Mixins from'web.mixins';

/**
 * Abstract thread is the super class of all threads, either backend threads
 * (which are compatible with mail service) or website livechats.
 *
 * Abstract threads contain abstract messages
 */
const AbstractThread = Class.extend(Mixins.EventDispatcherMixin, {
    /**
     * @param {Object} params
     * @param {Object} params.data
     * @param {integer|string} params.data.id the ID of this thread
     * @param {string} params.data.name the name of this thread
     * @param {string} [params.data.status=''] the status of this thread
     * @param {Object} params.parent Object with the event-dispatcher mixin
     *   (@see {web.mixins.EventDispatcherMixin})
     */
    init(params) {
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
     * @param {@im_livechat/legacy/models/public_livechat_message} message
     */
    addMessage(message) {
        this._addMessage(...arguments);
        this.trigger('message_added', message);
    },
    /**
     * Updates the folded state of the thread
     *
     * @param {boolean} folded
     */
    fold(folded) {
        this._folded = folded;
    },
    /**
     * Get the ID of this thread
     *
     * @returns {integer|string}
     */
    getID() {
        return this._id;
    },
    /**
     * @abstract
     * @returns {@im_livechat/legacy/models/public_livechat_message[]}
     */
    getMessages() {},
    /**
     * Get the name of this thread. If the name of the thread has been created
     * by the user from an input, it may be escaped.
     *
     * @returns {string}
     */
    getName() {
        return this._name;
    },
    /**
     * Get the status of the thread (e.g. 'online', 'offline', etc.)
     *
     * @returns {string}
     */
    getStatus() {
        return this._status;
    },
    /**
     * Returns the title to display in thread window's headers.
     *
     * @returns {string} the name of the thread by default (see @getName)
     */
    getTitle() {
        return this.getName();
    },
    getType() {},
    /**
     * @returns {integer}
     */
    getUnreadCounter() {
        return this._unreadCounter;
    },
    /**
     * @returns {boolean}
     */
    hasMessages() {
        return !_.isEmpty(this.getMessages());
    },
    /**
     * States whether this thread is folded or not.
     *
     * @return {boolean}
     */
    isFolded() {
        return this._folded;
    },
    /**
     * Mark the thread as read, which resets the unread counter to 0. This is
     * only performed if the unread counter is not 0.
     *
     * @returns {Promise}
     */
    markAsRead() {
        if (this._unreadCounter > 0) {
            return this._markAsRead();
        }
        return Promise.resolve();
    },
    /**
     * Post a message on this thread
     *
     * @returns {Promise} resolved with the message object to be sent to the
     *   server
     */
    postMessage() {
        return this._postMessage(...arguments)
                                .then(this.trigger.bind(this, 'message_posted'));
    },
    /**
     * Resets the unread counter of this thread to 0.
     */
    resetUnreadCounter() {
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
     * @param {@im_livechat/legacy/models/public_livechat_message} message
     */
    _addMessage(message) {},
    /**
     * Increments the unread counter of this thread by 1 unit.
     *
     * @private
     */
    _incrementUnreadCounter() {
        this._unreadCounter++;
    },
    /**
     * Mark the thread as read
     *
     * @private
     * @returns {Promise}
     */
    _markAsRead() {
        this.resetUnreadCounter();
        return Promise.resolve();
    },
    /**
     * Post a message on this thread
     *
     * @abstract
     * @private
     * @returns {Promise} resolved with the message object to be sent to the
     *   server
     */
    _postMessage() {
        return Promise.resolve();
    },
    /**
     * Warn views (e.g. discuss app, thread window, etc.) to update visually
     * the unread counter of this thread.
     *
     * @abstract
     * @private
     */
    _warnUpdatedUnreadCounter() {},
});

export default AbstractThread;
