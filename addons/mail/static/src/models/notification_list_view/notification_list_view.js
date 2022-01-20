/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'NotificationListView',
    identifyingFields: [['discussOwner', 'messagingMenuOwner']],
    recordMethods: {
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
         * @returns {FieldCommand}
         */
        _computeFilteredThreads() {
            switch (this.filter) {
                case 'mailbox': {
                    return replace(this.messaging.models['Thread']
                        .all(thread => thread.isPinned && thread.model === 'mail.box')
                        .sort((mailbox1, mailbox2) => {
                            if (mailbox1 === this.messaging.inbox) {
                                return -1;
                            }
                            if (mailbox2 === this.messaging.inbox) {
                                return 1;
                            }
                            if (mailbox1 === this.messaging.starred) {
                                return -1;
                            }
                            if (mailbox2 === this.messaging.starred) {
                                return 1;
                            }
                            const mailbox1Name = mailbox1.displayName;
                            const mailbox2Name = mailbox2.displayName;
                            mailbox1Name < mailbox2Name ? -1 : 1;
                        })
                    );
                }
                case 'channel': {
                    return replace(this.messaging.models['Thread']
                        .all(thread =>
                            thread.channel_type === 'channel' &&
                            thread.isPinned &&
                            thread.model === 'mail.channel'
                        )
                        .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1)
                    );
                }
                case 'chat': {
                    return replace(this.messaging.models['Thread']
                        .all(thread =>
                            thread.isChatChannel &&
                            thread.isPinned &&
                            thread.model === 'mail.channel'
                        )
                        .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1)
                    );
                }
                case 'all': {
                    // "All" filter is for channels and chats
                    return replace(this.messaging.models['Thread']
                        .all(thread => thread.isPinned && thread.model === 'mail.channel')
                        .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1)
                    );
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
            return insertAndReplace(
                this.models['NotificationGroup']
                    .all()
                    .sort((group1, group2) => group1.sequence - group2.sequence)
                    .map(notificationGroup => {
                        return { notificationGroup: replace(notificationGroup) };
                    })
            );
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNotificationRequestView() {
            return (this.filter === 'all' && this.messaging.isNotificationPermissionDefault) ? insertAndReplace() : clear();
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
            notifications.push(...this.threadPreviewViews);
            return replace(notifications);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThreadNeedactionPreviewViews() {
            if (this.filter !== 'all') {
                return clear();
            }
            return insertAndReplace(
                this.messaging.models['Thread']
                    .all(t => t.model !== 'mail.box' && t.needactionMessagesAsOriginThread.length > 0)
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
                    .map(thread => {
                        return { thread: replace(thread) };
                    })
            );
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThreadPreviewViews() {
            return insertAndReplace(
                this.filteredThreads
                    .sort((t1, t2) => {
                        if (t1.localMessageUnreadCounter > 0 && t2.localMessageUnreadCounter === 0) {
                            return -1;
                        }
                        if (t1.localMessageUnreadCounter === 0 && t2.localMessageUnreadCounter > 0) {
                            return 1;
                        }
                        if (t1.lastMessage && t2.lastMessage) {
                            return t1.lastMessage.id < t2.lastMessage.id ? 1 : -1;
                        }
                        if (t1.lastMessage) {
                            return -1;
                        }
                        if (t2.lastMessage) {
                            return 1;
                        }
                        return t1.id < t2.id ? -1 : 1;
                    })
                    .map(thread => {
                        return {
                            thread: replace(thread),
                        };
                    })
            );
        },
    },
    fields: {
        discussOwner: one('Discuss', {
            inverse: 'notificationListView',
            readonly: true,
        }),
        filter: attr({
            compute: '_computeFilter',
        }),
        filteredThreads: many('Thread', {
            compute: '_computeFilteredThreads',
        }),
        messagingMenuOwner: one('MessagingMenu', {
            inverse: 'notificationListView',
            readonly: true,
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
        notificationViews: many('Model', {
            compute: '_computeNotificationViews',
            isCausal: true,
        }),
        threadNeedactionPreviewViews: many('ThreadNeedactionPreviewView', {
            compute: '_computeThreadNeedactionPreviewViews',
            inverse: 'notificationListViewOwner',
            isCausal: true,
        }),
        threadPreviewViews: many('ThreadPreviewView', {
            compute: '_computeThreadPreviewViews',
            inverse: 'notificationListViewOwner',
            isCausal: true,
        }),
    },
});
