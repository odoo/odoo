odoo.define('mail_bot.MailBotService', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var core = require('web.core');
var session = require('web.session');

var MailBotService =  AbstractService.extend({
    name: 'mailbot_service',
    /**
     * @override
     */
    start: function () {
        var self = this;
        if ('odoobot_initialized' in session && ! session.odoobot_initialized) {
            setTimeout(function () {
                session.odoobot_initialized = true;
                self._rpc({
                    model: 'mail.channel',
                    method: 'init_odoobot',
                });
            }, 2*60*1000);
        }
    },
});
core.serviceRegistry.add('mailbot_service', MailBotService);
return MailBotService;
});
