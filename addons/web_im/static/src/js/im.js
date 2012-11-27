
openerp.web_im = function(instance) {

    instance.web.UserMenu.include({
        do_update: function(){
            var self = this;
            this.update_promise.then(function() {
                var im = new instance.web_im.InstantMessaging(self);
                im.appendTo(instance.client.$el);
                var button = new instance.web.ImTopButton(self);
                button.im = im;
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
            this.im.switch_display();
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
                _.each(self.users, function(user) {
                    user.destroy();
                });
                self.users = [];
                _.each(result, function(user) {
                    var widget = new instance.web_im.ImUser(self, user);
                    widget.appendTo(self.$(".oe_im_users"));
                    self.users.push(widget);
                });
            });
        },
        send_message: function() {
            // old code
            var mes = self.$(".oe_im_input").val();
            self.$(".oe_im_input").val("");
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
        }
    });

    instance.web_im.ImUser = instance.web.Widget.extend({
        "template": "ImUser",
        init: function(parent, user_rec) {
            this._super(parent);
            this.user_rec = user_rec;
        },
    });

}