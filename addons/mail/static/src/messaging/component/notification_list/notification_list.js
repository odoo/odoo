odoo.define('mail.messaging.component.NotificationList', function (require) {
'use strict';

const components = {
    ThreadPreview: require('mail.messaging.component.ThreadPreview'),
};
const useStore = require('mail.messaging.component_hook.useStore');

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
        const { notifications } = this.storeProps;
        const threads = notifications
            .filter(notification => notification.thread)
            .map(notification => this.env.entities.Thread.get(notification.thread));
        this.env.entities.Thread.loadPreviews(threads);
    }

    /**
     * @private
     * @param {Object} props
     */
    _useStoreSelector(props) {
        const threads = this._useStoreSelectorThreads(props);
        const notifications = threads
            .sort((t1, t2) => {
                if (t1.message_unread_counter > 0 && t2.message_unread_counter === 0) {
                    return -1;
                }
                if (t1.message_unread_counter === 0 && t2.message_unread_counter > 0) {
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
                return 0;
            })
            .map(thread => {
                return {
                    thread: thread,
                    type: 'thread',
                    uniqueId: thread.localId,
                };
            });
        return {
            isDeviceMobile: this.env.messaging.device.isMobile,
            notifications,
        };
    }

    /**
     * @private
     * @param {Object} props
     * @throws {Error} in case `props.filter` is not supported
     * @returns {mail.messaging.entity.Thread[]}
     */
    _useStoreSelectorThreads(props) {
        if (props.filter === 'mailbox') {
            return this.env.entities.Thread.allOrderedAndPinnedMailboxes;
        } else if (props.filter === 'channel') {
            return this.env.entities.Thread.allOrderedAndPinnedMultiUserChannels;
        } else if (props.filter === 'chat') {
            return this.env.entities.Thread.allOrderedAndPinnedChats;
        } else if (props.filter === 'all') {
            // "All" filter is for channels and chats
            return this.env.entities.Thread.allOrderedAndPinnedChannels;
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
    template: 'mail.messaging.component.NotificationList',
});

return NotificationList;

});
