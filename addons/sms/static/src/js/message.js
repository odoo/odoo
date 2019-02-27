odoo.define('sms.model.Message', function (require) {
"use strict";

var Message = require('mail.model.Message');

Message.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Cancels the 'sms.sms' which has a message_id corresponding to
     * the ID of this message, then update the status of the message
     * 
     * @returns {Deferred}
     */
    cancelSms: function () {
        var self = this;
        var mailBus = this.call('mail_service', 'getMailBus');
        return this._rpc({
            model: 'mail.message',
            method: 'cancel_sms',
            args: [[this.getID()], []],
        }).then(function () {
            self.setSmsStatus('canceled');
            self.setSmsError(false);
            mailBus.trigger('update_message', self);
        });
    },
    /**
     * @return {string}
     */
    getSmsStatus: function () {
        return this._smsStatus.toLowerCase();
    },
    /**
     * Is the sent sms letter in error
     * 
     * @return {Boolean}
     */
    getSmsError: function () {
        return this._smsError;
    },
    /**
     * Retries to send the 'sms.sms' corresponding to this message
     * 
     * @returns {Deferred}
     */
    resendSms: function () {
        return this._rpc({
            model: 'mail.message',
            method: 'send_sms',
            args: [[this.getID()], []],
        });
    },
    /**
     * @param {string} smsStatus 
     */
    setSmsStatus: function (smsStatus) {
        this._smsStatus = smsStatus;
    },
    /**
     * @param {Boolean} smsError
     */
    setSmsError: function (smsError) {
        this._smsError = smsError;
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
        this._smsStatus = data.sms_status;
        this._smsError = data.sms_error;
    },
});

});
