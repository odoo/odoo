
/*
    This file must compile in EcmaScript 3 and work in IE7.

    Prerequisites to use this module:
    - load the im_common.xml qweb template into openerp.qweb
    - implement all the stuff defined later
*/

(function() {

function declare($, _, openerp) {
    /* jshint es3: true */
    "use strict";

    var im_common = {};

    /*
        All of this must be defined to use this module
    */
    _.extend(im_common, {
        notification: function(message) {
            throw new Error("Not implemented");
        },
        connection: null
    });

    var _t = openerp._t;

    var ERROR_DELAY = 5000;

    im_common.ImUser = openerp.Class.extend(openerp.PropertiesMixin, {
        init: function(parent, user_rec) {
            openerp.PropertiesMixin.init.call(this, parent);
            
            user_rec.image_url = im_common.connection.url('/web/binary/image', {model:'im.user', field: 'image', id: user_rec.id});

            this.set(user_rec);
            this.set("watcher_count", 0);
            this.on("change:watcher_count", this, function() {
                if (this.get("watcher_count") === 0)
                    this.destroy();
            });
        },
        destroy: function() {
            this.trigger("destroyed");
            openerp.PropertiesMixin.destroy.call(this);
        },
        add_watcher: function() {
            this.set("watcher_count", this.get("watcher_count") + 1);
        },
        remove_watcher: function() {
            this.set("watcher_count", this.get("watcher_count") - 1);
        }
    });

    im_common.ConversationManager = openerp.Class.extend(openerp.PropertiesMixin, {
        init: function(parent, options) {
            openerp.PropertiesMixin.init.call(this, parent);
            this.options = _.clone(options) || {};
            _.defaults(this.options, {
                inputPlaceholder: _t("Say something..."),
                defaultMessage: null,
                userName: _t("Anonymous"),
                anonymous_mode: false
            });
            this.set("right_offset", 0);
            this.set("bottom_offset", 0);
            this.conversations = [];
            this.on("change:right_offset", this, this.calc_positions);
            this.on("change:bottom_offset", this, this.calc_positions);
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
            this.unload_event_handler = _.bind(this.unload, this);
        },
        start_polling: function() {
            var self = this;
            var def = $.when();
            var uuid = false;

            if (this.options.anonymous_mode) {
                uuid = localStorage["oe_livesupport_uuid"] || false;

                if (! uuid) {
                    def = im_common.connection.rpc("/longpolling/im/gen_uuid", {}).then(function(my_uuid) {
                        uuid = my_uuid;
                        localStorage["oe_livesupport_uuid"] = uuid;
                    });
                }
                def = def.then(function() {
                    return im_common.connection.model("im.user").call("assign_name", [uuid, self.options.userName]);
                });
            }

            return def.then(function() {
                return im_common.connection.model("im.user").call("get_my_id", [uuid]);
            }).then(function(my_user_id) {
                self.my_id = my_user_id;
                return self.ensure_users([self.my_id]);
            }).then(function() {
                var me = self.users_cache[self.my_id];
                delete self.users_cache[self.my_id];
                self.me = me;
                me.set("name", _t("You"));
                return im_common.connection.rpc("/longpolling/im/activated", {}, {shadow: true});
            }).then(function(activated) {
                if (activated) {
                    self.activated = true;
                    $(window).on("unload", self.unload_event_handler);
                    self.poll();
                } else {
                    return $.Deferred().reject();
                }
            }, function(a, e) {
                e.preventDefault();
            });
        },
        unload: function() {
            return im_common.connection.model("im.user").call("im_disconnect", [], {uuid: this.me.get("uuid"), context: {}});
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
                return im_common.connection.model("im.user").call("read", [_.values(no_cache), []]).then(function(users) {
                    self.add_to_user_cache(users);
                });
        },
        add_to_user_cache: function(user_recs) {
            _.each(user_recs, function(user_rec) {
                if (! this.users_cache[user_rec.id]) {
                    var user = new im_common.ImUser(this, user_rec);
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
            im_common.connection.rpc("/longpolling/im/poll", {
                last: this.last,
                users_watch: user_ids,
                uuid: self.me.get("uuid")
            }, {shadow: true}).then(function(result) {
                _.each(result.users_status, function(el) {
                    if (self.get_user(el.id))
                        self.get_user(el.id).set(el);
                });
                self.last = result.last;
                self.received_messages(result.res).then(function() {
                    self.poll();
                });
            }, function(unused, e) {
                e.preventDefault();
                setTimeout(_.bind(self.poll, self), ERROR_DELAY);
            });
        },
        get_activated: function() {
            return this.activated;
        },
        create_ting: function() {
            if (typeof(Audio) === "undefined") {
                this.ting = {play: function() {}};
                return;
            }
            var kitten = jQuery.deparam !== undefined && jQuery.deparam(jQuery.param.querystring()).kitten !== undefined;
            this.ting = new Audio(im_common.connection.url(
                "/im/static/src/audio/" +
                (kitten ? "purr" : "Ting") +
                (new Audio().canPlayType("audio/ogg; codecs=vorbis") ? ".ogg": ".mp3")
            ));
        },
        window_focus_change: function() {
            if (this.get("window_focus")) {
                this.set("waiting_messages", 0);
            }
        },
        messages_change: function() {
            if (! openerp.webclient || !openerp.webclient.set_title_part)
                return;
            openerp.webclient.set_title_part("im_messages", this.get("waiting_messages") === 0 ? undefined :
                _.str.sprintf(_t("%d Messages"), this.get("waiting_messages")));
        },
        activate_session: function(session_id, focus) {
            var conv = _.find(this.conversations, function(conv) {return conv.session_id == session_id;});
            var def = $.when();
            if (! conv) {
                conv = new im_common.Conversation(this, this, session_id, this.options);
                def = conv.appendTo($("body")).then(_.bind(function() {
                    conv.on("destroyed", this, function() {
                        this.conversations = _.without(this.conversations, conv);
                        this.calc_positions();
                    });
                    this.conversations.push(conv);
                    this.calc_positions();
                    this.trigger("new_conversation", conv);
                }, this));
            }
            if (focus) {
                def = def.then(function() {
                    conv.focus();
                });
            }
            return def.then(function() {return conv});
        },
        received_messages: function(messages) {
            var self = this;
            if (! this.get("window_focus") && messages.length >= 1) {
                this.set("waiting_messages", this.get("waiting_messages") + messages.length);
                this.ting.play();
                this.create_ting();
            }
            var defs = [];
            _.each(messages, function(message) {
                defs.push(self.activate_session(message.session_id[0]).then(function(conv) {
                    return conv.received_message(message);
                }));
            });
            return $.when.apply($, defs);
        },
        calc_positions: function() {
            var current = this.get("right_offset");
            _.each(_.range(this.conversations.length), function(i) {
                this.conversations[i].set("bottom_position", this.get("bottom_offset"));
                this.conversations[i].set("right_position", current);
                current += this.conversations[i].$().outerWidth(true);
            }, this);
        },
        destroy: function() {
            $(window).off("unload", this.unload_event_handler);
            $(window).unbind("blur", this.blur_hdl);
            $(window).unbind("focus", this.focus_hdl);
            openerp.PropertiesMixin.destroy.call(this);
        }
    });

    im_common.Conversation = openerp.Widget.extend({
        className: "openerp_style oe_im_chatview",
        events: {
            "keydown input": "send_message",
            "click .oe_im_chatview_close": "destroy",
            "click .oe_im_chatview_header": "show_hide"
        },
        init: function(parent, c_manager, session_id, options) {
            this._super(parent);
            this.c_manager = c_manager;
            this.options = options || {};
            this.session_id = session_id;
            this.set("right_position", 0);
            this.set("bottom_position", 0);
            this.shown = true;
            this.set("pending", 0);
            this.inputPlaceholder = this.options.defaultInputPlaceholder;
            this.users = [];
            this.others = [];
        },
        start: function() {
            var self = this;
            var user_ids;
            return im_common.connection.model("im.session").call("read", [self.session_id]).then(function(session) {
                user_ids = _.without(session.user_ids, self.c_manager.me.get("id"));
                return self.c_manager.ensure_users(session.user_ids);
            }).then(function() {
                self.users = _.map(user_ids, function(id) {return self.c_manager.get_user(id);});
                _.each(self.users, function(user) {
                    user.add_watcher();
                });
                // TODO: correctly display status
                self.$().append(openerp.qweb.render("im_common.conversation", {widget: self, to_url: _.bind(im_common.connection.url, im_common.connection)}));
                var change_status = function() {
                    self.$().toggleClass("oe_im_chatview_disconnected_status", self.users[0].get("im_status") === false);
                    self.$(".oe_im_chatview_online").toggle(self.users[0].get("im_status") === true);
                    self._go_bottom();
                };
                self.users[0].on("change:im_status", self, change_status);
                change_status.call(self);

                self.on("change:right_position", self, self.calc_pos);
                self.on("change:bottom_position", self, self.calc_pos);
                self.full_height = self.$().height();
                self.calc_pos();
                self.on("change:pending", self, _.bind(function() {
                    if (self.get("pending") === 0) {
                        self.$(".oe_im_chatview_nbr_messages").text("");
                    } else {
                        self.$(".oe_im_chatview_nbr_messages").text("(" + self.get("pending") + ")");
                    }
                }, self));
            });
        },
        show_hide: function() {
            if (this.shown) {
                this.$().animate({
                    height: this.$(".oe_im_chatview_header").outerHeight()
                });
            } else {
                this.$().animate({
                    height: this.full_height
                });
            }
            this.shown = ! this.shown;
            if (this.shown) {
                this.set("pending", 0);
            }
        },
        calc_pos: function() {
            this.$().css("right", this.get("right_position"));
            this.$().css("bottom", this.get("bottom_position"));
        },
        received_message: function(message) {
            if (this.shown) {
                this.set("pending", 0);
            } else {
                this.set("pending", this.get("pending") + 1);
            }
            this.c_manager.ensure_users([message.from_id[0]]).then(_.bind(function() {
                var user = this.c_manager.get_user(message.from_id[0]);
                if (! _.contains(this.users, user) && ! _.contains(this.others, user)) {
                    this.others.push(user);
                    user.add_watcher();
                }
                this._add_bubble(user, message.message, openerp.str_to_datetime(message.date));
            }, this));
        },
        send_message: function(e) {
            if(e && e.which !== 13) {
                return;
            }
            var mes = this.$("input").val();
            if (! mes.trim()) {
                return;
            }
            this.$("input").val("");
            var send_it = _.bind(function() {
                var model = im_common.connection.model("im.message");
                return model.call("post", [mes, this.session_id], {uuid: this.c_manager.me.get("uuid"), context: {}});
            }, this);
            var tries = 0;
            send_it().then(_.bind(function() {}, function(error, e) {
                e.preventDefault();
                tries += 1;
                if (tries < 3)
                    return send_it();
            }));
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
            
            this.last_bubble = $(openerp.qweb.render("im_common.conversation_bubble", {"items": items, "user": user, "time": date}));
            $(this.$(".oe_im_chatview_content").children()[0]).append(this.last_bubble);
            this._go_bottom();
        },
        _go_bottom: function() {
            this.$(".oe_im_chatview_content").scrollTop($(this.$(".oe_im_chatview_content").children()[0]).height());
        },
        add_user: function(user) {
            if (user === this.me || _.contains(this.users, user))
                return;
            im_common.connection.model("im.session").call("add_to_session",
                    [this.session_id, user.get("id"), this.c_manager.me.get("uuid")]).then(_.bind(function() {
                if (_.contains(this.others, user)) {
                    this.others = _.without(this.others, user);
                } else {
                    user.add_watcher();
                }
                this.users.push(user);
            }, this));
        },
        focus: function() {
            this.$(".oe_im_chatview_input").focus();
            if (! this.shown)
                this.show_hide();
        },
        destroy: function() {
            _.each(this.users, function(user) {
                user.remove_watcher();
            })
            _.each(this.others, function(user) {
                user.remove_watcher();
            })
            this.trigger("destroyed");
            return this._super();
        }
    });

    return im_common;
}

if (typeof(define) !== "undefined") {
    define(["jquery", "underscore", "openerp"], declare);
} else {
    window.im_common = declare($, _, openerp);
}

})();
