odoo.define('im_livechat.Discuss', function (require) {
"use strict";

var Discuss = require('mail.Discuss');

Discuss.include({
    /**
     * Override to sort livechats by last message's date
     *
     * @override
     * @private
     * @param {mail.model.Channel[]} channels
     * @returns {mail.model.Channel[]}
     */
    _sortChannels: function (channels) {
        var partition = _.partition(channels, function (channel) {
            return channel.getType() === 'livechat';
        });
        partition[0].sort(function (c1, c2) {
            if (!c1.hasMessages()) {
                return -1;
            } else if (!c2.hasMessages()) {
                return 1;
            }
            return c2.getLastMessage().getDate().diff(c1.getLastMessage().getDate());
        });
        channels = partition[0].concat(partition[1]);
        return this._super(channels);
    },
});

});
