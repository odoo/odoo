
(function() {
    "use strict";

    var instance = openerp;

    openerp.im = {};

    var USERS_LIMIT = 20;

    var _t = instance.web._t;
    var QWeb = instance.web.qweb;

    instance.web.UserMenu.include({
        do_update: function(){
            var self = this;
            this.update_promise.then(function() {
                im_common.notification = function(message) {
                    instance.client.do_warn(message);
                };
                im_common.connection = openerp.session;

                var im = new instance.im.InstantMessaging(self);
                im.appendTo(instance.client.$el);
                var button = new instance.im.ImTopButton(this);
                button.on("clicked", im, im.switch_display);
                button.appendTo(instance.webclient.$el.find('.oe_systray'));
            });
            return this._super.apply(this, arguments);
        },
    });

    instance.im.ImTopButton = instance.web.Widget.extend({
        template:'ImTopButton',
        events: {
            "click": "clicked",
        },
        clicked: function() {
            this.trigger("clicked");
        },
    });

    instance.im.InstantMessaging = instance.web.Widget.extend({
        template: "InstantMessaging",
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
            this.c_manager = new im_common.ConversationManager(this);
            this.on("change:right_offset", this.c_manager, _.bind(function() {
                this.c_manager.set("right_offset", this.get("right_offset"));
            }, this));
            this.user_search_dm = new instance.web.DropMisordered();
        },
        start: function() {
            this.$el.css("right", -this.$el.outerWidth());
            $(window).scroll(_.bind(this.calc_box, this));
            $(window).resize(_.bind(this.calc_box, this));
            this.calc_box();

            this.on("change:current_search", this, this.search_changed);
            this.search_changed();

            var self = this;

            return this.c_manager.start_polling();
        },
        calc_box: function() {
            var $topbar = instance.client.$(".oe_topbar");
            var top = $topbar.offset().top + $topbar.height();
            top = Math.max(top - $(window).scrollTop(), 0);
            this.$el.css("top", top);
            this.$el.css("bottom", 0);
        },
        input_change: function() {
            this.set("current_search", this.$(".oe_im_searchbox").val());
        },
        search_changed: function(e) {
            var users = new instance.web.Model("im.user");
            var self = this;
            return this.user_search_dm.add(users.call("search_users", [this.get("current_search"), ["name", "user_id", "uuid", "im_status"],
                    USERS_LIMIT], {context:new instance.web.CompoundContext()})).then(function(result) {
                self.c_manager.add_to_user_cache(result);
                self.$(".oe_im_input").val("");
                var old_users = self.users;
                self.users = [];
                _.each(result, function(user) {
                    var widget = new instance.im.UserWidget(self, self.c_manager.get_user(user.id));
                    widget.appendTo(self.$(".oe_im_users"));
                    widget.on("activate_user", self, self.activate_user);
                    self.users.push(widget);
                });
                _.each(old_users, function(user) {
                    user.destroy();
                });
            });
        },
        switch_display: function() {
            var fct =  _.bind(function(place) {
                this.set("right_offset", place + this.$el.outerWidth());
            }, this);
            var opt = {
                step: fct,
            };
            if (this.shown) {
                this.$el.animate({
                    right: -this.$el.outerWidth(),
                }, opt);
            } else {
                if (! this.c_manager.get_activated()) {
                    this.do_warn("Instant Messaging is not activated on this server.", "");
                    return;
                }
                this.$el.animate({
                    right: 0,
                }, opt);
            }
            this.shown = ! this.shown;
        },
        activate_user: function(user) {
            var self = this;
            im_common.connection.model("im.session").call("session_get", [user.get("id"), self.c_manager.me.get("uuid")]).then(function(session) {
                self.c_manager.activate_session(session.id, true);
            });
        },
    });

    instance.im.UserWidget = instance.web.Widget.extend({
        "template": "UserWidget",
        events: {
            "click": "activate_user",
        },
        init: function(parent, user) {
            this._super(parent);
            this.user = user;
            this.user.add_watcher();
        },
        start: function() {
            var change_status = function() {
                this.$(".oe_im_user_online").toggle(this.user.get("im_status") === true);
            };
            this.user.on("change:im_status", this, change_status);
            change_status.call(this);
        },
        activate_user: function() {
            this.trigger("activate_user", this.user);
        },
        destroy: function() {
            this.user.remove_watcher();
            this._super();
        },
    });

})();