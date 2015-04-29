odoo.define('mail_tip.mail_tip', function (require) {
"use strict";

var mail = require('mail.mail');
var core = require('web.core');

mail.MailThread.include({
    message_fetch: function() {
        return this._super.apply(this, arguments).done(function() {
            core.bus.trigger('chatter_messages_fetched');
        });
    }
});    

});

