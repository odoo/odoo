/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;
const { onMounted } = owl.hooks;

export class NotificationList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        onMounted(() => this._mounted());
    }

    _mounted() {
        this._loadPreviews();
    }

    /**
     * @returns {mail.notification_list_view}
     */
    get notificationListView() {
        return this.messaging && this.messaging.models['mail.notification_list_view'].get(this.props.localId);
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
        const threads = this.notificationListView.threadPreviewViews
            .map(threadPreviewView => threadPreviewView.thread);
        this.messaging.models['mail.thread'].loadPreviews(threads);
    }

}

Object.assign(NotificationList, {
    props: { localId: String },
    template: 'mail.NotificationList',
});

registerMessagingComponent(NotificationList);
