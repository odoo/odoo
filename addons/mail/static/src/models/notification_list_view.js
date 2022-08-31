/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'NotificationListView',
    identifyingMode: 'xor',
    lifecycleHooks: {
        _created() {
            this._loadPreviews();
        },
    },
    recordMethods: {
        /**
         * @private
         * @returns {Object[]}
         */
        _computeChannelPreviewViews() {
            return this.filteredChannels
                .sort((c1, c2) => {
                    if (c1.localMessageUnreadCounter > 0 && c2.localMessageUnreadCounter === 0) {
                        return -1;
                    }
                    if (c1.localMessageUnreadCounter === 0 && c2.localMessageUnreadCounter > 0) {
                        return 1;
                    }
                    if (c1.thread.lastMessage && c2.thread.lastMessage) {
                        return c1.thread.lastMessage.id < c2.thread.lastMessage.id ? 1 : -1;
                    }
                    if (c1.thread.lastMessage) {
                        return -1;
                    }
                    if (c2.thread.lastMessage) {
                        return 1;
                    }
                    return c1.id < c2.id ? -1 : 1;
                })
                .map(channel => ({ channel }));
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeFilter() {
            if (this.discussOwner) {
                return this.discussOwner.activeMobileNavbarTabId;
            }
            if (this.messagingMenuOwner) {
                return this.messagingMenuOwner.activeTabId;
            }
            return clear();
        },
        /**
         * @private
         * @returns {Channel[]|FieldCommand}
         */
        _computeFilteredChannels() {
            switch (this.filter) {
                case 'channel': {
                    return this.messaging.models['Channel']
                        .all(channel =>
                            channel.channel_type === 'channel' &&
                            channel.thread.isPinned
                        )
                        .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
                }
                case 'chat': {
                    return this.messaging.models['Channel']
                        .all(channel =>
                            channel.thread.isChatChannel &&
                            channel.thread.isPinned
                        )
                        .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
                }
                case 'all': {
                    // "All" filter is for channels and chats
                    return this.messaging.models['Channel']
                        .all(channel => channel.thread.isPinned)
                        .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
                }
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNotificationGroupViews() {
            if (this.filter !== 'all') {
                return clear();
            }
            return this.models['NotificationGroup']
                .all()
                .sort((group1, group2) => group1.sequence - group2.sequence)
                .map(notificationGroup => ({ notificationGroup }));
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNotificationRequestView() {
            return (this.filter === 'all' && this.messaging.isNotificationPermissionDefault) ? {} : clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNotificationViews() {
            const notifications = [];
            if (this.notificationRequestView) {
                notifications.push(this.notificationRequestView);
            }
            notifications.push(...this.notificationGroupViews);
            notifications.push(...this.threadNeedactionPreviewViews);
            notifications.push(...this.channelPreviewViews);
            return notifications;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThreadNeedactionPreviewViews() {
            if (this.filter !== 'all') {
                return clear();
            }
            return this.messaging.models['Thread']
                .all(t => !t.mailbox && t.needactionMessagesAsOriginThread.length > 0)
                .sort((t1, t2) => {
                    if (t1.needactionMessagesAsOriginThread.length > 0 && t2.needactionMessagesAsOriginThread.length === 0) {
                        return -1;
                    }
                    if (t1.needactionMessagesAsOriginThread.length === 0 && t2.needactionMessagesAsOriginThread.length > 0) {
                        return 1;
                    }
                    if (t1.lastNeedactionMessageAsOriginThread && t2.lastNeedactionMessageAsOriginThread) {
                        return t1.lastNeedactionMessageAsOriginThread.id < t2.lastNeedactionMessageAsOriginThread.id ? 1 : -1;
                    }
                    if (t1.lastNeedactionMessageAsOriginThread) {
                        return -1;
                    }
                    if (t2.lastNeedactionMessageAsOriginThread) {
                        return 1;
                    }
                    return t1.id < t2.id ? -1 : 1;
                })
                .map(thread => ({ thread }));
        },
        /**
         * Load previews of given thread. Basically consists of fetching all missing
         * last messages of each thread.
         *
         * @private
         */
        async _loadPreviews() {
            const threads = this.channelPreviewViews
                .map(channelPreviewView => channelPreviewView.thread);
            this.messaging.models['Thread'].loadPreviews(threads);
        },
    },
    fields: {
        channelPreviewViews: many('ChannelPreviewView', {
            compute: '_computeChannelPreviewViews',
            inverse: 'notificationListViewOwner',
            isCausal: true,
        }),
        discussOwner: one('Discuss', {
            identifying: true,
            inverse: 'notificationListView',
        }),
        filter: attr({
            compute: '_computeFilter',
        }),
        filteredChannels: many('Channel', {
            compute: '_computeFilteredChannels',
        }),
        messagingMenuOwner: one('MessagingMenu', {
            identifying: true,
            inverse: 'notificationListView',
        }),
        notificationGroupViews: many('NotificationGroupView', {
            compute: '_computeNotificationGroupViews',
            inverse: 'notificationListViewOwner',
            isCausal: true,
        }),
        notificationRequestView: one('NotificationRequestView', {
            compute: '_computeNotificationRequestView',
            inverse: 'notificationListViewOwner',
            isCausal: true,
        }),
        notificationViews: many('Record', {
            compute: '_computeNotificationViews',
            isCausal: true,
        }),
        threadNeedactionPreviewViews: many('ThreadNeedactionPreviewView', {
            compute: '_computeThreadNeedactionPreviewViews',
            inverse: 'notificationListViewOwner',
            isCausal: true,
        }),
    },
});
