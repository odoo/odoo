odoo.define('mail.model.Channel', function (require) {
"use strict";

var ChannelPreview = require('mail.model.ChannelPreview');
var Conversation = require('mail.model.Conversation');

var time = require('web.time');

var Channel = Conversation.extend({
    /**
     * @param {mail.ChatManager} parent
     * @param {Object} data
     * @param {string} [data.anonymous_name]
     * @param {string} data.channel_type
     * @param {Object} [data.direct_partner]
     * @param {integer} [data.direct_partner.id]
     * @param {string} [data.direct_partner.im_status]
     * @param {string} [data.direct_partner.name]
     * @param {*} data.group_based_subscription
     * @param {boolean} [data.is_minimized = false]
     * @param {string} [data.last_message_date] date in server-format
     * @param {boolean} [data.mass_mailing]
     * @param {integer} [data.message_unread_counter]
     * @param {string|Object} [data.name] an object for mailboxes, because of _lt
     * @param {Object[]} [data.needaction_partner_ids]
     * @param {string} [data.public] either 'public' or 'private'
     * @param {integer} [data.seen_message_id]
     * @param {string} data.state
     * @param {string} [data.type]
     * @param {string} [data.uuid]
     * @param {Object} options
     * @param {boolean} [options.autoswitch = true]
     * @param {boolean} [options.hidden]
     * @param {Object[]} commands
     */
    init: function (parent, data, options, commands) {
        var self = this;
        this._super.apply(this, arguments);

        /**
         * If set, autoswitch channel on joining this channel in discuss
         * the default behaviour is to autoswitch on join.
         * exception: receiving channel or chat session notifications
         */
        this.autoswitch = 'autoswitch' in options ? options.autoswitch : true;
        this.directPartnerID = undefined;


        this._chat = undefined;
        this._commands = undefined;
        this._detached = data.is_minimized;
        this._folded = data.state === 'folded';
        /**
         * if set: hide 'Leave channel' button
         */
        this._groupBasedSubscription = data.group_based_subscription;
        this._lastMessageDate = undefined;
        this._lastSeenMessageID = data.seen_message_id;
        /**
         * if set: display subject on message, use extended composer and show
         * "Send by messages by email" on discuss sidebar
         */
        this._massMailing = data.mass_mailing;
        /**
         * Deferred that is resolved on fetched members of this channel.
         */
        this._membersDef = undefined;
        /**
         * number of messages that are 'needaction', which is equivalent to the
         * number of messages in this channel that are in inbox.
         */
        this._needactionCounter = data.message_needaction_counter || 0;
        /**
         * On 1st request to getPreview, fetch data if incomplete. Otherwise it
         * means that there is no message in this channel.
         */
        this._previewed = false;
        this._serverType = data.channel_type;
        this._status = undefined;
        this._throttleFetchSeen = _.throttle(this._fetchSeen.bind(this), 3000);
        /**
         * unique identifier for this channel, which is required for some rpc
         */
        this._uuid = data.uuid;

        /**
         * list of commands available for this channel
         */
        this._commands = _.filter(commands, function (command) {
            return !command.channel_types || _.contains(command.channel_types, self._serverType);
        });


        if (this._type === 'channel') {
            this._type = data.public !== 'private' ? 'public' : 'private';
        }
        if (_.size(data.direct_partner) > 0) {
            // this is a DM channel
            this._type = 'dm';
            this._name = data.direct_partner[0].name;
            this.directPartnerID = data.direct_partner[0].id;
            this._status = data.direct_partner[0].im_status;
        } else if ('anonymous_name' in data) {
            this._name = data.anonymous_name;
        }
        if (data.last_message_date) {
            this._lastMessageDate = moment(time.str_to_datetime(data.last_message_date));
        }
        this._chat = !this.getType().match(/^(public|private|mailbox)$/);
        if (data.message_unread_counter) {
            this.updateUnreadCounter(data.message_unread_counter);
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Close the channel
     *
     * This operation is executed server-side and the chat window will be
     * folded in all potential tabs from all browsers.
     *
     * @override
     */
    close: function () {
        this._super.apply(this, arguments);
        this._rpc({
                model: 'mail.channel',
                method: 'channel_fold',
                kwargs: { uuid: this.getUUID(), state: 'closed' },
            }, { shadow: true });
    },
    /**
     * Open the chat window for this channel
     * (in all potential tabs from all browsers)
     *
     * @pverride
     */
    detach: function () {
        this._super.apply(this, arguments);
        this._rpc({
            model: 'mail.channel',
            method: 'channel_minimize',
            args: [this.getUUID(), true],
        }, {
            shadow: true,
        });
    },
    /**
     * Force fetch members of the channel
     *
     * @return {$.Promise<Object[]>} resolved with list of channel listeners
     */
    forceFetchMembers: function () {
        this._membersDef = undefined;
        return this.getMentionPartnerSuggestions();
    },
    /**
     * Folds/Minimize the channel
     * (in all potential tabs from all browsers)
     *
     * @override
     * @param  {boolean} folded
     */
    fold: function (folded) {
        this._super.apply(this, arguments);
        var args = {
            uuid: this.getUUID(),
        };
        if (_.isBoolean(folded)) {
            args.state = folded ? 'folded' : 'open';
        }
        this._rpc({
                model: 'mail.channel',
                method: 'channel_fold',
                kwargs: args,
            }, {shadow: true});
    },
    /**
     * Show the list of available commands on this channel (e.g. '/help')
     *
     * @override
     * @return {Array} list of commands
     */
    getCommands: function () {
        return this._commands;
    },
    /**
     * @return {mail.model.Message|undefined} last message of the channel, if any
     */
    getLastMessage: function () {
        return _.last(this._cache['[]'].messages);
    },
    /**
     * Return the date of the last message in this channel.
     * If there are no messages in this channel, return 'undefined'
     *
     * @return {moment|undefined}
     */
    getLastMessageDate: function () {
        if (!this.hasMessages()) {
            return undefined;
        }
        return this.getLastMessage().getDate();
    },
    /**
     * Get the last seen message for a given channel
     *
     * @return {mail.model.Message|undefined} last seen message (if any)
     */
    getLastSeenMessage: function () {
        var self = this;
        var result;
        if (this._lastSeenMessageID) {
            var messages = this._cache['[]'].messages;
            var msg = _.find(messages, function (message) {
                return message.getID() === self._lastSeenMessageID;
            });
            if (msg) {
                var previousIndex = _.sortedIndex(messages, msg, function (m) {
                    return m.getID();
                });
                var i = previousIndex + 1;
                while (i < messages.length &&
                    (messages[i].isAuthor() || messages[i].isSystemNotification())) {
                    msg = messages[i];
                    i++;
                }
                result = msg;
            }
        }
        return result;
    },
    /**
     * Get listeners of a channel
     *
     * @return {$.Promise<Object[]>} resolved with list of channel listeners
     */
    getMentionPartnerSuggestions: function () {
        if (!this._membersDef) {
            this._membersDef = this._rpc({
                model: 'mail.channel',
                method: 'channel_fetch_listeners',
                args: [this.getUUID()],
            }, {
                shadow: true
            })
            .then(function (members) {
                return members;
            });
        }
        return this._membersDef;
    },
    /**
     * @return {integer}
     */
    getNeedactionCounter: function () {
        return this._needactionCounter;
    },
    /**
     * Get preview format of this channel
     *
     * @return {mail.model.ChannelPreview}
     */
    getPreview: function () {
        return new ChannelPreview(this);
    },
    /**
     * @return {string}
     */
    getStatus: function () {
        return this._status;
    },
    /**
     * @return {string} uuid of this channel
     */
    getUUID: function () {
        return this._uuid;
    },
    /**
     * State whether this channel has been previewed
     *
     * A channel that has been previewed means that it had the necessary data
     * to display its preview format. A channel needs its meta data and the
     * last message in order to build its preview format.
     *
     * This is useful in order to not fetch preview info on this channel more
     * than once on channels that have no message at all.
     *
     * Any received message updates the last_message, so a channel should
     * always have all the necessary information to display its preview after
     * the 1st time.
     *
     * @return {boolean}
     */
    hasBeenPreviewed: function () {
        return this._previewed;
    },
    /**
     * @return {boolean} true if there is at least a message, false otherwise
     */
    hasMessages: function () {
        return !!(_.last(this._cache['[]'].messages));
    },
    /**
     * State whether there are unread messages in this channel
     *
     * @return {boolean}
     */
    hasUnreadMessages: function () {
        return this._unreadCounter !== 0;
    },
    /**
     * Increment the needaction counter of this channel by 1 unit
     */
    incrementNeedactionCounter: function () {
        this._needactionCounter++;
    },
    /**
     * Increment the unread counter of this channel by 1 unit
     */
    incrementUnreadCounter: function () {
        this._unreadCounter++;
    },
    /**
     * @override
     * @return {boolean}
     */
    isChat: function () {
        return this._chat;
    },
    /**
     * @return {boolean}
     */
    isGroupBasedSubscription: function () {
        return this._groupBasedSubscription;
    },
    /**
     * @return {boolean}
     */
    isMassMailing: function () {
        return this._massMailing;
    },
    /**
     * Mark this channel as previewed
     *
     * This is useful in order to not fetch preview info on this channel
     * is the server has no preview in the first place.
     *
     * Note: preview fetch is useful only when the channel contains messages
     * that have not been fetched at all. After that, this channel instance
     * is updated regularly so that the most up-to-date info are available
     * to make the preview of this channel.
     */
    markAsPreviewed: function () {
        this._previewed = true;
    },
    /**
     * Marks this channel as seen.
     * The seen message will be the last message.
     * Resolved with the last seen message, only for non-mailbox channels
     *
     * @override
     * @return {$.Promise<integer|undefined>} last message id seen in the channel
     */
    markAsSeen: function () {
        if (this._unreadCounter > 0) {
            this.updateUnreadCounter(0);
            return this._throttleFetchSeen();
        }
        return $.when();
    },
    /**
     * Prepare and send a message to the server on this channel
     *
     * @param  {Object} data data related to the new message
     * @return {$.Promise}
     */
    postMessage: function (data) {
        var msg = this._chatManager.makeBasicPostMessage(data);
        return this._rpc({
            model: 'mail.channel',
            method: data.command ? 'execute_command' : 'message_post',
            args: [this._id],
            kwargs: _.extend(msg, {
                message_type: 'comment',
                content_subtype: 'html',
                subtype: 'mail.mt_comment',
                command: data.command,
            }),
        });
    },
    /**
     * Set 'msgID' as the id of the last message seen in this channel
     *
     * @param {integer} msgID
     */
    setLastSeenMessageID: function (msgID) {
        this._lastSeenMessageID = msgID;
    },
    /**
     * Set the new value of the needaction counter of this channel
     *
     * @param {integer} newValue
     */
    setNeedactionCounter: function (newValue) {
        this._needactionCounter = newValue;
    },
    /**
     * @param {string} newStatus
     */
    setStatus: function (newStatus) {
        this._status = newStatus;
    },
    /**
     * Set the new value of the unread counter of this channel
     *
     * @param {integer} newValue
     */
    setUnreadCounter: function (newValue) {
        this._unreadCounter = newValue;
    },
    /**
     * Unsubscribes from channel
     *
     * @return {$.Promise} resolve when unsubscribed
     */
    unsubscribe: function () {
        if (_.contains(['public', 'private'], this.getType())) {
            // unfollow channel
            return this._rpc({
                model: 'mail.channel',
                method: 'action_unfollow',
                args: [[this._id]],
            });
        } else {
            // unpin dm
            return this._rpc({
                model: 'mail.channel',
                method: 'channel_pin',
                args: [this.getUUID(), false],
            });
        }
    },
    /**
     * @private
     * @param {integer} counter
     */
    updateUnreadCounter: function (counter) {
        if (this._unreadCounter > 0 && counter === 0) {
            this._chatManager.decrementUnreadConversationCounter();
        } else if (this._unreadCounter === 0 && counter > 0) {
            this._chatManager.incrementUnreadConversationCounter();
        }
        this._unreadCounter = counter;
        this._chatBus.trigger('update_conversation_unread_counter', this);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {$.Promise<integer>} resolved with ID of last seen message
     */
    _fetchSeen: function () {
        return this._rpc({
            model: 'mail.channel',
            method: 'channel_seen',
            args: [[this._id]],
        }, {
            shadow: true
        });
    },
});

return Channel;

});
