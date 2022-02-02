/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted } = owl;

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
     * @returns {NotificationListView}
     */
    get notificationListView() {
        return this.messaging && this.messaging.models['NotificationListView'].get(this.props.localId);
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
        this.messaging.models['Thread'].loadPreviews(threads);
    }

}

Object.assign(NotificationList, {
    props: { localId: String },
    template: 'mail.NotificationList',
});

registerMessagingComponent(NotificationList);
