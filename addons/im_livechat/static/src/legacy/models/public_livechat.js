/** @odoo-module **/

import ThreadTypingMixin from '@im_livechat/legacy/models/thread_typing_mixin';

import Class from 'web.Class';
import session from 'web.session';
import Mixins from 'web.mixins';

/**
 * Thread model that represents a livechat on the website-side. This livechat
 * is not linked to the mail service.
 */
const PublicLivechat = Class.extend(Mixins.EventDispatcherMixin, ThreadTypingMixin, {

    /**
     * @override
     * @private
     * @param {Object} params
     * @param {Object} params.data
     * @param {boolean} [params.data.folded] states whether the livechat is
     *   folded or not. It is considered only if this is defined and it is a
     *   boolean.
     * @param {integer} params.data.id the ID of this livechat.
     * @param {integer} [params.data.message_unread_counter] the unread counter
     *   of this livechat.
     * @param {Array} params.data.operator_pid
     * @param {string} params.data.name the name of this livechat.
     * @param {string} [params.data.state] if 'folded', the livechat is folded.
     *   This is ignored if `folded` is provided and is a boolean value.
     * @param {string} [params.data.status=''] the status of this thread
     * @param {string} params.data.uuid the UUID of this livechat.
     * @param {@im_livechat/legacy/widgets/livechat_button} params.parent
     */
    init(params) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(params.parent);

        this._folded = false; // threads are unfolded by default
        this._id = params.data.id;
        this._name = params.data.name;
        this._status = params.data.status || '';
        this._unreadCounter = 0; // amount of messages not yet been read
        ThreadTypingMixin.init.call(this, arguments);

        this._members = [];
        this._operatorPID = params.data.operator_pid;
        this._uuid = params.data.uuid;

        if (params.data.message_unread_counter !== undefined) {
            this._unreadCounter = params.data.message_unread_counter;
        }

        if (_.isBoolean(params.data.folded)) {
            this._folded = params.data.folded;
        } else {
            this._folded = params.data.state === 'folded';
        }

        // Necessary for thread typing mixin to display is typing notification
        // bar text (at least, for the operator in the members).
        this._members.push({
            id: this._operatorPID[0],
            name: this._operatorPID[1]
        });
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
     * @override
     * @returns {@im_livechat/legacy/models/public_livechat_message[]}
     */
     getMessages() {
        // ignore removed messages
        return this._messages.filter(message => !message.isEmpty());
    },
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
     * @returns {Array}
     */
    getOperatorPID() {
        return this._operatorPID;
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
    /**
     * @returns {integer}
     */
    getUnreadCounter() {
        return this._unreadCounter;
    },
    /**
     * @returns {string}
     */
    getUUID() {
        return this._uuid;
    },
    /**
     * @returns {boolean}
     */
    hasMessages() {
        return !_.isEmpty(this.getMessages());
    },
    /**
     * Increments the unread counter of this livechat by 1 unit.
     *
     * Note: this public method makes sense because the management of messages
     * for website livechat is external. This method should be dropped when
     * this class handles messages by itself.
     */
    incrementUnreadCounter() {
        this._incrementUnreadCounter();
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
    /**
     * AKU: hack for the moment
     *
     * @param {@im_livechat/legacy/models/public_livechat_message[]} messages
     */
    setMessages(messages) {
        this._messages = messages;
    },
    /**
     * @returns {Object}
     */
    toData() {
        return {
            folded: this.isFolded(),
            id: this.getID(),
            message_unread_counter: this.getUnreadCounter(),
            operator_pid: this.getOperatorPID(),
            name: this.getName(),
            uuid: this.getUUID(),
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Increments the unread counter of this thread by 1 unit.
     *
     * @private
     */
    _incrementUnreadCounter() {
        this._unreadCounter++;
    },
    /**
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {Object} params
     * @param {boolean} params.isWebsiteUser
     * @returns {boolean}
     */
    _isTypingMyselfInfo(params) {
        return params.isWebsiteUser;
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
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {Object} params
     * @param {boolean} params.typing
     * @returns {Promise}
     */
    _notifyMyselfTyping(params) {
        return session.rpc('/im_livechat/notify_typing', {
            uuid: this.getUUID(),
            is_typing: params.typing,
        }, { shadow: true });
    },
    /**
     * Post a message on this thread
     *
     * @private
     * @returns {Promise} resolved with the message object to be sent to the
     *   server
     */
    _postMessage() {
        return Promise.resolve();
    },
    /**
     * Warn views that the list of users that are currently typing on this
     * livechat has been updated.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @private
     */
    _warnUpdatedTypingPartners() {
        this.trigger_up('updated_typing_partners');
    },
    /**
     * Warn that the unread counter has been updated on this livechat
     *
     * @private
     */
    _warnUpdatedUnreadCounter() {
        this.trigger_up('updated_unread_counter');
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Override so that it only unregister typing operators.
     *
     * Note that in the frontend, there is no way to identify a message that is
     * from the current user, because there is no partner ID in the session and
     * a message with an author sets the partner ID of the author.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {mail.model.AbstractMessage} message
     */
     _onTypingMessageAdded(message) {
        const operatorID = this.getOperatorPID()[0];
        if (message.hasAuthor() && message.getAuthorID() === operatorID) {
            this.unregisterTyping({ partnerID: operatorID });
        }
    },
});

export default PublicLivechat;
