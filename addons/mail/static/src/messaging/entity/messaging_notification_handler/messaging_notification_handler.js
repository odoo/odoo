odoo.define('mail.messaging.entity.MessagingNotificationHandler', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers

function MessagingNotificationHandlerFactory({ Entity }) {

    class MessagingNotificationHandler extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Fetch messaging data initially to populate the store specifically for
         * the current users. This includes pinned channels for instance.
         */
        start() {
            this.env.call('bus_service', 'onNotification', null, notifs => this._handleNotifications(notifs));
            this.env.call('bus_service', 'startPolling');
        }

        /**
         * Called when messaging becomes stopped.
         */
        stop() {
            this.env.call('bus_service', 'off', 'notification');
            this.env.call('bus_service', 'stopPolling');
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {Object[]} notifications
         * @returns {Object[]}
         */
        _filterNotificationsOnUnsubscribe(notifications) {
            const unsubscribedNotif = notifications.find(notif =>
                notif[1].info === 'unsubscribe');
            if (unsubscribedNotif) {
                notifications = notifications.filter(notif =>
                    notif[0][1] !== 'mail.channel' ||
                    notif[0][2] !== unsubscribedNotif[1].id
                );
            }
            return notifications;
        }

        /**
         * @private
         * @param {Object[]} notifications
         * @param {Array} notifications[i][0] meta-data of the notification.
         * @param {string} notifications[i][0][0] name of database this
         *   notification comes from.
         * @param {string} notifications[i][0][1] type of notification.
         * @param {integer} notifications[i][0][2] usually id of related type
         *   of notification. For instance, with `mail.channel`, this is the id
         *   of the channel.
         * @param {Object} notifications[i][1] payload of the notification
         */
        async _handleNotifications(notifications) {
            const filteredNotifications = this._filterNotificationsOnUnsubscribe(notifications);
            const proms = filteredNotifications.map(notification => {
                const [[, model, id], data] = notification;
                switch (model) {
                    case 'ir.needaction':
                        return this._handleNotificationNeedaction(data);
                    case 'mail.channel':
                        return this._handleNotificationChannel(Object.assign({
                            channelId: id,
                        }, data));
                    case 'res.partner':
                        return this._handleNotificationPartner(Object.assign({}, data));
                    default:
                        console.warn(`[messaging store] Unhandled notification "${model}"`);
                        return;
                }
            });
            await Promise.all(proms);
        }

        /**
         * @private
         * @param {Object} data
         * @param {integer} data.channelId
         * @param {string} [data.info]
         * @param {integer} [data.last_message_id]
         * @param {integer} [data.partner_id]
         */
        async _handleNotificationChannel(data) {
            const {
                channelId,
                info,
                last_message_id,
                partner_id,
            } = data;
            switch (info) {
                case 'channel_fetched':
                    return; // disabled seen notification feature
                case 'channel_seen':
                    return this._handleNotificationChannelSeen({
                        channelId,
                        last_message_id,
                        partner_id,
                    });
                case 'typing_status':
                    /**
                     * data.is_typing
                     * data.is_website_user
                     * data.partner_id
                     */
                    return; // disabled typing status notification feature
                default:
                    return this._handleNotificationChannelMessage(data);
            }
        }

        /**
         * @private
         * @param {Object} param0
         * @param {integer} param0.channelId
         * @param {...Object} param0.data
         * @param {Array} [param0.data.author_id]
         * @param {integer} param0.data.author_id[0]
         * @param {integer[]} param0.data.channel_ids
         */
        async _handleNotificationChannelMessage(param0) {
            const channelId = param0.channelId;
            const data = Object.assign({}, param0);
            delete data.channelId;
            const {
                author_id: [authorPartnerId] = [],
                channel_ids,
            } = data;
            if (channel_ids.length === 1) {
                await this.env.entities.Thread.joinChannel(channel_ids[0]);
            }
            let message = this.env.entities.Message.fromId(data.id);
            if (message) {
                const oldMessageModerationStatus = message.moderation_status;
                const oldMessageWasModeratedByUser = message.isModeratedByUser;
                message.update(data);
                if (
                    oldMessageModerationStatus === 'pending_moderation' &&
                    message.moderation_status !== 'pending_moderation' &&
                    oldMessageWasModeratedByUser
                ) {
                    const moderation = this.env.entities.Thread.mailboxFromId('moderation');
                    moderation.update({ counter: moderation.counter - 1 });
                }
                return;
            }
            message = this.env.entities.Message.create(data);
            for (const thread of message.allThreads) {
                if (thread.model === 'mail.channel') {
                    const mainThreadCache = thread.mainCache;
                    mainThreadCache.link({ messages: message });
                }
            }
            const currentPartner = this.env.messaging.currentPartner;
            if (authorPartnerId === currentPartner.id) {
                return;
            }
            const channel = this.env.entities.Thread.channelFromId(channelId);
            const isOdooFocused = this.env.call('bus_service', 'isOdooFocused');
            if (!isOdooFocused) {
                this._notifyNewChannelMessageWhileOutOfFocus({ channel, message });
            }
            channel.update({ message_unread_counter: channel.message_unread_counter + 1 });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {integer} param0.channelId
         * @param {integer} param0.last_message_id
         * @param {integer} param0.partner_id
         */
        async _handleNotificationChannelSeen({
            channelId,
            last_message_id,
            partner_id,
        }) {
            const currentPartner = this.env.messaging.currentPartner;
            if (currentPartner.id !== partner_id) {
                return;
            }
            const channel = this.env.entities.Thread.channelFromId(channelId);
            channel.update({
                message_unread_counter: 0,
                seen_message_id: last_message_id,
            });
        }

        /**
         * @private
         * @param {Object} data
         */
        _handleNotificationNeedaction(data) {
            const message = this.env.entities.Message.insert(data);
            const inboxMailbox = this.env.entities.Thread.mailboxFromId('inbox');
            inboxMailbox.update({ counter: inboxMailbox.counter + 1 });
            for (const thread of message.allThreads) {
                if (
                    thread.channel_type === 'channel' &&
                    message.allThreads.includes(inboxMailbox)
                ) {
                    thread.update({
                        message_needaction_counter: thread.message_needaction_counter + 1,
                    });
                }
                const mainThreadCache = thread.mainCache;
                mainThreadCache.link({ messages: message });
            }
        }

        /**
         * @private
         * @param {Object} data
         * @param {string} [data.info]
         * @param {string} [data.type]
         */
        async _handleNotificationPartner(data) {
            const {
                info,
                type,
            } = data;
            if (type === 'activity_updated') {
                /**
                 * data.activity_created
                 * data.activity_deleted
                 */
                console.warn('activity_updated not handled', data);
                return; // disabled
            } else if (type === 'author') {
                return this._handleNotificationPartnerAuthor(data);
            } else if (type === 'deletion') {
                return this._handleNotificationPartnerDeletion(data);
            } else if (type === 'mail_failure') {
                return this._handleNotificationPartnerMailFailure(data.elements);
            } else if (type === 'mark_as_read') {
                return this._handleNotificationPartnerMarkAsRead(data);
            } else if (type === 'moderator') {
                return this._handleNotificationPartnerModerator(data);
            } else if (type === 'toggle_star') {
                return this._handleNotificationPartnerToggleStar(data);
            } else if (info === 'transient_message') {
                return this._handleNotificationPartnerTransientMessage(data);
            } else if (info === 'unsubscribe') {
                return this._handleNotificationPartnerUnsubscribe(data.id);
            } else if (type === 'user_connection') {
                return this._handleNotificationPartnerUserConnection(data);
            } else {
                return this._handleNotificationPartnerChannel(data);
            }
        }

        /**
         * @private
         * @param {Object} data
         * @param {Object} data.message
         */
        _handleNotificationPartnerAuthor(data) {
            this.env.entities.Message.insert(data.message);
        }

        /**
         * @private
         * @param {Object} data
         * @param {string} data.channel_type
         * @param {integer} data.id
         * @param {string} [data.info]
         * @param {boolean} data.is_minimized
         * @param {string} data.name
         * @param {string} data.state
         * @param {string} data.uuid
         */
        _handleNotificationPartnerChannel(data) {
            const {
                channel_type,
                id,
                info,
                is_minimized,
                name,
                state: channelState,
            } = data;
            if (channel_type !== 'channel' || channelState !== 'open') {
                return;
            }
            let channel = this.env.entities.Thread.channelFromId(id);
            if (
                !is_minimized &&
                info !== 'creation' &&
                (
                    !channel ||
                    !channel.members.includes(this.env.messaging.currentPartner)
                )
            ) {
                this.env.do_notify(
                    this.env._t("Invitation"),
                    _.str.sprintf(
                        this.env._t("You have been invited to: %s"),
                        name
                    )
                );
            }
            if (!channel) {
                channel = this.env.entities.Thread.create(
                    Object.assign({}, data, { isPinned: true })
                );
            }
        }

        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} param0.messag_ids
         */
        _handleNotificationPartnerDeletion({ message_ids }) {
            const moderationMailbox = this.env.entities.Thread.mailboxFromId('moderation');
            for (const id of message_ids) {
                const message = this.env.entities.Message.fromId(id);
                if (
                    message &&
                    message.moderation_status === 'pending_moderation' &&
                    message.originThread.isModeratedByUser
                ) {
                    moderationMailbox.update({ counter: moderationMailbox.counter - 1 });
                }
                message.delete();
            }
        }

        /**
         * @private
         * @param {Object[]} elements
         */
        _handleNotificationPartnerMailFailure(elements) {}

        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} [param0.channel_ids=[]]
         * @param {integer[]} [param0.message_ids=[]]
         */
        _handleNotificationPartnerMarkAsRead({ channel_ids = [], message_ids = [] }) {
            const inboxMailbox = this.env.entities.Thread.mailboxFromId('inbox');
            const historyMailbox = this.env.entities.Thread.mailboxFromId('history');
            const mainHistoryThreadCache = historyMailbox.mainCache;
            for (const cache of inboxMailbox.caches) {
                for (const messageId of message_ids) {
                    const message = this.env.entities.Message.fromId(messageId);
                    if (!message) {
                        continue;
                    }
                    cache.unlink({ messages: message });
                    mainHistoryThreadCache.link({ messages: message });
                }
            }
            for (const channel of this.env.entities.Thread.allChannels) {
                channel.update({ message_needaction_counter: 0 });
            }
            inboxMailbox.update({ counter: inboxMailbox.counter - message_ids.length });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {Object} param0.message
         */
        _handleNotificationPartnerModerator({ message: data }) {
            this.env.entities.Message.insert(data);
            const moderationMailbox = this.env.entities.Thread.mailboxFromId('moderation');
            if (moderationMailbox) {
                moderationMailbox.update({ counter: moderationMailbox.counter + 1 });
            }
        }

        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} param0.message_ids
         * @param {boolean} param0.starred
         */
        _handleNotificationPartnerToggleStar({ message_ids = [], starred }) {
            const starredMailbox = this.env.entities.Thread.mailboxFromId('starred');
            for (const messageId of message_ids) {
                const message = this.env.entities.Message.fromId(messageId);
                if (!message) {
                    continue;
                }
                if (starred) {
                    message.link({ threadCaches: starredMailbox.mainCache });
                    starredMailbox.update({ counter: starredMailbox.counter + 1 });
                } else {
                    for (const cache of starredMailbox.caches) {
                        cache.unlink({ messages: message });
                    }
                    starredMailbox.update({ counter: starredMailbox.counter - 1 });
                }
            }
        }

        /**
         * @private
         * @param {Object} data
         */
        _handleNotificationPartnerTransientMessage(data) {
            const messageIds = this.env.entities.Message.all.map(message => message.id);
            const partnerRoot = this.env.messaging.partnerRoot;
            this.env.entities.Message.create(Object.assign({}, data, {
                author_id: [partnerRoot.id, partnerRoot.display_name],
                id: (messageIds ? Math.max(...messageIds) : 0) + 0.01,
                isTransient: true,
            }));
        }

        /**
         * @private
         * @param {integer} channelId
         */
        _handleNotificationPartnerUnsubscribe(channelId) {
            const channel = this.env.entities.Thread.channelFromId(channelId);
            if (!channel) {
                return;
            }
            let message;
            if (channel.directPartner) {
                const directPartner = channel.directPartner;
                message = _.str.sprintf(
                    this.env._t("You unpinned your conversation with <b>%s</b>."),
                    directPartner.name
                );
            } else {
                message = _.str.sprintf(
                    this.env._t("You unsubscribed from <b>%s</b>."),
                    channel.name
                );
            }
            this.env.do_notify(this.env._t("Unsubscribed"), message);
            channel.update({ isPinned: false });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {string} param0.message
         * @param {integer} param0.partner_id
         * @param {string} param0.title
         */
        _handleNotificationPartnerUserConnection({ message, partner_id, title }) {
            this.env.call('bus_service', 'sendNotification', title, message);
            this.env.entities.Thread.createChannel({
                autoselect: true,
                partnerId: partner_id,
                type: 'chat',
            });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {mail.messaging.entity.Thread} param0.channel
         * @param {mail.messaging.entity.Message} param0.message
         */
        _notifyNewChannelMessageWhileOutOfFocus({ channel, message }) {
            const author = message.author;
            const messaging = this.env.messaging;
            let notificationTitle;
            if (!author) {
                notificationTitle = this.env._t("New message");
            } else {
                const authorName = author.nameOrDisplayName;
                if (channel.channel_type === 'channel') {
                    // hack: notification template does not support OWL components,
                    // so we simply use their template to make HTML as if it comes
                    // from component
                    const channelIcon = this.env.qweb.renderToString('mail.messaging.component.ThreadIcon', {
                        env: this.env,
                        thread: channel,
                    });
                    const channelName = _.escape(channel.displayName);
                    const channelNameWithIcon = channelIcon + channelName;
                    notificationTitle = _.str.sprintf(
                        this.env._t("%s from %s"),
                        _.escape(authorName),
                        channelNameWithIcon
                    );
                } else {
                    notificationTitle = _.escape(authorName);
                }
            }
            const notificationContent = message.prettyBody.substr(0, PREVIEW_MSG_MAX_SIZE);
            this.env.call('bus_service', 'sendNotification', notificationTitle, notificationContent);
            messaging.update({
                outOfFocusUnreadMessageCounter: messaging.outOfFocusUnreadMessageCounter + 1,
            });
            const titlePattern = messaging.outOfFocusUnreadMessageCounter === 1
                ? this.env._t("%d Message")
                : this.env._t("%d Messages");
            this.env.trigger_up('set_title_part', {
                part: '_chat',
                title: _.str.sprintf(titlePattern, messaging.outOfFocusUnreadMessageCounter),
            });
        }

    }

    Object.assign(MessagingNotificationHandler, {
        relations: Object.assign({}, Entity.relations, {
            messaging: {
                inverse: 'notificationHandler',
                to: 'Messaging',
                type: 'one2one',
            },
        }),
    });

    return MessagingNotificationHandler;
}

registerNewEntity('MessagingNotificationHandler', MessagingNotificationHandlerFactory);

});
