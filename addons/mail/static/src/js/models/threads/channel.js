odoo.define('mail.model.Channel', function (require) {
"use strict";

var SearchableThread = require('mail.model.SearchableThread');
var ThreadTypingMixin = require('mail.model.ThreadTypingMixin');
var mailUtils = require('mail.utils');

const config = require('web.config');
var session = require('web.session');
var time = require('web.time');

/**
 * This class represent channels in JS. In this context, the word channel
 * has the same meaning of channel on the server, meaning that direct messages
 * (DM) and livechats are also channels.
 *
 * Any piece of code in JS that make use of channels must ideally interact with
 * such objects, instead of direct data from the server.
 */
var Channel = SearchableThread.extend(ThreadTypingMixin, {
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.data
     * @param {string} params.data.channel_type
     * @param {integer} [params.data.create_uid] the ID of the user that has
     *   created the channel.
     * @param {boolean} params.data.group_based_subscription
     * @param {boolean} [params.data.is_minimized=false]
     * @param  {boolean} params.data.is_moderator whether the current user is
     *   moderator of this channel.
     * @param {string} [params.data.last_message_date] date in server-format
     * @param {Object[]} [params.data.members=[]]
     * @param {integer} [params.data.members[i].id]
     * @param {string} [params.data.members[i].name]
     * @param {string} [params.data.members[i].email]
     * @param {integer} [params.data.message_unread_counter]
     * @param {boolean} [params.data.moderation=false] whether the channel is
     *   moderated or not
     * @param {Object[]} [params.data.partners_info=[]]
     * @param {integer} [params.data.partners_info[i].partner_id]
     * @param {integer} [params.data.partners_info[i].fetched_message_id]
     * @param {integer} [params.data.partners_info[i].seen_message_id]
     * @param {string} params.data.state
     * @param {string} [params.data.uuid]
     * @param {Object} params.options
     * @param {boolean} [params.options.autoswitch=true]
     * @param {Object[]} params.commands
     */
    init: function (params) {
        var self = this;
        this._super.apply(this, arguments);
        ThreadTypingMixin.init.apply(this, arguments);

        var data = params.data;
        var options = params.options;
        var commands = params.commands;

        // If set, autoswitch channel on joining this channel in discuss
        // the default behaviour is to autoswitch on join.
        // exception: receiving channel session notifications
        this._autoswitch = 'autoswitch' in options ? options.autoswitch : true;
        this._commands = undefined;
        this._creatorUID = data.create_uid;
        this._detached = data.is_minimized || false;
        this._directPartnerID = undefined;
        this._folded = data.state === 'folded';
        // if set: hide 'Leave channel' button
        this._groupBasedSubscription = data.group_based_subscription;
        this._isModerated = data.moderation;
        this._isMyselfModerator = data.is_moderator;
        this._lastMessageDate = undefined;
        this._members = data.members || [];
        // Promise that is resolved on fetched members of this channel.
        this._membersDef = undefined;
        // number of messages that are 'needaction', which is equivalent to the
        // number of messages in this channel that are in inbox.
        this._needactionCounter = data.message_needaction_counter || 0;
        this._serverType = data.channel_type;
        // unique identifier for this channel, which is required for some rpc
        this._uuid = data.uuid;

        // * list of commands available for this channel
        this._commands = _.filter(commands, function (command) {
            return !command.channel_types ||
                    _.contains(command.channel_types, self._serverType);
        });
        if (data.last_message_date) {
            this._lastMessageDate = moment(time.str_to_datetime(data.last_message_date));
        }
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
        // Do not notify the server to avoid desktop chat window from closing
        // when a chat window is closed on mobile.
        if (!config.device.isMobile) {
            this._rpc({
                    model: 'mail.channel',
                    method: 'channel_fold',
                    kwargs: { uuid: this.getUUID(), state: 'closed' },
                }, { shadow: true });
        }
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
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            // Do not notify the server to avoid desktop chat window from opening
            // when a chat window is opened on mobile.
            if (!config.device.isMobile) {
                self._rpc({
                    model: 'mail.channel',
                    method: 'channel_minimize',
                    args: [self.getUUID(), true],
                }, {
                    shadow: true,
                });
            }
        });
    },
    /**
     * Force fetch members of the channel
     *
     * @returns {Promise<Object[]>} resolved with list of channel listeners
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
     * @returns {Promise<Object[]>} resolved with list of list of
     *   channel listeners.
     */
    getMentionPartnerSuggestions: function () {
        var self = this;
        if (!this._membersDef) {
            this._membersDef = this._rpc({
                model: 'mail.channel',
                method: 'channel_fetch_listeners',
                args: [this.getUUID()],
            }, {
                shadow: true
            })
            .then(function (members) {
                self._members = members;
                return [members];
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
        if (!this.isTwoUserThread()) {
            result.imageSRC = '/web/image/mail.channel/' + this.getID() + '/image_128';
        }
        var lastMessage = this.getLastMessage();
        return _.extend(result, {
            author: lastMessage ? lastMessage.getDisplayedAuthor() : '',
            body: lastMessage ? mailUtils.htmlToTextContentInline(lastMessage.getBody()) : '',
            date: lastMessage ? lastMessage.getDate() : undefined,
            isMyselfAuthor: this.hasMessages() && this.getLastMessage().isMyselfAuthor(),
        });
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
        return this._isModerated;
    },
    /**
     * Tells whether the current user is administrator of the channel.
     * Note that there is no administrator for two-user channels
     *
     * @returns {boolean}
     */
    isMyselfAdministrator: function () {
        return session.uid === this._creatorUID && !this.isTwoUserThread();
    },
    /**
     * States whether the current user is moderator of this channel.
     *
     * @returns {boolean}
     */
    isMyselfModerator: function () {
        return this._isMyselfModerator;
    },
    /**
     * Unsubscribes from channel
     *
     * @abstract
     * @returns {Promise} resolve when unsubscribed
     */
    unsubscribe: function () {},
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
     * Override so that it tells whether the channel is moderated or not. This
     * is useful in order to display pending moderation messages when the
     * current user is either moderator of the channel or has posted some
     * messages that are pending moderation.
     *
     * @override
     * @private
     * @returns {Object}
     */
    _getFetchMessagesKwargs: function () {
        var kwargs = this._super.apply(this, arguments);
        if (this.isModerated()) {
            kwargs.moderated_channel_ids = [this.getID()];
        }
        return kwargs;
    },
    /**
     * Get the domain to fetch all the messages in the current channel
     *
     * @override
     * @private
     * @returns {Array}
     */
    _getThreadDomain: function () {
        return [['channel_ids', 'in', [this._id]]];
    },
    /**
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {Object} params
     * @param {integer} params.partnerID
     */
    _isTypingMyselfInfo: function (params) {
        return session.partner_id === params.partnerID;
    },
    /**
     * Marks this channel as read.
     * The last seen message will be the last message.
     * Resolved with the last seen message, only for non-mailbox channels
     *
     * @override
     * @private
     * @returns {Promise} resolved when message has been marked as read
     */
    _markAsRead: function () {
        var superDef = this._super.apply(this, arguments);
        var seenDef = this._notifySeen();
        return Promise.all([superDef, seenDef]);
    },
    /**
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {Object} params
     * @param {boolean} params.typing
     * @returns {Promise}
     */
    _notifyMyselfTyping: function (params) {
        return this._rpc({
            model: 'mail.channel',
            method: 'notify_typing',
            args: [this.getID()],
            kwargs: { is_typing: params.typing },
        }, { shadow: true });
    },
    /**
     * @private
     * @returns {$.Promise<integer>} resolved with ID of last seen message
     */
    _notifySeen: function () {
        var self = this;
        return this._rpc({
            model: 'mail.channel',
            method: 'channel_seen',
            args: [[this._id]],
        }, { shadow: true }).then(function (lastSeenMessageID) {
            self._lastSeenMessageID = lastSeenMessageID;
            return lastSeenMessageID;
        });
    },
    /**
     * Prepare and send a message to the server on this channel.
     *
     * @override
     * @private
     * @param {Object} data data related to the new message
     * @returns {Promise<Object>} resolved when the message has been sent to
     *   the server, with the object message that has been sent to the server.
     */
    _postMessage: function (data) {
        var self = this;
        return this._super.apply(this, arguments).then(function (messageData) {
            _.extend(messageData, {
                message_type: 'comment',
                subtype_xmlid: 'mail.mt_comment',
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
     * Warn views that the list of users that are currently typing on this
     * thread has been updated.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @private
     */
    _warnUpdatedTypingPartners: function () {
        this.call('mail_service', 'getMailBus')
            .trigger('update_typing_partners', this.getID());
    },
});

return Channel;

});
