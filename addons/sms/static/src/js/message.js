odoo.define('sms.model.Message', function (require) {
"use strict";

const { _t } = require('web.core');

var Message = require('mail.model.Message');

Message.include({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getNotificationIcon() {
        if (this.getType() === 'sms') {
            return 'fa fa-mobile';
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    getNotificationText() {
        if (this.getType() === 'sms') {
            return _t("SMS");
        }
        return this._super(...arguments);
    },
});
});
