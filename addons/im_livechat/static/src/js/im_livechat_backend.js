odoo.define('im_livechat.chat_discuss', function (require) {
"use strict";

var Discuss = require('mail.chat_discuss');

Discuss.include({
    _renderSidebar: function (options) {
        // Override to sort livechat channels by last message's date
        var channel_partition = _.partition(options.channels, function (channel) {
            return channel.type === 'livechat';
        });
        channel_partition[0].sort(function (c1, c2) {
            return c2.last_message_date.diff(c1.last_message_date);
        });
        options.channels = channel_partition[0].concat(channel_partition[1]);
        return this._super(options);
    },
});

});
