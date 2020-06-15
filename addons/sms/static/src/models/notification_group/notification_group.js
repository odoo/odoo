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
        if (this.notification_type === 'sms') {
            this.env.bus.trigger('do-action', {
                action: 'sms.sms_cancel_action',
                options: {
                    additional_context: {
                        default_model: this.res_model,
                        unread_counter: this.notifications.length,
                    },
                },
            });
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _openDocuments() {
        if (this.notification_type === 'sms') {
            this.env.bus.trigger('do-action', {
                action: {
                    name: this.env._t("SMS Failures"),
                    type: 'ir.actions.act_window',
                    view_mode: 'kanban,list,form',
                    views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                    target: 'current',
                    res_model: this.res_model,
                    domain: [['message_has_sms_error', '=', true]],
                },
            });
        }
        return this._super(...arguments);
    },
});

});
