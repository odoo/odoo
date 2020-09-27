odoo.define('mail/static/src/components/notification_list/notification_list.js', function (require) {
'use strict';

const components = {
    NotificationGroup: require('mail/static/src/components/notification_group/notification_group.js'),
    NotificationRequest: require('mail/static/src/components/notification_request/notification_request.js'),
    ThreadNeedactionPreview: require('mail/static/src/components/thread_needaction_preview/thread_needaction_preview.js'),
    ThreadPreview: require('mail/static/src/components/thread_preview/thread_preview.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class NotificationList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.storeProps = useStore((...args) => this._useStoreSelector(...args), {
            compareDepth: {
                // list + notification object created in useStore
                notifications: 2,
            },
        });
    }

    mounted() {
        this._loadPreviews();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Object[]}
     */
    get notifications() {
        const { notifications } = this.storeProps;
        return notifications;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Load previews of given thread. Basically consists of fetching all missing
     * last messages of each thread.
     *
     * @private
     */
    async _loadPreviews() {
        const threads = this.notifications
            .filter(notification => notification.thread && notification.thread.exists())
            .map(notification => notification.thread);
        this.env.models['mail.thread'].loadPreviews(threads);
    }

    /**
     * @private
     * @param {Object} props
     */
    _useStoreSelector(props) {
        const threads = this._useStoreSelectorThreads(props);
        let threadNeedactionNotifications = [];
        if (props.filter === 'all') {
            // threads with needactions
            threadNeedactionNotifications = this.env.models['mail.thread']
                .all(t => t.model !== 'mail.box' && t.needactionMessages.length > 0)
                .sort((t1, t2) => {
                    if (t1.needactionMessages.length > 0 && t2.needactionMessages.length === 0) {
                        return -1;
                    }
                    if (t1.needactionMessages.length === 0 && t2.needactionMessages.length > 0) {
                        return 1;
                    }
                    if (t1.lastNeedactionMessage && t2.lastNeedactionMessage) {
                        return t1.lastNeedactionMessage.date.isBefore(t2.lastNeedactionMessage.date) ? 1 : -1;
                    }
                    if (t1.lastNeedactionMessage) {
                        return -1;
                    }
                    if (t2.lastNeedactionMessage) {
                        return 1;
                    }
                    return t1.id < t2.id ? -1 : 1;
                })
                .map(thread => {
                    return {
                        thread,
                        type: 'thread_needaction',
                        uniqueId: thread.localId + '_needaction',
                    };
                });
        }
        // thread notifications
        const threadNotifications = threads
            .sort((t1, t2) => {
                if (t1.localMessageUnreadCounter > 0 && t2.localMessageUnreadCounter === 0) {
                    return -1;
                }
                if (t1.localMessageUnreadCounter === 0 && t2.localMessageUnreadCounter > 0) {
                    return 1;
                }
                if (t1.lastMessage && t2.lastMessage) {
                    return t1.lastMessage.date.isBefore(t2.lastMessage.date) ? 1 : -1;
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
                    thread,
                    type: 'thread',
                    uniqueId: thread.localId,
                };
            });
        let notifications = threadNeedactionNotifications.concat(threadNotifications);
        if (props.filter === 'all') {
            const notificationGroups = this.env.messaging.notificationGroupManager.groups;
            notifications = Object.values(notificationGroups)
                .sort((group1, group2) =>
                    group1.date.isAfter(group2.date) ? -1 : 1
                ).map(notificationGroup => {
                    return {
                        notificationGroup,
                        uniqueId: notificationGroup.localId,
                    };
                }).concat(notifications);
        }
        // native notification request
        if (props.filter === 'all' && this.env.messaging.isNotificationPermissionDefault()) {
            notifications.unshift({
                type: 'odoobotRequest',
                uniqueId: 'odoobotRequest',
            });
        }
        return {
            isDeviceMobile: this.env.messaging.device.isMobile,
            notifications,
        };
    }

    /**
     * @private
     * @param {Object} props
     * @throws {Error} in case `props.filter` is not supported
     * @returns {mail.thread[]}
     */
    _useStoreSelectorThreads(props) {
        if (props.filter === 'mailbox') {
            return this.env.models['mail.thread']
                .all(thread => thread.isPinned && thread.model === 'mail.box')
                .sort((mailbox1, mailbox2) => {
                    if (mailbox1 === this.env.messaging.inbox) {
                        return -1;
                    }
                    if (mailbox2 === this.env.messaging.inbox) {
                        return 1;
                    }
                    if (mailbox1 === this.env.messaging.starred) {
                        return -1;
                    }
                    if (mailbox2 === this.env.messaging.starred) {
                        return 1;
                    }
                    const mailbox1Name = mailbox1.displayName;
                    const mailbox2Name = mailbox2.displayName;
                    mailbox1Name < mailbox2Name ? -1 : 1;
                });
        } else if (props.filter === 'channel') {
            return this.env.models['mail.thread']
                .all(thread =>
                    thread.channel_type === 'channel' &&
                    thread.isPinned &&
                    thread.model === 'mail.channel'
                )
                .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
        } else if (props.filter === 'chat') {
            return this.env.models['mail.thread']
                .all(thread =>
                    thread.isChatChannel &&
                    thread.isPinned &&
                    thread.model === 'mail.channel'
                )
                .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
        } else if (props.filter === 'all') {
            // "All" filter is for channels and chats
            return this.env.models['mail.thread']
                .all(thread => thread.isPinned && thread.model === 'mail.channel')
                .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
        } else {
            throw new Error(`Unsupported filter ${props.filter}`);
        }
    }

}

Object.assign(NotificationList, {
    _allowedFilters: ['all', 'mailbox', 'channel', 'chat'],
    components,
    defaultProps: {
        filter: 'all',
    },
    props: {
        filter: {
            type: String,
            validate: prop => NotificationList._allowedFilters.includes(prop),
        },
    },
    template: 'mail.NotificationList',
});

return NotificationList;

});
