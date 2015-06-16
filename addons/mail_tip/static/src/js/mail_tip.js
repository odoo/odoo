odoo.define('mail_tip.mail_tip', function (require) {
"use strict";

var mail = require('mail.mail');
var core = require('web.core');

mail.MailThread.include({
    message_fetch: function() {
        var self = this;
        return this._super.apply(this, arguments).done(function() {
            // event has to be triggered on form view
            self.parent_view.trigger('chatter_messages_displayed');
        });
    }
});

});
