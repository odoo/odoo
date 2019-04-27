odoo.define('mail.model.TwoUserChannel', function (require) {
"use strict";

var Channel = require('mail.model.Channel');

var TwoUserChannel = Channel.extend({
    /**
     * @override
     * @returns {boolean}
     */
    isTwoUserThread: function () {
        return true;
    },
    /**
     * Unpin from two-user thread
     *
     * @override
     * @returns {Promise} resolve when unsubscribed
     */
    unsubscribe: function () {
        return this._rpc({
            model: 'mail.channel',
            method: 'channel_pin',
            args: [this.getUUID(), false],
        });
    },

});

return TwoUserChannel;

});
