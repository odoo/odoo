odoo.define('snailmail/static/src/models/notification_group/notification_group.js', function (require) {
'use strict';

const {
    registerInstancePatchModel,
} = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.notification_group', 'snailmail/static/src/models/notification_group/notification_group.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    openCancelAction() {
        if (this.notification_type === 'snail') {
            this.env.bus.trigger('do-action', {
                action: 'snailmail.snailmail_letter_cancel_action',
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
        if (this.notification_type === 'snail') {
            this.env.bus.trigger('do-action', {
                action: {
                    name: this.env._t("Snailmail Failures"),
                    type: 'ir.actions.act_window',
                    view_mode: 'kanban,list,form',
                    views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                    target: 'current',
                    res_model: this.res_model,
                    domain: [['message_ids.snailmail_error', '=', true]],
                },
            });
        }
        return this._super(...arguments);
    },
});

});
