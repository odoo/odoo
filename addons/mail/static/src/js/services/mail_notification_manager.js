odoo.define('mail.Manager.Notification', function (require) {
"use strict";

/**
 * Mail Notification Manager
 *
 * This part of the mail manager is responsible for receiving notifications on
 * the longpoll bus, which are data received from the server.
 */
var MailManager = require('mail.Manager');
var MailFailure = require('mail.model.MailFailure');

var core = require('web.core');
var session = require('web.session');

var _t = core._t;

MailManager.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Remove channel notifications if there is an unsubscribe notification
     * on this channel.
     *
     * @private
     * @param {Object[]} notifications
     * @returns {Object[]} notifications filtered of channel notifications
     *   matching unsubscribe notifs
     */
    _filterNotificationsOnUnsubscribe: function (notifications) {
        var unsubscribedNotif = _.find(notifications, function (notif) {
            return notif[1].info === 'unsubscribe';
        });
        if (unsubscribedNotif) {
            notifications = _.reject(notifications, function (notif) {
                return notif[0][1] === 'mail.channel' &&
                        notif[0][2] === unsubscribedNotif[1].id;
            });
        }
        return notifications;
    },
    /**
     * Called when receiving a notification on a channel (all members of a
     * channel receive this notification)
     *
     * @private
     * @param {Object} params
     * @param {integer} [params.channelID]
     * @param {Object} params.data
     * @param {string} [params.data.info] if set, specify the type of data on
     *   this channel notification
     */
    _handleChannelNotification: function (params) {
        if (params.data && params.data.info === 'typing_status') {
            this._handleChannelTypingNotification(params.channelID, params.data);
        } else if (params.data && params.data.info === 'channel_fetched') {
            this._handleChannelFetchedNotification(params.channelID, params.data);
        } else if (params.data && params.data.info === 'channel_seen') {
            this._handleChannelSeenNotification(params.channelID, params.data);
        } else {
            this._handleChannelMessageNotification(params.data);
        }
    },
    /**
     * Called when a channel has been fetched, and the server responses with the
     * last message fetched. Useful in order to track last message fetched.
     *
     * @private
     * @param {integer} channelID
     * @param {Object} data
     * @param {string} data.info 'channel_fetched'
     * @param {integer} data.last_message_id
     * @param {integer} data.partner_id
     */
    _handleChannelFetchedNotification: function (channelID, data) {
        var channel = this.getChannel(channelID);
        if (!channel) {
            return;
        }
        if (channel.hasSeenFeature()) {
            channel.updateSeenPartnersInfo(data);
        }
    },
    /**
     * Called when a new or updated message is received on a channel
     *
     * @private
     * @param {Object} messageData
     * @param {integer[]} messageData.channel_ids channel IDs of this message
     *   (note that 'pending moderation' messages in moderated channels do not
     *   have the moderated channels in this array).
     */
    _handleChannelMessageNotification: function (messageData) {
        var self = this;
        var def;
        var channelAlreadyInCache = true;
        if (messageData.channel_ids.length === 1) {
            channelAlreadyInCache = !!this.getChannel(messageData.channel_ids[0]);
            def = this.joinChannel(messageData.channel_ids[0], { autoswitch: false });
        } else {
            def = Promise.resolve();
        }
        def.then(function () {
            // don't increment unread if channel wasn't in cache yet as
            // its unread counter has just been fetched
            return self.addMessage(messageData, {
                showNotification: true,
                incrementUnread: channelAlreadyInCache
            });
        });
    },
    /**
     * Called when a channel has been seen, and the server responses with the
     * last message seen. Useful in order to track last message seen.
     *
     * @private
     * @param {integer} channelID
     * @param {Object} data
     * @param {string} data.info 'channel_seen'
     * @param {integer} data.last_message_id
     * @param {integer} data.partner_id
     */
    _handleChannelSeenNotification: function (channelID, data) {
        var channel = this.getChannel(channelID);
        if (!channel) {
            return;
        }
        if (channel.hasSeenFeature()) {
            channel.updateSeenPartnersInfo(data);
        }
        if (session.partner_id !== data.partner_id) {
            return;
        }
        channel.setLastSeenMessageID(data.last_message_id);
        if (channel.hasUnreadMessages()) {
            channel.resetUnreadCounter();
        }
    },
    /**
     * Called when someone starts or stops typing a message in a channel
     *
     * @private
     * @param {integer} channelID
     * @param {Object} typingData
     * @param {boolean} typingData.is_typing
     * @param {boolean} typingData.is_website_user
     * @param {integer} typingData.partner_id
     */
    _handleChannelTypingNotification: function (channelID, typingData) {
        var isWebsiteUser = typingData.is_website_user;
        var partnerID = typingData.partner_id;
        if (partnerID === session.partner_id && !isWebsiteUser) {
            return; // ignore typing notification of myself
        }
        var channel = this.getChannel(channelID);
        if (!channel) {
            return;
        }
        var typingID = {
            isWebsiteUser: typingData.is_website_user,
            partnerID: typingData.partner_id,
        };
        if (typingData.is_typing) {
            channel.registerTyping(typingID);
        } else {
            channel.unregisterTyping(typingID);
        }
    },
     /**
     * On message becoming a need action (pinned to inbox)
     *
     * @private
     * @param {Object} messageData
     * @param {integer[]} messageData.channel_ids
     */
    _handleNeedactionNotification: function (messageData) {
        var self = this;
        var inbox = this.getMailbox('inbox');
        this.addMessage(messageData, {
            incrementUnread: true,
            showNotification: true,
        }).then(function (message) {
            inbox.incrementMailboxCounter();
            _.each(message.getThreadIDs(), function (threadID) {
                var channel = self.getChannel(threadID);
                if (channel) {
                    channel.incrementNeedactionCounter();
                }
            });
            self._mailBus.trigger('update_needaction', inbox.getMailboxCounter());
        });
    },
    /**
     * Called when an activity record has been updated on the server
     *
     * @private
     * @param {Object} data key, value to decide activity created or deleted
     */
    _handlePartnerActivityUpdateNotification: function (data) {
        this._mailBus.trigger('activity_updated', data);
    },
    /**
     * Called to open the channel in detach mode (minimized) even if no new message:
     *
     * @private
     * @param {Object} channelData
     * @param {integer} channelData.id
     * @param {string} [channelData.info]
     * @param {boolean} channelData.is_minimized
     * @param {string} channelData.state
     */
    _handlePartnerChannelMinimizeNotification: function (channelData) {
        var self = this;
        this._addChannel(channelData).then(function (channelID){
            self.getChannel(channelID).detach()
        });
    },
    /**
     * Called when receiving a channel state as a partner notification:
     *
     *  - if it is a new channel, it means we have been invited to this channel
     *  - if it is an existing channel, it means the window state of the channel
     *    may have changed (as this state is stored server-side)
     *
     * @private
     * @param {Object} channelData
     * @param {integer} channelData.id
     * @param {string} [channelData.info]
     * @param {boolean} channelData.is_minimized
     * @param {string} channelData.state
     */
    _handlePartnerChannelNotification: function (channelData) {
        if (
            (channelData.channel_type === 'channel') &&
            (channelData.state === 'open')
        ) {
            // invited to a new channel
            this._addChannel(channelData, { autoswitch: false });
            if (
                !channelData.is_minimized &&
                channelData.info !== 'creation'
            ) {
                this.do_notify(
                    _t("Invitation"),
                    _t("You have been invited to: ") + channelData.name);
            }
        }
        var channel = this.getChannel(channelData.id);
        if (channel && channelData.info !== 'join') {
            channel.updateWindowState({
                folded: channelData.state === 'folded' ? true : false,
                detached: channelData.is_minimized,
            });
        }
    },
    /**
     * Called when receiving a multi_user_channel seen notification. Only
     * the current user is notified. This must be handled as if this is a
     * channel seen notification.
     *
     * Note that this is a 'res.partner' notification because only the current
     * user is notified on channel seen. This is a consequence from disabling
     * the seen feature on multi_user_channel, because we still need to get
     * the last seen message ID in order to display the "New Messages" separator
     * in Discuss.
     *
     * @private
     * @param {Object} data
     * @param {integer} data.channel_id
     * @param {string} data.info 'channel_seen'
     * @param {integer} data.last_message_id
     * @param {integer} data.partner_id
     */
    _handlePartnerChannnelSeenNotification: function (data) {
        this._handleChannelSeenNotification(data.channel_id, data);
    },
    /**
     * Add or remove failure when receiving a failure update message
     *
     * @private
     * @param {Object} datas
     * @param {Object[]} datas.elements list of mail failure data
     * @param {string} datas.elements[].message_id ID of related message that
     *   has a mail failure.
     * @param {Array} datas.elements[].notifications list of notifications
     *   that is related to a mail failure.
     * @param {string} datas.elements[].notifications[0] sending state of a mail
     *   failure (e.g. 'exception').
     */
    _handlePartnerMailFailureNotification: function (datas) {
        var self = this;
        _.each(datas.elements, function (data) {
            var isNewFailure = _.some(data.notifications, function (notif) {
                return notif[0] === 'exception' || notif[0] === 'bounce';
            });
            var matchedFailure = _.find(self._mailFailures, function (failure) {
                return failure.getMessageID() === data.message_id;
            });
            if (matchedFailure) {
                var index = _.findIndex(self._mailFailures, matchedFailure);
                if (isNewFailure) {
                    self._mailFailures[index] = new MailFailure(self, data);
                } else {
                    self._mailFailures.splice(index, 1);
                }
            } else if (isNewFailure) {
                self._mailFailures.push(new MailFailure(self, data));
            }
            var message = _.find(self._messages, function (msg) {
                return msg.getID() === data.message_id;
            });
            if (message) {
                if (isNewFailure) {
                    message.updateCustomerEmailStatus('exception');
                } else {
                    message.updateCustomerEmailStatus('sent');
                }
                self._updateMessageNotificationStatus(data, message);
                self._mailBus.trigger('update_message', message);
            }
        });
        this._mailBus.trigger('update_needaction', this.needactionCounter);
    },
    /**
     * Updates mailbox_inbox when a message has marked as read.
     *
     * @private
     * @param {Object} data
     * @param {integer[]} [data.channel_ids]
     * @param {integer[]} [data.message_ids]
     * @param {string} [data.type]
     */
    _handlePartnerMarkAsReadNotification: function (data) {
        var self = this;
        var history = this.getMailbox('history');
        _.each(data.message_ids, function (messageID) {
            var message = _.find(self._messages, function (msg) {
                return msg.getID() === messageID;
            });
            if (message) {
                self._removeMessageFromThread('mailbox_inbox', message);
                history.addMessage(message);
                self._mailBus.trigger('update_message', message, data.type);
            }
        });
        if (data.channel_ids) {
            _.each(data.channel_ids, function (channelID) {
                var channel = self.getChannel(channelID);
                if (channel) {
                    channel.decrementNeedactionCounter(data.message_ids.length, 0);
                }
            });
        } else {
            // if no channel_ids specified, this is a 'mark all read' in inbox
            _.each(this.getChannels(), function (channel) {
                channel.resetNeedactionCounter();
            });
        }
        var inbox = this.getMailbox('inbox');
        inbox.decrementMailboxCounter(data.message_ids.length);
        this._mailBus.trigger('update_needaction', inbox.getMailboxCounter());
    },
    /**
     * On receiving a message made by the current user, on a moderated channel,
     * which is pending moderation.
     *
     * @private
     * @param {Object} data
     * @param {Object} data.message server-side data of the message
     */
    _handlePartnerMessageAuthorNotification: function (data) {
        this.addMessage(data.message);
    },
    /**
     * Notification to delete several messages locally
     * Useful when a pending moderation message has been rejected, so that
     * this message should not be displayed anymore.
     *
     * @private
     * @param {Object} data
     * @param {Object[]} [data.message_ids] IDs of messages to delete locally.
     */
    _handlePartnerMessageDeletionNotification: function (data) {
        var self = this;
        _.each(data.message_ids, function (messageID) {
            var message = self.getMessage(messageID);
            if (message) {
                message.setModerationStatus('rejected');
            }
        });
    },
    /**
     * On receiving a message pending moderation, and current user is moderator
     * of such message.
     *
     * @param {Object} data notification data
     * @param {Object} data.message data of message
     */
    _handlePartnerMessageModeratorNotification: function (data) {
        var self = this;
        this.addMessage(data.message).then(function () {
            self._mailBus.trigger('update_moderation_counter');
        });
    },
    /**
     * On receiving a notification that is specific to a user
     *
     * @private
     * @param {Object} data structure depending on the type
     * @param {integer} data.id
     */
    _handlePartnerNotification: function (data) {
        if (data.info === 'unsubscribe') {
            this._handlePartnerUnsubscribeNotification(data);
        } else if (data.type === 'toggle_star') {
            this._handlePartnerToggleStarNotification(data);
        } else if (data.type === 'mark_as_read') {
            this._handlePartnerMarkAsReadNotification(data);
        } else if (data.type === 'moderator') {
            this._handlePartnerMessageModeratorNotification(data);
        } else if (data.type === 'author') {
            this._handlePartnerMessageAuthorNotification(data);
        } else if (data.type === 'deletion') {
            this._handlePartnerMessageDeletionNotification(data);
        } else if (data.info === 'transient_message') {
            this._handlePartnerTransientMessageNotification(data);
        } else if (data.type === 'activity_updated') {
            this._handlePartnerActivityUpdateNotification(data);
        } else if (data.type === 'mail_failure') {
            this._handlePartnerMailFailureNotification(data);
        } else if (data.type === 'user_connection') {
            this._handlePartnerUserConnectionNotification(data);
        } else if (data.info === 'channel_seen') {
            this._handlePartnerChannnelSeenNotification(data);
        } else if (data.type === 'simple_notification') {
            var title = _.escape(data.title), message = _.escape(data.message);
            data.warning ? this.do_warn(title, message, data.sticky) : this.do_notify(title, message, data.sticky);
        } else if (data.info === 'channel_minimize') {
            this._handlePartnerChannelMinimizeNotification(data);
        } else {
            this._handlePartnerChannelNotification(data);
        }
    },
    /**
     * On toggling on or off the star status of one or several messages.
     * As the information is stored server-side, the web client must adapt
     * itself from server's data on the messages.
     *
     * @private
     * @param {Object} data
     * @param {integer[]} data.message_ids IDs of messages that have a change
     *   of their starred status.
     * @param {boolean} data.starred states whether the messages with id in
     *   `data.message_ids` have become either starred or unstarred
     */
    _handlePartnerToggleStarNotification: function (data) {
        var self = this;
        var starred = this.getMailbox('starred');
        _.each(data.message_ids, function (messageID) {
            var message = _.find(self._messages, function (msg) {
                return msg.getID() === messageID;
            });
            if (message) {
                message.setStarred(data.starred);
                if (!message.isStarred()) {
                    self._removeMessageFromThread('mailbox_starred', message);
                } else {
                    self._addMessageToThreads(message, []);
                    var channelStarred = self.getMailbox('starred');
                    channelStarred.invalidateCaches();
                }
                self._mailBus.trigger('update_message', message);
            }
        });

        if (data.starred) {
            // increase starred counter if message is marked as star
            starred.incrementMailboxCounter(data.message_ids.length);
        } else {
            // decrease starred counter if message is remove from starred
            // if unstar_all then it will set to 0.
            starred.decrementMailboxCounter(data.message_ids.length);
        }

        this._mailBus.trigger('update_starred', starred.getMailboxCounter());
    },
    /**
     * On receiving a transient message, i.e. a message which does not come from
     * a member of the channel. Usually a log message, such as one generated
     * from a command with ('/').
     *
     * @private
     * @param {Object} data
     */
    _handlePartnerTransientMessageNotification: function (data) {
        var lastMessage = _.last(this._messages);
        data.id = (lastMessage ? lastMessage.getID() : 0) + 0.01;
        data.author_id = this.getOdoobotID();
        this.addMessage(data);
    },
    /**
     * On receiving a unsubscribe from channel notification, confirm
     * unsubscription from channel and adapt screen accordingly.
     *
     * @private
     * @param {Object} data
     * @param {Object} data.id ID of the unsubscribed channel
     */
    _handlePartnerUnsubscribeNotification: function (data) {
        var channel = this.getChannel(data.id);
        if (channel) {
            var message;
            if (_.contains(['public', 'private'], channel.getType())) {
                message = _.str.sprintf(
                    _t("You unsubscribed from <b>%s</b>."),
                    channel.getName()
                );
            } else {
                message = _.str.sprintf(
                    _t("You unpinned your conversation with <b>%s</b>."),
                    channel.getName()
                );
            }
            this._removeChannel(channel);
            this._mailBus.trigger('unsubscribe_from_channel', data.id);
            this.do_notify(_t("Unsubscribed"), message);
        }
    },
     /**
     * Shows a popup to notify a user connection
     *
     * @private
     * @param {Object} data
     * @param {Object[]} data.partner_id id of the connected partner
     * @param {string} data.title title to display on notification
     * @param {Array} data.messages message to display on notification
     */
    _handlePartnerUserConnectionNotification: function (data) {
        var self = this;
        var partnerID = data.partner_id;
        this.call('bus_service', 'sendNotification', data.title, data.message, function ( ){
            self.call('mail_service', 'openDMChatWindowFromBlankThreadWindow', partnerID);
        });
    },
    /**
     * @override
     * @private
     */
    _listenOnBuses: function () {
        this._super.apply(this, arguments);
        this.call('bus_service', 'onNotification', this, this._onNotification);
    },
    /**
     * Update the message notification status of message based on update_message
     *
     * @private
     * @param {Object} data
     * @param {Object[]} data.notifications
     * @param {mail.model.Message} message
     */
    _updateMessageNotificationStatus: function (data, message) {
        _.each(data.notifications, function (notif, id) {
            var partnerName = notif[1];
            var notifStatus = notif[0];
            var res = _.find(message.getCustomerEmailData(), function (entry) {
                return entry[0] === parseInt(id);
            });
            if (res) {
                res[2] = notifStatus;
            } else {
                message.addCustomerEmailData([parseInt(id), partnerName, notifStatus]);
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Notification handlers
     * Sometimes, the web client receives unsubscribe notification and an extra
     * notification on that channel.  This is then followed by an attempt to
     * rejoin the channel that we just left.  The next few lines remove the
     * extra notification to prevent that situation to occur.
     *
     * @private
     * @param {Array} notifs
     */
    _onNotification: function (notifs) {
        var self = this;
        notifs = this._filterNotificationsOnUnsubscribe(notifs);
        _.each(notifs, function (notif) {
            var model = notif[0][1];
            if (model === 'ir.needaction') {
                self._handleNeedactionNotification(notif[1]);
            } else if (model === 'mail.channel') {
                // new message in a channel
                self._handleChannelNotification({
                    channelID: notif[0][2],
                    data: notif[1],
                });
            } else if (model === 'res.partner') {
                self._handlePartnerNotification(notif[1]);
            }
        });
    },
});

return MailManager;

});
