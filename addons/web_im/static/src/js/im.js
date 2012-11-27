
openerp.web_im = function(instance) {

    instance.web.UserMenu.include({
        do_update: function(){
            var self = this;
            this.update_promise.then(function() {
                var im = new instance.web_im.InstantMessaging(self);
                im.appendTo(instance.client.$el);
                var button = new instance.web.ImTopButton(this);
                button.on("clicked", im, im.switch_display);
                button.appendTo(instance.webclient.$el.find('.oe_systray'));
            });
            return this._super.apply(this, arguments);
        },
    });

    instance.web.ImTopButton = instance.web.Widget.extend({
        template:'ImTopButton',
        events: {
            "click button": "clicked",
        },
        clicked: function() {
            this.trigger("clicked");
        },
    });

    instance.web_im.InstantMessaging = instance.web.Widget.extend({
        template: "InstantMessaging",
        events: {
            "keydown .oe_im_input": "search_users",
        },
        init: function(parent) {
            this._super(parent);
            this.shown = false;
            this.set("right_offset", 0);
            this.last = null;
            this.users = [];
        },
        start: function() {
            this.$el.css("right", -this.$el.outerWidth());
            $(window).scroll(_.bind(this.calc_box, this));
            $(window).resize(_.bind(this.calc_box, this));
            this.calc_box();

            this.poll();
            this.search_users();
        },
        calc_box: function() {
            var $topbar = instance.client.$(".oe_topbar");
            var top = $topbar.offset().top + $topbar.height();
            top = Math.max(top - $(window).scrollTop(), 0);
            this.$el.css("top", top);
            this.$el.css("bottom", 0);
        },
        search_users: function(e) {
            if(e && e.which !== 13) {
                return;
            }
            var users = new instance.web.Model("res.users");
            var self = this;
            return users.query(["name"]).filter([["name", "ilike", this.$(".oe_im_input").val()]]).limit(20).all().then(function(result) {
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
        send_message: function(user_rec, mes) {
            var model = new instance.web.Model("im.message");
            model.call("post", [mes], {context: new instance.web.CompoundContext()});
        },
        switch_display: function() {
            var fct =  _.bind(function() {
                this.set("right_offset", $(window).width() - this.$el.offset().left);
            }, this);
            var opt = {
                step: fct,
                complete: fct,
            };
            if (this.shown) {
                this.$el.animate({
                    right: -this.$el.outerWidth(),
                }, opt);
            } else {
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
                context: new instance.web.CompoundContext()
            }, {shadow: true}).then(function(result) {
                self.last = result.last;
                _.each(result.res, function(mes) {
                    $("<div>").text(mes).appendTo(self.$(".oe_im_content"));
                });
                self.poll();
            }, function(unused, e) {
                e.preventDefault();
                setTimeout(_.bind(self.poll, self), 5000);
            });
        },
        activate_user: function(user_rec) {
            // shitty, to replace
            var conv = new instance.web_im.Conversation(this, this, user_rec);
            conv.appendTo(this.$el);
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

    instance.web_im.Conversation = instance.web.Widget.extend({
        "template": "Conversation",
        events: {
            "keydown input": "send_message",
        },
        init: function(parent, im, user_rec) {
            this._super(parent);
            this.im = im;
            this.user_rec = user_rec;
        },
        start: function() {
            this.im.on("change:right_offset", this, this.calc_pos);
            this.calc_pos();
        },
        calc_pos: function() {
            this.$el.css("right", this.im.get("right_offset"));
        },
        send_message: function(e) {
            if(e && e.which !== 13) {
                return;
            }
            var mes = this.$("input").val();
            this.$("input").val("");
            this.im.send_message(this.user_rec, mes);
        },
    });

}