
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
            return im_common.connection.rpc('/web/proxy/load', {path: '/im_livechat/static/ext/static/js/livechat.xml'}).then(function(xml) {
                openerp.qweb.add_template(xml);
            });
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

    im_common.ChatButton = openerp.Widget.extend({
        className: "openerp_style oe_chat_button",
        events: {
            "click": "click"
        },
        init: function(parent, channel, options) {
            this._super(parent);
            this.channel = channel;
            this.options = options;
            this.text = options.buttonText;
        },
        start: function() {
            this.$().append(openerp.qweb.render("chatButton", {widget: this}));
        },
        click: function() {
            if (! this.manager) {
                this.manager = new im_common.ConversationManager(null);
                this.activated_def = this.manager.start_polling();
            }
            var def = $.Deferred();
            $.when(this.activated_def).then(function() {
                def.resolve();
            }, function() {
                def.reject();
            });
            setTimeout(function() {
                def.reject();
            }, 5000);
            def.then(_.bind(this.chat, this), function() {
                im_common.notification(_t("It seems the connection to the server is encountering problems, please try again later."));
            });
        },
        chat: function() {
            var self = this;
            if (this.manager.conversations.length > 0)
                return;
            im_common.connection.model("im_livechat.channel").call("get_available_user", [this.channel]).then(function(user_id) {
                if (! user_id) {
                    im_common.notification(_t("None of our collaborators seems to be available, please try again later."));
                    return;
                }
                self.manager.ensure_users([user_id]).then(function() {
                    var conv = self.manager.activate_user(self.manager.get_user(user_id), true);
                    if (self.options.defaultMessage) {
                        conv.received_message({message: self.options.defaultMessage, 
                            date: openerp.datetime_to_str(new Date())});
                    }
                });
            });
        }
    });

    return livesupport;
});
