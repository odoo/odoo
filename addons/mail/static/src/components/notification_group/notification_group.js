/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, useRef } = owl;

export class NotificationGroup extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        /**
         * Reference of the "mark as read" button. Useful to disable the
         * top-level click handler when clicking on this specific button.
         */
        this._markAsReadRef = useRef('markAsRead');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {NotificationGroupView}
     */
    get notificationGroupView() {
        return this.messaging && this.messaging.models['NotificationGroupView'].get(this.props.localId);
    }

    /**
     * @returns {string|undefined}
     */
    image() {
        if (this.notificationGroupView.notificationGroup.notification_type === 'email') {
            return '/mail/static/src/img/smiley/mailfailure.jpg';
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        const markAsRead = this._markAsReadRef.el;
        if (markAsRead && markAsRead.contains(ev.target)) {
            // handled in `_onClickMarkAsRead`
            return;
        }
        this.notificationGroupView.notificationGroup.openDocuments();
        if (!this.messaging.device.isMobile) {
            this.messaging.messagingMenu.close();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMarkAsRead(ev) {
        this.notificationGroupView.notificationGroup.openCancelAction();
        if (!this.messaging.device.isMobile) {
            this.messaging.messagingMenu.close();
        }
    }

}

Object.assign(NotificationGroup, {
    props: { localId: String },
    template: 'mail.NotificationGroup',
});

registerMessagingComponent(NotificationGroup);
