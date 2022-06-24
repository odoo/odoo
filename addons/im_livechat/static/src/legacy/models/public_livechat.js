/** @odoo-module **/

import CCThrottleFunction from '@im_livechat/legacy/models/cc_throttle_function';
import Timer from '@im_livechat/legacy/models/timer';
import Timers from '@im_livechat/legacy/models/timers';

import Class from 'web.Class';
import { _t } from 'web.core';
import session from 'web.session';
import Mixins from 'web.mixins';
import { sprintf } from 'web.utils';

/**
 * Thread model that represents a livechat on the website-side. This livechat
 * is not linked to the mail service.
 */
const PublicLivechat = Class.extend(Mixins.EventDispatcherMixin, {
    // Default partner infos
    _DEFAULT_TYPING_PARTNER_ID: '_default',
    _DEFAULT_TYPING_PARTNER_NAME: 'Someone',
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

        /**
         * Initialize the internal data for typing feature on threads.
         *
         * Also listens on some internal events of the thread:
         *
         * - 'message_added': when a message is added, remove the author in the
         *     typing partners.
         * - 'message_posted': when a message is posted, let the user have the
         *     possibility to immediately notify if he types something right away,
         *     instead of waiting for a throttle behaviour.
         */

        // Store the last "myself typing" status that has been sent to the
        // server. This is useful in order to not notify the same typing
        // status multiple times.
        this._lastNotifiedMyselfTyping = false;

        // Timer of current user that is typing a very long text. When the
        // receivers do not receive any typing notification for a long time,
        // they assume that the related partner is no longer typing
        // something (e.g. they have closed the browser tab).
        // This is a timer to let others know that we are still typing
        // something, so that they do not assume we stopped typing
        // something.
        this._myselfLongTypingTimer = new Timer({
            duration: 50 * 1000,
            onTimeout: this._onMyselfLongTypingTimeout.bind(this),
        });

        // Timer of current user that was currently typing something, but
        // there is no change on the input for several time. This is used
        // in order to automatically notify other users that we have stopped
        // typing something, due to making no changes on the composer for
        // some time.
        this._myselfTypingInactivityTimer = new Timer({
            duration: 5 * 1000,
            onTimeout: this._onMyselfTypingInactivityTimeout.bind(this),
        });

        // Timers of users currently typing in the thread. This is useful
        // in order to automatically unregister typing users when we do not
        // receive any typing notification after a long time. Timers are
        // internally indexed by partnerID. The current user is ignored in
        // this list of timers.
        this._othersTypingTimers = new Timers({
            duration: 60 * 1000,
            onTimeout: this._onOthersTypingTimeout.bind(this),
        });

        // Clearable and cancellable throttled version of the
        // `doNotifyMyselfTyping` method. (basically `notifyMyselfTyping`
        // with slight pre- and post-processing)
        // @see {mail.model.ResetableThrottleFunction}
        // This is useful when the user posts a message and types something
        // else: he must notify immediately that he is typing something,
        // instead of waiting for the throttle internal timer.
        this._throttleNotifyMyselfTyping = CCThrottleFunction({
            duration: 2.5 * 1000,
            func: this._onNotifyMyselfTyping.bind(this),
        });

        // This is used to track the order of registered partners typing
        // something, in order to display the oldest typing partners.
        this._typingPartnerIDs = [];

        this.on('message_added', this, this._onTypingMessageAdded);
        this.on('message_posted', this, this._onTypingMessagePosted);


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
     * Get the text to display when some partners are typing something on the
     * thread:
     *
     * - single typing partner:
     *
     *   A is typing...
     *
     * - two typing partners:
     *
     *   A and B are typing...
     *
     * - three or more typing partners:
     *
     *   A, B and more are typing...
     *
     * The choice of the members name for display is not random: it displays
     * the user that have been typing for the longest time. Also, this function
     * is hard-coded to display at most 2 partners. This limitation comes from
     * how translation works in Odoo, for which unevaluated string cannot be
     * translated.
     *
     * @returns {string} list of members that are typing something on the thread
     *   (excluding the current user).
     */
    getTypingMembersToText() {
        const typingPartnerIDs = this._typingPartnerIDs;
        const typingMembers = _.filter(this._members, function (member) {
            return _.contains(typingPartnerIDs, member.id);
        });
        const sortedTypingMembers = _.sortBy(typingMembers, function (member) {
            return _.indexOf(typingPartnerIDs, member.id);
        });
        const displayableTypingMembers = sortedTypingMembers.slice(0, 3);

        if (displayableTypingMembers.length === 0) {
            return '';
        } else if (displayableTypingMembers.length === 1) {
            return sprintf(_t("%s is typing..."), displayableTypingMembers[0].name);
        } else if (displayableTypingMembers.length === 2) {
            return sprintf(_t("%s and %s are typing..."),
                                    displayableTypingMembers[0].name,
                                    displayableTypingMembers[1].name);
        } else {
            return sprintf(_t("%s, %s and more are typing..."),
                                    displayableTypingMembers[0].name,
                                    displayableTypingMembers[1].name);
        }
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
     * Threads with this mixin have the typing notification feature
     *
     * @returns {boolean}
     */
    hasTypingNotification() {
        return true;
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
     * Tells if someone other than current user is typing something on this
     * thread.
     *
     * @returns {boolean}
     */
    isSomeoneTyping() {
        return !(_.isEmpty(this._typingPartnerIDs));
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
     * Register someone that is currently typing something in this thread.
     * If this is the current user that is typing something, don't do anything
     * (we do not have to display anything)
     *
     * This method is ignored if we try to register the current user.
     *
     * @param {Object} params
     * @param {integer} params.partnerID ID of the partner linked to the user
     *   currently typing something on the thread.
     */
    registerTyping(params) {
        if (this._isTypingMyselfInfo(params)) {
            return;
        }
        const partnerID = params.partnerID;
        this._othersTypingTimers.registerTimer({
            timeoutCallbackArguments: [partnerID],
            timerID: partnerID,
        });
        if (_.contains(this._typingPartnerIDs, partnerID)) {
            return;
        }
        this._typingPartnerIDs.push(partnerID);
        this._warnUpdatedTypingPartners();
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
     * This method must be called when the user starts or stops typing something
     * in the composer of the thread.
     *
     * @param {Object} params
     * @param {boolean} params.typing tell whether the current is typing or not.
     */
    setMyselfTyping(params) {
        const typing = params.typing;
        if (this._lastNotifiedMyselfTyping === typing) {
            this._throttleNotifyMyselfTyping.cancel();
        } else {
            this._throttleNotifyMyselfTyping(params);
        }

        if (typing) {
            this._myselfTypingInactivityTimer.reset();
        } else {
            this._myselfTypingInactivityTimer.clear();
        }
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
    /**
     * Unregister someone from currently typing something in this thread.
     *
     * @param {Object} params
     * @param {integer} params.partnerID ID of the partner related to the user
     *   that is currently typing something
     */
    unregisterTyping(params) {
        const partnerID = params.partnerID;
        this._othersTypingTimers.unregisterTimer({ timerID: partnerID });
        if (!_.contains(this._typingPartnerIDs, partnerID)) {
            return;
        }
        this._typingPartnerIDs = _.reject(this._typingPartnerIDs, function (id) {
            return id === partnerID;
        });
        this._warnUpdatedTypingPartners();
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
     * Tells whether the provided information on a partner is related to the
     * current user or not.
     *
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
     * Notify to the server that the current user either starts or stops typing
     * something.
     *
     * @private
     * @param {Object} params
     * @param {boolean} params.typing whether we are typing something or not
     * @returns {Promise} resolved if the server is notified, rejected
     *   otherwise
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
     * Called when current user is typing something for a long time. In order
     * to not let other users assume that we are no longer typing something, we
     * must notify again that we are typing something.
     *
     * @private
     */
    _onMyselfLongTypingTimeout() {
        this._throttleNotifyMyselfTyping.clear();
        this._throttleNotifyMyselfTyping({ typing: true });
    },
    /**
     * Called when current user has something typed in the composer, but is
     * inactive for some time. In this case, he automatically notifies that he
     * is no longer typing something
     *
     * @private
     */
    _onMyselfTypingInactivityTimeout() {
        this._throttleNotifyMyselfTyping.clear();
        this._throttleNotifyMyselfTyping({ typing: false });
    },
    /**
     * Called by throttled version of notify myself typing
     *
     * Notify to the server that the current user either starts or stops typing
     * something. Remember last notified stuff from the server, and update
     * related typing timers.
     *
     * @private
     * @param {Object} params
     * @param {boolean} params.typing whether we are typing something or not.
     */
    _onNotifyMyselfTyping(params) {
        const typing = params.typing;
        this._lastNotifiedMyselfTyping = typing;
        this._notifyMyselfTyping(params);
        if (typing) {
            this._myselfLongTypingTimer.reset();
        } else {
            this._myselfLongTypingTimer.clear();
        }
    },
    /**
     * Called when current user do not receive a typing notification of someone
     * else typing for a long time. In this case, we assume that this person is
     * no longer typing something.
     *
     * @private
     * @param {integer} partnerID partnerID of the person we assume he is no
     *   longer typing something.
     */
    _onOthersTypingTimeout(partnerID) {
        this.unregisterTyping({ partnerID });
    },
    /**
     * Called when a new message is added to the thread
     * On receiving a message from a typing partner, unregister this partner
     * from typing partners (otherwise, it will still display it until timeout).
     *
     * Note that it only unregister typing operators.
     *
     * Note that in the frontend, there is no way to identify a message that is
     * from the current user, because there is no partner ID in the session and
     * a message with an author sets the partner ID of the author.
     *
     * @private
     * @param {mail.model.AbstractMessage} message
     */
    _onTypingMessageAdded(message) {
        const operatorID = this.getOperatorPID()[0];
        if (message.hasAuthor() && message.getAuthorID() === operatorID) {
            this.unregisterTyping({ partnerID: operatorID });
        }
    },
    /**
     * Called when current user has posted a message on this thread.
     *
     * The current user receives the possibility to immediately notify the
     * other users if he is typing something else.
     *
     * Refresh the context for the current user to notify that he starts or
     * stops typing something. In other words, when this function is called and
     * then the current user types something, it immediately notifies the
     * server as if it is the first time he is typing something.
     *
     * @private
     */
    _onTypingMessagePosted() {
        this._lastNotifiedMyselfTyping = false;
        this._throttleNotifyMyselfTyping.clear();
        this._myselfLongTypingTimer.clear();
        this._myselfTypingInactivityTimer.clear();
    },
});

export default PublicLivechat;
