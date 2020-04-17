odoo.define('snailmail.model.Message', function (require) {
"use strict";

var Message = require('mail.model.Message');

Message.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Cancels the 'snailmail.letter' which has a message_id corresponding to
     * the ID of this message.
     *
     * @returns {Deferred}
     */
    cancelLetter() {
        return this._rpc({
            model: 'mail.message',
            method: 'cancel_letter',
            args: [[this.getID()]],
        });
    },
    /**
     * @override
     */
    getNotificationIcon() {
        if (this.getType() === 'snail') {
            return 'fa fa-paper-plane';
        }
        return this._super(...arguments);
    },
    /**
     * Retries to send the 'snailmail.letter' corresponding to this message
     *
     * @returns {Deferred}
     */
    resendLetter() {
        return this._rpc({
            model: 'mail.message',
            method: 'send_letter',
            args: [[this.getID()]],
        });
    },
});

});
