odoo.define('sms.NotificationManager', function (require) {
"use strict";

var MailManager = require('mail.Manager');
var MailFailure = require('mail.model.MailFailure');

MailManager.include({

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object} data structure depending on the type
     * @param {integer} data.id
     */
    _handlePartnerNotification: function (data) {
        if (data.type === 'sms_update') {
            this._handleSMSUpdateNotification(data);
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Updates message in thread when there's an update in a SMS letter
     *
     * @private
     * @param {Object} datas
     * @param {Object[]} datas.elements list of SMS failure data
     * @param {string} datas.elements[].message_id ID of related message that
     *   has a sms failure.
     */
    _handleSMSUpdateNotification: function (datas) {
        var self = this;
        _.each(datas.elements, function (data) {
            var isNewFailure = data.sms_status === 'error';
            var matchedFailure = _.find(self._mailFailures, function (failure) {
                return failure.getMessageID() === data.message_id;
            });

            if (matchedFailure) {
                var index = _.findIndex(self._mailFailures, matchedFailure);
                if (isNewFailure) {
                    self._mailFailures[index] = new MailFailure(self, data);
                } else {
                    self._mailFailures.splice(index, 1);
                }
            } else if (isNewFailure) {
                self._mailFailures.push(new MailFailure(self, data));
            }
            var message = _.find(self._messages, function (msg) {
                return msg.getID() === data.message_id;
            });
            if (message) {
                message.setSmsStatus(data.sms_id, data.sms_status);
                self._mailBus.trigger('update_message', message);
            }
        });
        this._mailBus.trigger('update_needaction', this.needactionCounter);
    },
});

});
