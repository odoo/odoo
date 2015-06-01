odoo.define('im_chat.im_chat', function (require) {
"use strict";

// to do: make this work in website

var bus = require('bus.bus');
var core = require('web.core');
var data = require('web.data');
var Model = require('web.DataModel');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var utils = require('web.utils');
var web_client = require('web.web_client');
var Widget = require('web.Widget');
var im_chat_common = require('im_chat.im_chat_common');

var _t = core._t;
var QWeb = core.qweb;

var USERS_LIMIT = 20;


// ########## CONVERSATION extentions ###############

im_chat_common.ConversationManager.include({
    _message_receive: function(message){
        var self = this;
        var session_id = message.to_id[0];
        var conv = this.sessions[message.to_id[1]];
        if(!conv){
            // fetch the session, and init it with the message
            var def_session = new Model("im_chat.session").call("session_info", [], {"ids" : [session_id]}).then(function(session){
                conv = self.session_apply(session, {'force_open': true});
                conv.message_receive(message);
            });
        }else{
            this._super(message);
        }
    },
});

im_chat_common.Conversation.include({
    // user actions
    prepare_action_menu: function(){
        this._super();
        this._add_action(_t('Shortcuts'), 'im_chat_option_shortcut', 'fa fa-info-circle', this.action_shorcode);
        this._add_action(_t('Quit discussion'), 'im_chat_option_quit', 'fa fa-minus-square', this.action_quit_session);
    },
    action_shorcode: function(e){
        return web_client.action_manager.do_action({
            type: 'ir.actions.act_window',
            name : _t('Shortcode'),
            res_model: 'im_chat.shortcode',
            view_mode: 'tree,form',
            view_type: 'tree',
            views: [[false, 'list'], [false, 'form']],
            target: "new",
            limit: 80,
            flags: {
                action_buttons: true,
                pager: true,
            }
        });
    },
    action_quit_session: function(e){
        var self = this;
        var Session = new Model("im_chat.session");
        return Session.call("quit_user", [this.get("session").uuid]).then(function(res) {
            if(! res){
                self.do_warn(_t("Warning"), _t("You are only 2 identified users. Just close the conversation to leave."));
            }
        });
    },
    // session
    session_update_state: function(state){
        var self = this;
        var args = arguments;
        var super_call = this._super;
        // broadcast the state changing
        return new Model("im_chat.session").call("update_state", [], {"uuid" : this.get("session").uuid, "state" : state}).then(function(){
            super_call.apply(self, args);
        });
    },
    // window title
    window_title_change: function() {
        this.super();
        var title = undefined;
        if (this.get("waiting_messages") !== 0) {
            title = _.str.sprintf(_t("%d Messages"), this.get("waiting_messages"))
        }
        web_client.set_title_part("im_messages", title);
    },
    // TODO : change this way
    add_user: function(user){
        return new Model("im_chat.session").call("add_user", [this.get("session").uuid , user.id]);
    },
});



// ###### BACKEND : contact panel, top menu button #########

var UserWidget = Widget.extend({
    template: "im_chat.UserWidget",
    events: {
        "click": "activate_user",
    },
    init: function(parent, user) {
        this._super(parent);
        this.set("id", user.id);
        this.set("name", user.name);
        this.set("im_status", user.im_status);
        this.set("image_url", user.image_url);
    },
    start: function() {
        this.$el.data("user", {id:this.get("id"), name:this.get("name")});
        this.$el.draggable({helper: "clone"});
        this.on("change:im_status", this, this.update_status);
        this.update_status();
    },
    update_status: function(){
        this.$(".oe_im_user_online").toggle(this.get('im_status') !== 'offline');
        var img_src = (this.get('im_status') == 'away' ? '/im_chat/static/src/img/yellow.png' : '/im_chat/static/src/img/green.png');
        this.$(".oe_im_user_online").attr('src', img_src);
    },
    activate_user: function() {
        this.trigger("user_clicked", this.get("id"));
    },
});

var InstantMessaging = Widget.extend({
    template: "im_chat.InstantMessaging",
    events: {
        "keydown .oe_im_searchbox": "input_change",
        "keyup .oe_im_searchbox": "input_change",
        "change .oe_im_searchbox": "input_change",
    },
    init: function(parent) {
        this._super(parent);
        this.shown = false;
        this.set("right_offset", 0);
        this.set("current_search", "");
        this.users = [];
        this.widgets = {};

        // listen bus
        this.bus = bus.bus;
        this.bus.on("notification", this, this.on_notification);
    },
    start: function() {
        var self = this;
        // ui
        this.conv_manager = new im_chat_common.ConversationManager(this);
        this.on("change:right_offset", this.conv_manager, _.bind(function() {
            this.conv_manager.set("right_offset", this.get("right_offset"));
        }, this));
        $(window).scroll(_.bind(this.position_compute, this));
        $(window).resize(_.bind(this.position_compute, this));
        this.$el.css("right", -this.$el.outerWidth());
        this.position_compute();

        // business
        this.on("change:current_search", this, this.user_search);

        // add a drag & drop listener
        self.conv_manager.on("im_session_activated", self, function(conv) {
            conv.$el.droppable({
                drop: function(event, ui) {
                    conv.add_user(ui.draggable.data("user"));
                }
            });
        });

        // fetch the unread message and the recent activity (e.i. to re-init in case of refreshing page)
        return session.rpc("/im_chat/init", {}).then(function(notifications) {
            _.each(notifications, function(notif){
                self.conv_manager.on_notification(notif, {'load_history': true});
            });
            // start polling
            self.bus.start_polling();
        });
    },
    on_notification: function(notification){
        var channel = notification[0];
        var message = notification[1];
        // user status notification
        if(channel[1] === 'im_chat.presence'){
            if(message.im_status){
                this.user_update_status([message]);
            }
        }
    },
    // ui
    position_compute: function() {
        var top = 48;
        this.$el.css("top", top);
        this.$el.css("bottom", 0);
    },
    input_change: function() {
        this.set("current_search", this.$(".oe_im_searchbox").val());
    },
    switch_display: function() {
        this.position_compute();
        var fct =  _.bind(function(place) {
            this.set("right_offset", place + this.$el.outerWidth());
            this.$(".oe_im_searchbox").focus();
        }, this);
        var opt = {
            step: fct,
        };
        if (this.shown) {
            this.$el.animate({
                right: -this.$el.outerWidth(),
            }, opt);
        } else {
            if (! bus.bus.activated) {
                this.do_warn("Instant Messaging is not activated on this server. Try later.", "");
                return;
            }
            // update the list of user status when show the IM
            this.user_search();
            this.$el.animate({
                right: 0,
            }, opt);
        }
        this.shown = ! this.shown;
    },
    // user methods
    user_search: function(e) {
        var self = this;
        var user_model = new Model("res.users");
        return user_model.call('im_search', [this.get("current_search"), USERS_LIMIT]).then(function(result){
            self.$(".oe_im_input").val("");
            var old_widgets = self.widgets;
            self.widgets = {};
            self.users = [];
            _.each(result, function(user) {
                user.image_url = session.url('/web/image', {model:'res.users', field: 'image_small', id: user.id});
                var widget = new UserWidget(self, user);
                widget.appendTo(self.$(".oe_im_users"));
                widget.on("user_clicked", self, self.user_clicked);
                self.widgets[user.id] = widget;
                self.users.push(user);
            });
            _.each(old_widgets, function(w) {
                w.destroy();
            });
        });
    },
    user_clicked: function(user_id) {
        var self = this;
        var sessions = new Model("im_chat.session");
        return sessions.call("session_get", [user_id]).then(function(session) {
            self.conv_manager.session_apply(session, {'focus': true, 'force_open': true});
        });
    },
    user_update_status: function(users_list){
        var self = this;
        _.each(users_list, function(el) {
            if (self.widgets[el.id]) {
                self.widgets[el.id].set("im_status", el.im_status);
            }
        });
    }
});


var ImTopButton = Widget.extend({
    template:'im_chat.ImTopButton',
    events: {
        "click": "clicked",
    },
    start: function() {
        // Create the InstantMessaging widget and put it in the DOM
        var im = new InstantMessaging(this);
        web_client.im_messaging = im;
        im.appendTo(web_client.$el);
        // Bind the click action to the ImTopButton
        this.on("clicked", im, im.switch_display);
        return this._super();
    },
    clicked: function(ev) {
        ev.preventDefault();
        this.trigger("clicked");
    },
});

// Put the ImTopButton widget in the systray menu if the user is an employee
var Users = new Model('res.users');
Users.call('has_group', ['base.group_user']).done(function(is_employee) {
    if (is_employee) {
        SystrayMenu.Items.push(ImTopButton);
    }
});

return {
    InstantMessaging: InstantMessaging,
    UserWidget: UserWidget,
};

});
