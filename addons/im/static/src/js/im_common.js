
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
            user_rec.image_url = im_common.connection.url("/im/static/src/img/avatar/avatar.jpeg");

            // TODO : check it works correctly
            if (user_rec.user_id)
                user_rec.image_url = im_common.connection.url('/web/binary/image', {model:'res.users', field: 'image_small', id: user_rec.user_id[0]});
            /*if (user_rec.image)
                user_rec.image_url = "data:image/png;base64," + user_rec.image;*/

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
            this.users = {};
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

            var auth_def = null;
            var user_id = null;

            if (this.options.anonymous_mode) {
                var uuid = localStorage["oe_livesupport_uuid"];
                var def = $.when(uuid);

                if (! uuid) {
                    def = im_common.connection.rpc("/longpolling/im/gen_uuid", {});
                }
                var anonymous_user_id = null;
                auth_def = def.then(function(uuid) {
                    localStorage["oe_livesupport_uuid"] = uuid;
                    return im_common.connection.model("im.user").call("get_by_user_id", [uuid]);
                }).then(function(my_id) {
                    user_id = my_id["id"];
                    return im_common.connection.model("im.user").call("assign_name", [uuid, self.options.userName]);
                });
            } else {
                auth_def = im_common.connection.model("im.user").call("get_by_user_id",
                        [im_common.connection.uid]).then(function(my_id) {
                    user_id = my_id["id"];
                });
            }

            return auth_def.then(function() {
                self.my_id = user_id;
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
                var user_ids = _.pluck(_.pluck(result.res, "from_id"), 0);
                self.ensure_users(user_ids).then(function() {
                    _.each(result.res, function(mes) {
                        var user = self.get_user(mes.from_id[0]);
                        self.received_message(mes, user);
                    });
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
        activate_user: function(user, focus) {
            var conv = this.users[user.get('id')];
            if (! conv) {
                conv = new im_common.Conversation(this, user, this.me, this.options);
                conv.appendTo($("body"));
                conv.on("destroyed", this, function() {
                    this.conversations = _.without(this.conversations, conv);
                    delete this.users[conv.user.get('id')];
                    this.calc_positions();
                });
                this.conversations.push(conv);
                this.users[user.get('id')] = conv;
                this.calc_positions();
            }
            if (focus)
                conv.focus();
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
        init: function(parent, user, me, options) {
            this._super(parent);
            this.options = options;
            this.me = me;
            this.user = user;
            this.user.add_watcher();
            this.set("right_position", 0);
            this.set("bottom_position", 0);
            this.shown = true;
            this.set("pending", 0);
            this.inputPlaceholder = this.options.defaultInputPlaceholder;
        },
        start: function() {
            this.$().append(openerp.qweb.render("im_common.conversation", {widget: this, to_url: _.bind(im_common.connection.url, im_common.connection)}));
            var change_status = function() {
                this.$().toggleClass("oe_im_chatview_disconnected_status", this.user.get("im_status") === false);
                this.$(".oe_im_chatview_online").toggle(this.user.get("im_status") === true);
                this._go_bottom();
            };
            this.user.on("change:im_status", this, change_status);
            change_status.call(this);

            this.on("change:right_position", this, this.calc_pos);
            this.on("change:bottom_position", this, this.calc_pos);
            this.full_height = this.$().height();
            this.calc_pos();
            this.on("change:pending", this, _.bind(function() {
                if (this.get("pending") === 0) {
                    this.$(".oe_im_chatview_nbr_messages").text("");
                } else {
                    this.$(".oe_im_chatview_nbr_messages").text("(" + this.get("pending") + ")");
                }
            }, this));
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
            this._add_bubble(this.user, message.message, openerp.str_to_datetime(message.date));
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
                return model.call("post", [mes, this.user.get('id')], {uuid: this.me.get("uuid"), context: {}});
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
        focus: function() {
            this.$(".oe_im_chatview_input").focus();
            if (! this.shown)
                this.show_hide();
        },
        destroy: function() {
            this.user.remove_watcher();
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
