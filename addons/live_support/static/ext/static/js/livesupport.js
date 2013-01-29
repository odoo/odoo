
define(["nova", "jquery", "underscore", "oeclient", "require"], function(nova, $, _, oeclient, require) {
    var livesupport = {};

    var templateEngine = new nova.TemplateEngine();
    templateEngine.extendEnvironment({"toUrl": _.bind(require.toUrl, require)});
    var connection;

    livesupport.main = function(server_url, db, login, password) {
        var templates_def = $.ajax({
            url: require.toUrl("./livesupport_templates.js"),
            jsonp: false,
            jsonpCallback: "oe_livesupport_templates_callback",
            dataType: "jsonp",
            cache: true,
        }).then(function(content) {
            return templateEngine.loadFileContent(content);
        });
        var css_def = $.Deferred();
        $('<link rel="stylesheet" href="' + require.toUrl("../css/livesupport.css") + '"></link>')
                .appendTo($("head")).ready(function() {
            css_def.resolve();
        });

        $.when(templates_def, css_def).then(function() {
            console.log("starting client");
            connection = new oeclient.Connection(new oeclient.JsonpRPCConnector(server_url), db, login, password);
            connection.getModel("res.users").search_read([["login", "=", ["demo"]]]).then(function(result) {
                demo_id = result[0].id;
                var manager = new livesupport.ConversationManager(null);
                manager.start_polling().then(function() {
                    manager.ensure_users([demo_id]).then(function() {
                        manager.activate_user(manager.get_user(demo_id));
                    });
                });
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
            this.activated = false;
            this.users_cache = {};
            this.last = null;
        },
        start_polling: function() {
            var self = this;
            return this.ensure_users([connection.userId]).then(function() {
                var me = self.users_cache[connection.userId];
                delete self.users_cache[connection.userId];
                self.me = me;
                connection.connector.call("/longpolling/im/activated", {}).then(function(activated) {
                    if (activated) {
                        self.activated = true;
                        self.poll();
                    }
                });
            });
        },
        ensure_users: function(user_ids) {
            var no_cache = {};
            _.each(user_ids, function(el) {
                if (! this.users_cache[el])
                    no_cache[el] = el;
            }, this);
            var self = this;
            if (_.size(no_cache) === 0)
                return $.when();
            else
                return connection.getModel("im.user").call("read_users", [_.values(no_cache), ["name"]]).then(function(users) {
                    self.add_to_user_cache(users);
                });
        },
        add_to_user_cache: function(user_recs) {
            _.each(user_recs, function(user_rec) {
                if (! this.users_cache[user_rec.id]) {
                    var user = new livesupport.ImUser(this, user_rec);
                    this.users_cache[user_rec.id] = user;
                    user.on("destroyed", this, function() {
                        delete this.users_cache[user_rec.id];
                    });
                }
            }, this);
        },
        get_user: function(user_id) {
            return this.users_cache[user_id];
        },
        poll: function() {
            var self = this;
            var user_ids = _.map(this.users_cache, function(el) {
                return el.get("id");
            });
            connection.connector.call("/longpolling/im/poll", {
                last: this.last,
                users_watch: user_ids,
                db: connection.database,
                uid: connection.userId,
                password: connection.password,
            }).then(function(result) {
                _.each(result.users_status, function(el) {
                    if (self.get_user(el.id))
                        self.get_user(el.id).set(el);
                });
                self.last = result.last;
                var user_ids = _.pluck(_.pluck(result.res, "from"), 0);
                self.ensure_users(user_ids).then(function() {
                    _.each(result.res, function(mes) {
                        var user = self.get_user(mes.from[0]);
                        self.received_message(mes, user);
                    });
                    self.poll();
                });
            }, function() {
                setTimeout(_.bind(self.poll, self), ERROR_DELAY);
            });
        },
        get_activated: function() {
            return this.activated;
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
        className: "openerp_style oe_im_chatview",
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
            this._add_bubble(this.user, message.message, oeclient.str_to_datetime(message.date));
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
            var zpad = function(str, size) {
                str = "" + str;
                return new Array(size - str.length + 1).join('0') + str;
            };
            date = "" + zpad(date.getHours(), 2) + ":" + zpad(date.getMinutes(), 2);
            
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
