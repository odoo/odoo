
/*
    This file must compile in EcmaScript 3 and work in IE7.
*/

define(["openerp", "im_common", "underscore", "require", "jquery",
        "jquery.achtung"], function(openerp, im_common, _, require, $) {
    /* jshint es3: true */
    "use strict";

    var _t = openerp._t;
    
    var livesupport = {};

    livesupport.main = function(server_url, db, login, password, channel, options) {
        var defs = [];
        options = options || {};
        _.defaults(options, {
            buttonText: _t("Chat with one of our collaborators"),
            inputPlaceholder: _t("How may I help you?"),
            defaultMessage: null,
            auto: false,
            userName: _t("Anonymous")
        });

        im_common.notification = notification;
        im_common.to_url = require.toUrl;
        im_common.defaultInputPlaceholder = options.inputPlaceholder;
        im_common.userName = options.userName;
        defs.push(add_css("im/static/src/css/im_common.css"));
        defs.push(add_css("im_livechat/static/ext/static/lib/jquery-achtung/src/ui.achtung.css"));

        return $.when.apply($, defs).then(function() {
            console.log("starting live support customer app");
            im_common.connection = new openerp.Session(null, server_url, { override_session: true });
            return im_common.connection.session_authenticate(db, login, password);
        }).then(function() {
            return im_common.connection.rpc('/web/proxy/load', {path: '/im/static/src/xml/im_common.xml'}).then(function(xml) {
                openerp.qweb.add_template(xml);
            });
        }).then(function() {
            return im_common.connection.rpc("/im_livechat/available", {db: db, channel: channel}).then(function(activated) {
                if (! activated & ! options.auto)
                    return;
                var button = new im_common.ChatButton(null, channel, options);
                button.appendTo($("body"));
                if (options.auto)
                    button.click();
            });
        });
    };

    var add_css = function(relative_file_name) {
        var css_def = $.Deferred();
        $('<link rel="stylesheet" href="' + im_common.to_url(relative_file_name) + '"></link>')
                .appendTo($("head")).ready(function() {
            css_def.resolve();
        });
        return css_def.promise();
    };

    var notification = function(message) {
        $.achtung({message: message, timeout: 0, showEffects: false, hideEffects: false});
    };

    return livesupport;
});
