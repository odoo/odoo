odoo.define('mail/static/src/components/notification_list/notification_list.js', function (require) {
'use strict';

const components = {
    NotificationGroup: require('mail/static/src/components/notification_group/notification_group.js'),
    ThreadNeedactionPreview: require('mail/static/src/components/thread_needaction_preview/thread_needaction_preview.js'),
    ThreadPreview: require('mail/static/src/components/thread_preview/thread_preview.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class NotificationList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
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
                .all(t =>
                    t.__mfield_model(this) !== 'mail.box' &&
                    t.__mfield_needactionMessages(this).length > 0
                )
                .sort((t1, t2) => {
                    if (
                        t1.__mfield_needactionMessages(this).length > 0 &&
                        t2.__mfield_needactionMessages(this).length === 0
                    ) {
                        return -1;
                    }
                    if (
                        t1.__mfield_needactionMessages(this).length === 0 &&
                        t2.__mfield_needactionMessages(this).length > 0
                    ) {
                        return 1;
                    }
                    if (
                        t1.__mfield_lastNeedactionMessage(this) &&
                        t2.__mfield_lastNeedactionMessage(this)
                    ) {
                        return t1.__mfield_lastNeedactionMessage(this).__mfield_date(this).isBefore(t2.__mfield_lastNeedactionMessage(this).__mfield_date(this)) ? 1 : -1;
                    }
                    if (t1.__mfield_lastNeedactionMessage(this)) {
                        return -1;
                    }
                    if (t2.__mfield_lastNeedactionMessage(this)) {
                        return 1;
                    }
                    return t1.__mfield_id(this) < t2.__mfield_id(this) ? -1 : 1;
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
                if (
                    t1.__mfield_localMessageUnreadCounter(this) > 0 &&
                    t2.__mfield_localMessageUnreadCounter(this) === 0
                ) {
                    return -1;
                }
                if (
                    t1.__mfield_localMessageUnreadCounter(this) === 0 &&
                    t2.__mfield_localMessageUnreadCounter(this) > 0
                ) {
                    return 1;
                }
                if (
                    t1.__mfield_lastMessage(this) &&
                    t2.__mfield_lastMessage(this)
                ) {
                    return t1.__mfield_lastMessage(this).__mfield_date(this).isBefore(t2.__mfield_lastMessage(this).__mfield_date(this)) ? 1 : -1;
                }
                if (t1.__mfield_lastMessage(this)) {
                    return -1;
                }
                if (t2.__mfield_lastMessage(this)) {
                    return 1;
                }
                return t1.__mfield_id(this) < t2.__mfield_id(this) ? -1 : 1;
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
            const notificationGroups = this.env.messaging.__mfield_notificationGroupManager(this).__mfield_groups(this);
            notifications = Object.values(notificationGroups)
                .sort((group1, group2) =>
                    group1.__mfield_date(this).isAfter(group2.__mfield_date(this)) ? -1 : 1
                ).map(notificationGroup => {
                    return {
                        notificationGroup,
                        uniqueId: notificationGroup.localId,
                    };
                }).concat(notifications);
        }
        return {
            isDeviceMobile: this.env.messaging.__mfield_device(this).__mfield_isMobile(this),
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
                .all(thread =>
                    thread.__mfield_isPinned(this) &&
                    thread.__mfield_model(this) === 'mail.box'
                )
                .sort((mailbox1, mailbox2) => {
                    if (mailbox1 === this.env.messaging.__mfield_inbox(this)) {
                        return -1;
                    }
                    if (mailbox2 === this.env.messaging.__mfield_inbox(this)) {
                        return 1;
                    }
                    if (mailbox1 === this.env.messaging.__mfield_starred(this)) {
                        return -1;
                    }
                    if (mailbox2 === this.env.messaging.__mfield_starred(this)) {
                        return 1;
                    }
                    const mailbox1Name = mailbox1.__mfield_displayName(this);
                    const mailbox2Name = mailbox2.__mfield_displayName(this);
                    mailbox1Name < mailbox2Name ? -1 : 1;
                });
        } else if (props.filter === 'channel') {
            return this.env.models['mail.thread']
                .all(thread =>
                    thread.__mfield_channel_type(this) === 'channel' &&
                    thread.__mfield_isPinned(this) &&
                    thread.__mfield_model(this) === 'mail.channel'
                )
                .sort((c1, c2) =>
                    c1.__mfield_displayName(this) < c2.__mfield_displayName(this) ? -1 : 1
                );
        } else if (props.filter === 'chat') {
            return this.env.models['mail.thread']
                .all(thread =>
                    thread.__mfield_isChatChannel(this) &&
                    thread.__mfield_isPinned(this) &&
                    thread.__mfield_model(this) === 'mail.channel'
                )
                .sort((c1, c2) =>
                    c1.__mfield_displayName(this) < c2.__mfield_displayName(this) ? -1 : 1
                );
        } else if (props.filter === 'all') {
            // "All" filter is for channels and chats
            return this.env.models['mail.thread']
                .all(thread =>
                    thread.__mfield_isPinned(this) &&
                    thread.__mfield_model(this) === 'mail.channel'
                )
                .sort((c1, c2) =>
                    c1.__mfield_displayName(this) < c2.__mfield_displayName(this) ? -1 : 1
                );
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
