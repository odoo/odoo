odoo.define('mail.model.Channel', function (require) {
"use strict";

var ThreadWithCache = require('mail.model.ThreadWithCache');
var mailUtils = require('mail.utils');

var time = require('web.time');

/**
 * This class represent channels in JS. In this context, the word channel
 * has the same meaning of channel on the server, meaning that direct messages
 * (DM) and livechats are also channels.
 *
 * Any piece of code in JS that make use of channels must ideally interact with
 * such objects, instead of direct data from the server.
 */
var Channel = ThreadWithCache.extend({
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.data
     * @param {string} [params.data.anonymous_name]
     * @param {string} params.data.channel_type
     * @param {boolean} params.data.group_based_subscription
     * @param {boolean} [params.data.is_minimized=false]
     * @param  {boolean} params.data.is_moderator whether the current user is
     *   moderator of this channel.
     * @param {string} [params.data.last_message_date] date in server-format
     * @param {boolean} [params.data.mass_mailing]
     * @param {integer} [params.data.message_unread_counter]
     * @param {string} [params.data.public] either 'public' or 'private'
     * @param {string} params.data.state
     * @param {string} [params.data.uuid]
     * @param {Object} params.options
     * @param {boolean} [params.options.autoswitch=true]
     * @param {Object[]} params.commands
     */
    init: function (params) {
        var self = this;
        this._super.apply(this, arguments);

        var data = params.data;
        var options = params.options;
        var commands = params.commands;

        // If set, autoswitch channel on joining this channel in discuss
        // the default behaviour is to autoswitch on join.
        // exception: receiving channel or chat session notifications
        this._autoswitch = 'autoswitch' in options ? options.autoswitch : true;
        this._chat = undefined; // FIXME: could be dropped when livechat and DM are moved out of this class
        this._commands = undefined;
        this._detached = data.is_minimized;
        this._directPartnerID = undefined;
        this._folded = data.state === 'folded';
        // if set: hide 'Leave channel' button
        this._groupBasedSubscription = data.group_based_subscription;
        this._isModerator = data.is_moderator;
        this._lastMessageDate = undefined;
        this._massMailing = data.mass_mailing;
        // Deferred that is resolved on fetched members of this channel.
        this._membersDef = undefined;
        this._moderation = data.is_moderation;
        // number of messages that are 'needaction', which is equivalent to the
        // number of messages in this channel that are in inbox.
        this._needactionCounter = data.message_needaction_counter || 0;
        this._serverType = data.channel_type;
        this._status = undefined;
        this._throttleFetchSeen = _.throttle(this._fetchSeen.bind(this), 3000);
        // unique identifier for this channel, which is required for some rpc
        this._uuid = data.uuid;

        // * list of commands available for this channel
        this._commands = _.filter(commands, function (command) {
            return !command.channel_types ||
                    _.contains(command.channel_types, self._serverType);
        });
        if (this._type === 'channel') {
            this._type = data.public !== 'private' ? 'public' : 'private';
        }
        if ('anonymous_name' in data) {
            this._name = data.anonymous_name;
        }
        if (data.last_message_date) {
            this._lastMessageDate = moment(time.str_to_datetime(data.last_message_date));
        }
        this._chat = !this.getType().match(/^(public|private)$/);
        if (data.message_unread_counter) {
            this._unreadCounter = data.message_unread_counter;
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
     * Decrement the needaction counter of the channel
     * Floor value at 0.
     *
     * @param {integer} [num=1] the amount to decrement at most
     */
    decrementNeedactionCounter: function (num) {
        num = _.isNumber(num) ? num : 1;
        this._needactionCounter = Math.max(this._needactionCounter - 1, 0);
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
     * @returns {$.Promise<Object[]>} resolved with list of channel listeners
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
     * @param {boolean} folded
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
     * @returns {Array} list of commands
     */
    getCommands: function () {
        return this._commands;
    },
    /**
     * @returns {mail.model.Message|undefined} last message of channel, if any
     */
    getLastMessage: function () {
        return _.last(this._cache['[]'].messages);
    },
    /**
     * Get listeners of a channel
     *
     * @returns {$.Promise<Object[]>} resolved with list of channel listeners
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
     * @returns {integer}
     */
    getNeedactionCounter: function () {
        return this._needactionCounter;
    },
    /**
     * @override
     */
    getPreview: function () {
        var result = this._super.apply(this, arguments);
        if (!this.isChat()) {
            result.imageSRC = '/web/image/mail.channel/' + this.getID() + '/image_small';
        }
        var lastMessage = this.getLastMessage();
        return _.extend(result, {
            author: lastMessage ? lastMessage.getDisplayedAuthor() : '',
            body: lastMessage ? mailUtils.parseAndTransform(lastMessage.getBody(), mailUtils.inline) : '',
            date: lastMessage ? lastMessage.getDate() : moment(),
            isAuthor: this.hasMessages() && this.getLastMessage().isAuthor(),
        });
    },
    /**
     * Returns the title to display in thread window's headers.
     * For channels, the title is prefixed with "#".
     *
     * @override
     * @returns {string|Object} the name of the thread by default (see getName)
     */
    getTitle: function () {
        return "#" + this._super.apply(this, arguments);
    },
    /**
     * Get the UUID of the channel.
     * This is a string that uniquely links this channel to a server channel.
     *
     * @returns {string} uuid of this channel
     */
    getUUID: function () {
        return this._uuid;
    },
    /**
     * Increment the needaction counter of this channel by 1 unit
     */
    incrementNeedactionCounter: function () {
        this._needactionCounter++;
    },
    /**
     * States whether the channel should be auto-selected on creation
     *
     * Note that this is not of the responsibility of the channel
     * (see mail.model.Thread for more information)
     *
     * @override
     * @returns {boolean}
     */
    isAutoswitch: function () {
        return this._autoswitch;
    },
    /**
     * All instances of this class are chanels
     *
     * @override
     * @returns {boolean}
     */
    isChannel: function () {
        return true;
    },
    /**
     * States whether this channel is a chat or not.
     * These types of channels are chat:
     * - direct messages (DM)
     * - livechat
     *
     * @override
     * @returns {boolean}
     */
    isChat: function () {
        return this._chat;
    },
    /**
     * States whether the channel auto-subscribes some users in a group
     *
     * @returns {boolean}
     */
    isGroupBasedSubscription: function () {
        return this._groupBasedSubscription;
    },
    /**
     * States whether the channel is moderated or not.
     *
     * @override
     * @returns {boolean}
     */
    isModerated: function () {
        return this._moderation;
    },
    /**
     * States whether the current user is moderator of this channel.
     *
     * @returns {boolean}
     */
    isModerator: function () {
        return this._isModerator;
    },
    /**
     * Marks this channel as read.
     * The last seen message will be the last message.
     * Resolved with the last seen message, only for non-mailbox channels
     *
     * @override
     * @returns {$.Promise<integer|undefined>} resolved with last message ID
     *   seen in the channel, and when the channel has been marked as seen on
     *   the server.
     */
    markAsRead: function () {
        if (this._unreadCounter > 0) {
            this.resetUnreadCounter();
            return this._throttleFetchSeen();
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Prepare and send a message to the server on this channel
     *
     * @override
     * @param {Object} data data related to the new message
     * @returns {$.Promise<Object>} resolved when the message has been sent to
     *   the server, with the object message that has been sent to the server.
     */
    postMessage: function (data) {
        var self = this;
        return this._super.apply(this, arguments).then(function (messageData) {
            _.extend(messageData, {
                message_type: 'comment',
                subtype: 'mail.mt_comment',
                command: data.command,
            });
            return self._rpc({
                    model: 'mail.channel',
                    method: data.command ? 'execute_command' : 'message_post',
                    args: [self._id],
                    kwargs: messageData,
                }).then(function () {
                    return messageData;
                });
        });
    },
    /**
     * Unsubscribes from channel
     *
     * @returns {$.Promise} resolve when unsubscribed
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
            // unpin livechat
            return this._rpc({
                model: 'mail.channel',
                method: 'channel_pin',
                args: [this.getUUID(), false],
            });
        }
    },
    /**
     * Updates the internal state of the channel, and reflects the changes in
     * the UI.
     *
     * Called by {mail.Manager.Notification} on receiving a channel window
     * notification. A notification is received after a client-side action
     * that changes the state of the channel window visually, so that cross tab
     * channels are updated similarly.
     *
     * TODO: This method should be dropped if the state of windows are
     * completely handled client-side, which should be the case in the near
     * future.
     *
     * @param {Object} params
     * @param {boolean} params.detached
     * @param {boolean} params.folded
     */
    updateWindowState: function (params) {
        this._folded = 'folded' in params ? params.folded : this._folded;
        this._detached = 'detached' in params ? params.detached : this._detached;
        this._warnUpdatedWindowState();
    },
    /**
     * Reset the needaction counter to 0.
     */
    resetNeedactionCounter: function () {
        this._needactionCounter = 0;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {$.Promise<integer>} resolved with ID of last seen message
     */
    _fetchSeen: function () {
        var self = this;
        return this._rpc({
            model: 'mail.channel',
            method: 'channel_seen',
            args: [[this._id]],
        }, {
            shadow: true
        }).then(function (lastSeenMessageID) {
            self._lastSeenMessageID = lastSeenMessageID;
            return lastSeenMessageID;
        });
    },
    /**
     * Get the domain to fetch all the messages in the current channel
     *
     * Note that with moderation, even though some messages are not really
     * linked to a channel ('channel_ids'), we should nonetheless display them.
     * These messages are fetched from their associated document
     * ('mail.channel' with provided channel ID), and messages that are pending
     * moderation.
     *
     * @override
     * @private
     * @returns {Array}
     */
    _getThreadDomain: function () {
        return ['|', '&', '&',
                ['model', '=', 'mail.channel'],
                ['res_id', 'in', [this._id]],
                ['need_moderation', '=', true],
                ['channel_ids', 'in', [this._id]]];
    },
});

return Channel;

});
