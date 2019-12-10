odoo.define('snailmail.model.Message', function (require) {
"use strict";

var Message = require('mail.model.Message');

Message.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Cancels the 'snailmail.letter' which has a message_id corresponding to 
     * the ID of this message, then update the status of the message
     * 
     * @returns {Deferred}
     */
    cancelLetter: function () {
        var self = this;
        var mailBus = this.call('mail_service', 'getMailBus');
        return this._rpc({
            model: 'mail.message',
            method: 'cancel_letter',
            args: [[this.getID()]],
        }).then(function () {
            self.setSnailmailStatus('canceled');
            self.setSnailmailError(false);
            mailBus.trigger('update_message', self);
        });
    },
    /**
     * @return {string}
     */
    getSnailmailStatus: function () {
        return this._snailmailStatus.toLowerCase();
    },
    /**
     * Is the sent snailmail letter in error
     * 
     * @return {Boolean}
     */
    getSnailmailError: function () {
        return this._snailmailError;
    },
    /**
     * Retries to send the 'snailmail.letter' corresponding to this message
     * 
     * @returns {Deferred}
     */
    resendLetter: function () {
        return this._rpc({
            model: 'mail.message',
            method: 'send_letter',
            args: [[this.getID()]],
        });
    },
    /**
     * @param {string} snailmailStatus 
     */
    setSnailmailStatus: function (snailmailStatus) {
        this._snailmailStatus = snailmailStatus;
    },
    /**
     * @param {Boolean} snailmailError
     */
    setSnailmailError: function (snailmailError) {
        this._snailmailError = snailmailError;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _setInitialData: function (data){
        this._super.apply(this, arguments);
        this._snailmailStatus = data.snailmail_status;
        this._snailmailError = data.snailmail_error;
    },
});

});
