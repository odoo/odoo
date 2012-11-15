
openerp.web_chat = function(instance) {

    instance.web.Menu = instance.web.Menu.extend({
        start: function() {
            new instance.web_chat.Chat(instance.client).appendTo(instance.client.$el);
            return this._super();
        }
    });

    instance.web_chat.Chat = instance.web.Widget.extend({
        template: "Chat",
        start: function() {
            var self = this;
            self.poll();
            self.last = null;
            self.$(".oe_chat_input").keypress(function(e) {
                if(e.which != 13) {
                    return;
                }
                var mes = self.$(".oe_chat_input").val();
                self.$(".oe_chat_input").val("");
                var model = new instance.web.Model("chat.message");
                model.call("post", [mes], {context: new instance.web.CompoundContext()}).then(function() {
                    console.log("pushed message");
                });
            }).focus();
        },
        poll: function() {
            var self = this;
            var model = new instance.web.Model("chat.message");
            model.call("poll", [this.last], {context: new instance.web.CompoundContext()}).then(function(result) {
                console.log("got it", result);
                self.last = result.last;
                _.each(result.res, function(mes) {
                    $("<div>").text(mes).appendTo(self.$(".oe_chat_content"));
                });
                //self.poll();
            }, function(unused, e) {
                e.preventDefault();
                //setTimeout(_.bind(self.poll, self), 5000);
            });
        }
    });

}