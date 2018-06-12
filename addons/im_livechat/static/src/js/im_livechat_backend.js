odoo.define('im_livechat.Discuss', function (require) {
"use strict";

var Discuss = require('mail.Discuss');

Discuss.include({
    _renderSidebar: function (options) {
        // Override to sort livechat threads by last message's date
        var threadPartition = _.partition(options.threads, function (thread) {
            return thread.getType() === 'livechat';
        });
        threadPartition[0].sort(function (c1, c2) {
            if (!c1.hasMessages()) {
                return -1;
            } else if (!c2.hasMessages()) {
                return 1;
            }
            return c2.getLastMessage().getDate().diff(c1.getLastMessage().getDate());
        });
        options.threads = threadPartition[0].concat(threadPartition[1]);
        return this._super(options);
    },
});

});
