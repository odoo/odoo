/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationGroup extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'markAsReadRef', modelName: 'NotificationGroupView', refName: 'markAsRead' });
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
        if (!this.notificationGroupView) {
            return;
        }
        const markAsRead = this.notificationGroupView.markAsReadRef.el;
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
        this.notificationGroupView.notificationGroup.notifyCancel();
    }

}

Object.assign(NotificationGroup, {
    props: { localId: String },
    template: 'mail.NotificationGroup',
});

registerMessagingComponent(NotificationGroup);
