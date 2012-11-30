
openerp.web_im = function(instance) {

    var USERS_LIMIT = 20;
    var ERROR_DELAY = 5000;

    instance.web.UserMenu.include({
        do_update: function(){
            var self = this;
            this.update_promise.then(function() {
                var im = new instance.web_im.InstantMessaging(self);
                im.appendTo(instance.client.$el);
                var button = new instance.web_im.ImTopButton(this);
                button.on("clicked", im, im.switch_display);
                button.appendTo(instance.webclient.$el.find('.oe_systray'));
            });
            return this._super.apply(this, arguments);
        },
    });

    instance.web_im.ImTopButton = instance.web.Widget.extend({
        template:'ImTopButton',
        events: {
            "click": "clicked",
        },
        clicked: function() {
            this.trigger("clicked");
        },
    });

    instance.web_im.InstantMessaging = instance.web.Widget.extend({
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
            this.last = null;
            this.users = [];
            this.activated = false;
            this.c_manager = new instance.web_im.ConversationManager(this);
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

            new instance.web.Model("im.message").call("activated", [], {context: new instance.web.CompoundContext()}).then(function(activated) {
                if (activated) {
                    self.activated = true;
                    self.poll();
                }
            });
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
            var users = new instance.web.Model("res.users");
            var self = this;
            return this.user_search_dm.add(users.query(["name"])
                    .filter([["name", "ilike", this.get("current_search")]])
                    .limit(USERS_LIMIT).all()).then(function(result) {
                self.$(".oe_im_input").val("");
                _.each(self.users, function(user) {
                    user.destroy();
                });
                self.users = [];
                _.each(result, function(user) {
                    var widget = new instance.web_im.ImUser(self, user);
                    widget.appendTo(self.$(".oe_im_users"));
                    widget.on("activate_user", self, self.activate_user);
                    self.users.push(widget);
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
                if (! this.activated) {
                    this.do_warn("Instant Messaging is not activated on this server.", "");
                    return;
                }
                this.$el.animate({
                    right: 0,
                }, opt);
            }
            this.shown = ! this.shown;
        },
        poll: function() {
            var self = this;
            this.rpc("/im/poll", {
                last: this.last,
                context: instance.web.pyeval.eval('context', {}),
            }, {shadow: true}).then(function(result) {
                self.last = result.last;
                _.each(result.res, function(mes) {
                    self.c_manager.received_message(mes, {"id": mes.from[0]});
                });
                self.poll();
            }, function(unused, e) {
                e.preventDefault();
                setTimeout(_.bind(self.poll, self), ERROR_DELAY);
            });
        },
        activate_user: function(user_rec) {
            this.c_manager.activate_user(user_rec);
        },
    });

    instance.web_im.ImUser = instance.web.Widget.extend({
        "template": "ImUser",
        events: {
            "click": "activate_user",
        },
        init: function(parent, user_rec) {
            this._super(parent);
            this.user_rec = user_rec;
        },
        activate_user: function() {
            this.trigger("activate_user", this.user_rec);
        },
    });

    instance.web_im.ConversationManager = instance.web.Controller.extend({
        init: function(parent) {
            this._super(parent);
            this.set("right_offset", 0);
            this.conversations = [];
            this.users = {};
            this.on("change:right_offset", this, this.calc_positions);
        },
        activate_user: function(user_rec) {
            if (this.users[user_rec.id]) {
                return this.users[user_rec.id];
            }
            var conv = new instance.web_im.Conversation(this, user_rec);
            conv.appendTo(instance.client.$el);
            conv.on("destroyed", this, function() {
                this.conversations = _.without(this.conversations, conv);
                delete this.users[conv.user_rec.id];
            });
            this.conversations.push(conv);
            this.users[user_rec.id] = conv;
            this.calc_positions();
            return conv;
        },
        received_message: function(message, user_rec) {
            var conv = this.activate_user(user_rec);
            conv.received_message(message);
        },
        calc_positions: function() {
            var current = this.get("right_offset");
            _.each(_.range(this.conversations.length), function(i) {
                this.conversations[i].set("right_position", current);
                current += this.conversations[i].$el.outerWidth();
            }, this);
        },
    });

    instance.web_im.Conversation = instance.web.Widget.extend({
        "template": "Conversation",
        events: {
            "keydown input": "send_message",
        },
        init: function(parent, user_rec) {
            this._super(parent);
            this.user_rec = user_rec;
            this.set("right_position", 0);
        },
        start: function() {
            this.on("change:right_position", this, this.calc_pos);
            this.calc_pos();
        },
        calc_pos: function() {
            this.$el.css("right", this.get("right_position"));
        },
        received_message: function(message) {
            this.$(".oe_im_chatview_content").append($("<div>").text("Him: " + message.message));
        },
        send_message: function(e) {
            if(e && e.which !== 13) {
                return;
            }
            var mes = this.$("input").val();
            this.$("input").val("");
            this.$(".oe_im_chatview_content").append($("<div>").text("Me: " + mes));
            var model = new instance.web.Model("im.message");
            model.call("post", [mes, this.user_rec.id], {context: new instance.web.CompoundContext()});
        },
        destroy: function() {
            this.trigger("destroyed");
            return this._super();
        },
    });

}