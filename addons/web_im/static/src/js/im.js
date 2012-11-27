
openerp.web_im = function(instance) {

    instance.web.UserMenu.include({
        do_update: function(){
            var self = this;
            this.update_promise.then(function() {
                var im = new instance.web_im.InstantMessaging(self);
                im.appendTo(instance.client.$el);
                var button = new instance.web.IMTopButton(self);
                button.im = im;
                button.appendTo(instance.webclient.$el.find('.oe_systray'));
            });
            return this._super.apply(this, arguments);
        },
    });

    instance.web.IMTopButton = instance.web.Widget.extend({
        template:'IMTopButton',
        events: {
            "click button": "clicked",
        },
        clicked: function() {
            this.im.switch_display();
        },
    });

    instance.web_im.InstantMessaging = instance.web.Widget.extend({
        template: "InstantMessaging",
        init: function(parent) {
            this._super(parent);
            this.shown = false;
            this.set("right_offset", 0);
        },
        start: function() {
            var self = this;
            this.$el.css("right", -this.$el.outerWidth());
            self.poll();
            self.last = null;
            $(window).scroll(_.bind(this.calc_box, this));
            $(window).resize(_.bind(this.calc_box, this));
            self.calc_box();
            self.$(".oe_im_input").keypress(function(e) {
                if(e.which != 13) {
                    return;
                }
                var mes = self.$(".oe_im_input").val();
                self.$(".oe_im_input").val("");
                var model = new instance.web.Model("im.message");
                model.call("post", [mes], {context: new instance.web.CompoundContext()});
            }).focus();
        },
        calc_box: function() {
            var $topbar = instance.client.$(".oe_topbar");
            var top = $topbar.offset().top + $topbar.height();
            top = Math.max(top - $(window).scrollTop(), 0);
            this.$el.css("top", top);
            this.$el.css("bottom", 0);
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

}