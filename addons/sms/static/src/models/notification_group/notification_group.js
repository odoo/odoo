odoo.define('sms/static/src/models/notification_group/notification_group.js', function (require) {
'use strict';

const {
    registerInstancePatchModel,
} = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.notification_group', 'sms/static/src/models/notification_group/notification_group.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    openCancelAction() {
        if (this.__mfield_notification_type(this) !== 'sms') {
            return this._super(...arguments);
        }
        this.env.bus.trigger('do-action', {
            action: 'sms.sms_cancel_action',
            options: {
                additional_context: {
                    default_model: this.__mfield_res_model(this),
                    unread_counter: this.__mfield_notifications(this).length,
                },
            },
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _openDocuments() {
        if (this.__mfield_notification_type(this) !== 'sms') {
            return this._super(...arguments);
        }
        this.env.bus.trigger('do-action', {
            action: {
                name: this.env._t("SMS Failures"),
                type: 'ir.actions.act_window',
                view_mode: 'kanban,list,form',
                views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                target: 'current',
                res_model: this.__mfield_res_model(this),
                domain: [['message_has_sms_error', '=', true]],
            },
        });
        if (this.env.messaging.__mfield_device(this).__mfield_isMobile(this)) {
            // messaging menu has a higher z-index than views so it must
            // be closed to ensure the visibility of the view
            this.__mfield_messagingMenu(this).close();
        }
    },
});

});
