
define(["nova", "jquery", "underscore", "oeclient", "require"], function(nova, $, _, oeclient, require) {
    var livesupport = {};

    var templateEngine = new nova.TemplateEngine();
    templateEngine.extendEnvironment({"toUrl": _.bind(require.toUrl, require)});
    var connection;

    livesupport.main = function(server_url, db, login, password) {
        $.ajax({
            url: require.toUrl("./livesupport_templates.js"),
            jsonp: false,
            jsonpCallback: "oe_livesupport_templates_callback",
            dataType: "jsonp",
            cache: true,
        }).then(function(content) {
            return templateEngine.loadFileContent(content);
        }).then(function() {
            console.log("starting client");
            connection = new oeclient.Connection(new oeclient.JsonpRPCConnector(server_url), db, login, password);
            connection.getModel("res.users").search_read([["login", "in", ["demo", "admin"]]]).then(function(result) {
                var admin, demo;
                if (result[0].login === "admin") {
                    admin = result[0];
                    demo = result[1];
                } else {
                    admin = result[1];
                    demo = result[0];
                }
                admin = new livesupport.ImUser(null, admin);
                demo = new livesupport.ImUser(null, demo);
                var manager = new livesupport.ConversationManager(null);
                manager.set_me(admin);
                manager.activate_user(demo);
            });
        });
    };

    var ERROR_DELAY = 5000;

    livesupport.ImUser = nova.Class.$extend({
        __include__: [nova.DynamicProperties],
        __init__: function(parent, user_rec) {
            nova.DynamicProperties.__init__.call(this, parent);
            //user_rec.image_url = instance.session.url('/web/binary/image', {model:'res.users', field: 'image_small', id: user_rec.id});
            this.set(user_rec);
            this.set("watcher_count", 0);
            this.on("change:watcher_count", this, function() {
                if (this.get("watcher_count") === 0)
                    this.destroy();
            });
        },
        destroy: function() {
            this.trigger("destroyed");
            nova.DynamicProperties.destroy.call(this);
        },
        add_watcher: function() {
            this.set("watcher_count", this.get("watcher_count") + 1);
        },
        remove_watcher: function() {
            this.set("watcher_count", this.get("watcher_count") - 1);
        },
    });

    livesupport.ConversationManager = nova.Class.$extend({
        __include__: [nova.DynamicProperties],
        __init__: function(parent) {
            nova.DynamicProperties.__init__.call(this, parent);
            this.set("right_offset", 0);
            this.conversations = [];
            this.users = {};
            this.on("change:right_offset", this, this.calc_positions);
            this.set("window_focus", true);
            this.set("waiting_messages", 0);
            this.focus_hdl = _.bind(function() {
                this.set("window_focus", true);
            }, this);
            $(window).bind("focus", this.focus_hdl);
            this.blur_hdl = _.bind(function() {
                this.set("window_focus", false);
            }, this);
            $(window).bind("blur", this.blur_hdl);
            this.on("change:window_focus", this, this.window_focus_change);
            this.window_focus_change();
            this.on("change:waiting_messages", this, this.messages_change);
            this.messages_change();
            this.create_ting();
        },
        create_ting: function() {
            this.ting = new Audio(new Audio().canPlayType("audio/ogg; codecs=vorbis") ?
                require.toUrl("../audio/Ting.ogg") :
                require.toUrl("../audio/Ting.mp3")
            );
        },
        window_focus_change: function() {
            if (this.get("window_focus")) {
                this.set("waiting_messages", 0);
            }
        },
        messages_change: function() {
            /*if (! instance.webclient.set_title_part)
                return;
            instance.webclient.set_title_part("im_messages", this.get("waiting_messages") === 0 ? undefined :
                _.str.sprintf(_t("%d Messages"), this.get("waiting_messages")));*/
        },
        set_me: function(me) {
            this.me = me;
        },
        activate_user: function(user) {
            if (this.users[user.get('id')]) {
                return this.users[user.get('id')];
            }
            var conv = new livesupport.Conversation(this, user, this.me);
            conv.appendTo($("body"));
            conv.on("destroyed", this, function() {
                this.conversations = _.without(this.conversations, conv);
                delete this.users[conv.user.get('id')];
                this.calc_positions();
            });
            this.conversations.push(conv);
            this.users[user.get('id')] = conv;
            this.calc_positions();
            return conv;
        },
        received_message: function(message, user) {
            if (! this.get("window_focus")) {
                this.set("waiting_messages", this.get("waiting_messages") + 1);
                this.ting.play();
                this.create_ting();
            }
            var conv = this.activate_user(user);
            conv.received_message(message);
        },
        calc_positions: function() {
            var current = this.get("right_offset");
            _.each(_.range(this.conversations.length), function(i) {
                this.conversations[i].set("right_position", current);
                current += this.conversations[i].$().outerWidth(true);
            }, this);
        },
        destroy: function() {
            $(window).unbind("blur", this.blur_hdl);
            $(window).unbind("focus", this.focus_hdl);
            nova.DynamicProperties.destroy.call(this);
        },
    });

    livesupport.Conversation = nova.Widget.$extend({
        tagClass: "oe_im_chatview",
        events: {
            "keydown input": "send_message",
            "click .oe_im_chatview_close": "destroy",
            "click .oe_im_chatview_header": "show_hide",
        },
        __init__: function(parent, user, me) {
            this.$super(parent);
            this.me = me;
            this.user = user;
            this.user.add_watcher();
            this.set("right_position", 0);
            this.shown = true;
        },
        render: function() {
            this.$().append(templateEngine.conversation({widget: this}));
            var change_status = function() {
                this.$().toggleClass("oe_im_chatview_disconnected_status", this.user.get("im_status") === false);
                this.$(".oe_im_chatview_online").toggle(this.user.get("im_status") === true);
                this._go_bottom();
            };
            this.user.on("change:im_status", this, change_status);
            change_status.call(this);

            this.on("change:right_position", this, this.calc_pos);
            this.full_height = this.$().height();
            this.calc_pos();
        },
        show_hide: function() {
            if (this.shown) {
                this.$().animate({
                    height: this.$(".oe_im_chatview_header").outerHeight(),
                });
            } else {
                this.$().animate({
                    height: this.full_height,
                });
            }
            this.shown = ! this.shown;
        },
        calc_pos: function() {
            this.$().css("right", this.get("right_position"));
        },
        received_message: function(message) {
            this._add_bubble(this.user, message.message, message.date);
        },
        send_message: function(e) {
            if(e && e.which !== 13) {
                return;
            }
            var mes = this.$("input").val();
            this.$("input").val("");
            var send_it = _.bind(function() {
                var model = connection.getModel("im.message");
                return model.call("post", [mes, this.user.get('id')], {context: {}});
            }, this);
            var tries = 0;
            send_it().then(_.bind(function() {
                this._add_bubble(this.me, mes, new Date());
            }, this), function(error, e) {
                e.preventDefault();
                tries += 1;
                if (tries < 3)
                    return send_it();
            });
        },
        _add_bubble: function(user, item, date) {
            var items = [item];
            if (user === this.last_user) {
                this.last_bubble.remove();
                items = this.last_items.concat(items);
            }
            this.last_user = user;
            this.last_items = items;
            date = "" + date; // TODO
            
            this.last_bubble = $(templateEngine.conversation_bubble({"items": items, "user": user, "time": date}));
            $(this.$(".oe_im_chatview_content").children()[0]).append(this.last_bubble);
            this._go_bottom();
        },
        _go_bottom: function() {
            this.$(".oe_im_chatview_content").scrollTop($(this.$(".oe_im_chatview_content").children()[0]).height());
        },
        destroy: function() {
            this.user.remove_watcher();
            this.trigger("destroyed");
            return this._super();
        },
    });



    return livesupport;
});
