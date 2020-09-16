odoo.define('mail/static/src/components/notification_group/notification_group.js', function (require) {
'use strict';

const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class NotificationGroup extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
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
     * @returns {mail.notification_group}
     */
    get group() {
        return this.env.models['mail.notification_group'].get(this.props.notificationGroupLocalId);
    }

    /**
     * @returns {string|undefined}
     */
    image() {
        if (this.group.__mfield_notification_type(this) === 'email') {
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
        this.group.openDocuments();
        if (!this.env.messaging.__mfield_device(this).__mfield_isMobile(this)) {
            this.env.messaging.__mfield_messagingMenu(this).close();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMarkAsRead(ev) {
        this.group.openCancelAction();
        if (!this.env.messaging.__mfield_device(this).__mfield_isMobile(this)) {
            this.env.messaging.__mfield_messagingMenu(this).close();
        }
    }

}

Object.assign(NotificationGroup, {
    props: {
        notificationGroupLocalId: String,
    },
    template: 'mail.NotificationGroup',
});

return NotificationGroup;

});
