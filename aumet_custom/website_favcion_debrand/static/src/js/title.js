odoo.define('website_favcion_debrand.title', function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var WebClient = require('web.AbstractWebClient');
    var utils = require('web.utils');
    var config = require('web.config');
    var _t = core._t;

    var ajax = require('web.ajax');
    var Dialog = require('web.Dialog');
    var ServiceProviderMixin = require('web.ServiceProviderMixin');
    var KeyboardNavigationMixin = require('web.KeyboardNavigationMixin');
    var CrashManager = require('web.CrashManager').CrashManager; // We can import crash_manager also
    var CrashManagerDialog = require('web.CrashManager').CrashManagerDialog; // We can import crash_manager also
    var ErrorDialog = require('web.CrashManager').ErrorDialog; // We can import crash_manager also
    var WarningDialog = require('web.CrashManager').WarningDialog; // We can import crash_manager also
//    var MailBotService = require('mail_bot.MailBotService').MailBotService; // We can import crash_manager also
    var concurrency = require('web.concurrency');
    var mixins = require('web.mixins');

    var QWeb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;

    let active = true;


    WebClient.include({
        init: function (parent) {
            this._super(parent);
            var self = this;
            this.set('title_part', {"zopenerp": "Aumet Pharmacy"});
        },
    });

});