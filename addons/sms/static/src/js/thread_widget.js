odoo.define('sms.widget.Thread', function (require) {
"use strict";

var ThreadWidget = require('mail.widget.Thread');

ThreadWidget.include({
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onClickMessageNotificationError(ev) {
        if ($(ev.currentTarget).data('message-type') === 'sms') {
            var messageID = $(ev.currentTarget).data('message-id');
            this.do_action('sms.sms_resend_action', {
                additional_context: {
                    default_mail_message_id: messageID
                }
            });
        } else {
            this._super(...arguments);
        }
    },
});
});
