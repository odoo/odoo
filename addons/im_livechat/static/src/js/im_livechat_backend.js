odoo.define('im_livechat.Discuss', function (require) {
"use strict";

var Discuss = require('mail.Discuss');

Discuss.include({
    _renderSidebar: function (options) {
        // Override to sort livechat channels by last message's date
        var channelPartition = _.partition(options.channels, function (channel) {
            return channel.getType() === 'livechat';
        });
        // livechat channels always have a last message date that is set
        channelPartition[0].sort(function (c1, c2) {
            return c2.getLastMessageDate().diff(c1.getLastMessageDate());
        });
        options.channels = channelPartition[0].concat(channelPartition[1]);
        return this._super(options);
    },
});

});
