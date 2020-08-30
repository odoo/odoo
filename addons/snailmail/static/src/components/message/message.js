odoo.define('snailmail/static/src/components/message/message.js', function (require) {
'use strict';

const components = {
    Message: require('mail/static/src/components/message/message.js'),
    SnailmailErrorDialog: require('snailmail/static/src/components/snailmail_error_dialog/snailmail_error_dialog.js'),
    SnailmailNotificationPopover: require('snailmail/static/src/components/snailmail_notification_popover/snailmail_notification_popover.js'),
};

const { patch } = require('web.utils');

const { useState } = owl;

Object.assign(components.Message.components, {
    SnailmailErrorDialog: components.SnailmailErrorDialog,
    SnailmailNotificationPopover: components.SnailmailNotificationPopover,
});

patch(components.Message, 'snailmail/static/src/components/message/message.js', {
    /**
     * @override
     */
    _constructor() {
        this._super(...arguments);
        this.snailmailState = useState({
            // Determine if the error dialog is displayed.
            hasDialog: false,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onClickFailure() {
        if (this.message.message_type === 'snailmail') {
            /**
             * Messages from snailmail are considered to have at most one
             * notification. The failure type of the whole message is considered
             * to be the same as the one from that first notification, and the
             * click action will depend on it.
             */
            switch (this.message.notifications[0].failure_type) {
                case 'sn_credit':
                    // URL only used in this component, not received at init
                    this.env.messaging.fetchSnailmailCreditsUrl();
                    this.snailmailState.hasDialog = true;
                    break;
                case 'sn_error':
                    this.snailmailState.hasDialog = true;
                    break;
                case 'sn_fields':
                    this.message.openMissingFieldsLetterAction();
                    break;
                case 'sn_format':
                    this.message.openFormatLetterAction();
                    break;
                case 'sn_price':
                    this.snailmailState.hasDialog = true;
                    break;
                case 'sn_trial':
                    // URL only used in this component, not received at init
                    this.env.messaging.fetchSnailmailCreditsUrlTrial();
                    this.snailmailState.hasDialog = true;
                    break;
            }
        } else {
            this._super(...arguments);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onDialogClosedSnailmailError() {
        this.snailmailState.hasDialog = false;
    },
});

});
