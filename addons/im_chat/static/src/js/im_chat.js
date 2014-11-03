(function(){

    "use strict";

    var _t = openerp._t;
    var _lt = openerp._lt;
    var QWeb = openerp.qweb;
    var NBR_LIMIT_HISTORY = 20;
    var USERS_LIMIT = 20;
    var im_chat = openerp.im_chat = {};

    im_chat.ConversationManager = openerp.Widget.extend({
        init: function(parent, options) {
            var self = this;
            this._super(parent);
            this.options = _.clone(options) || {};
            _.defaults(this.options, {
                inputPlaceholder: _t("Say something..."),
                defaultMessage: null,
                defaultUsername: _t("Visitor"),
            });
            // business
            this.sessions = {};
            this.bus = openerp.bus.bus;
            this.bus.on("notification", this, this.on_notification);
            this.bus.options["im_presence"] = true;

            // ui
            this.set("right_offset", 0);
            this.set("bottom_offset", 0);
            this.on("change:right_offset", this, this.calc_positions);
            this.on("change:bottom_offset", this, this.calc_positions);

            this.set("window_focus", true);
            this.on("change:window_focus", self, function(e) {
                self.bus.options["im_presence"] = self.get("window_focus");
            });
            this.set("waiting_messages", 0);
            this.on("change:waiting_messages", this, this.window_title_change);
            $(window).on("focus", _.bind(this.window_focus, this));
            $(window).on("blur", _.bind(this.window_blur, this));
            this.window_title_change();
        },
        on_notification: function(notification) {
            var self = this;
            var channel = notification[0];
            var message = notification[1];
            var regex_uuid = new RegExp(/(\w{8}(-\w{4}){3}-\w{12}?)/g);

            // Concern im_chat : if the channel is the im_chat.session or im_chat.status, or a 'private' channel (aka the UUID of a session)
            if((Array.isArray(channel) && (channel[1] === 'im_chat.session' || channel[1] === 'im_chat.presence')) || (regex_uuid.test(channel))){
                // message to display in the chatview
                if (message.type === "message" || message.type === "meta") {
                    self.received_message(message);
                }
                // activate the received session
                if(message.uuid){
                    this.apply_session(message);
                }
                // user status notification
                if(message.im_status){
                    self.trigger("im_new_user_status", [message]);
                }
            }
        },

        // window focus unfocus beep and title
        window_focus: function() {
            this.set("window_focus", true);
            this.set("waiting_messages", 0);
        },
        window_blur: function() {
            this.set("window_focus", false);
        },
        window_beep: function() {
            if (typeof(Audio) === "undefined") {
                return;
            }
            var audio = new Audio();
            var ext = audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
            var kitten = jQuery.deparam !== undefined && jQuery.deparam(jQuery.param.querystring()).kitten !== undefined;
            audio.src = openerp.session.url("/im_chat/static/src/audio/" + (kitten ? "purr" : "ting") + ext);
            audio.play();
        },
        window_title_change: function() {
            var title = undefined;
            if (this.get("waiting_messages") !== 0) {
                title = _.str.sprintf(_t("%d Messages"), this.get("waiting_messages"))
                this.window_beep();
            }
            if (! openerp.webclient || !openerp.webclient.set_title_part)
                return;
            openerp.webclient.set_title_part("im_messages", title);
        },

        apply_session: function(session, focus){
            var self = this;
            var conv = this.sessions[session.uuid];
            if (! conv) {
                if(session.state !== 'closed'){
                    conv = new im_chat.Conversation(this, this, session, this.options);
                    conv.appendTo($("body"));
                    conv.on("destroyed", this, _.bind(this.delete_session, this));
                    this.sessions[session.uuid] = conv;
                    this.calc_positions();
                }
            }else{
                conv.set("session", session);
            }
            conv && this.trigger("im_session_activated", conv);
            if (focus)
                conv.focus();
            return conv;
        },
        activate_session: function(session, focus) {
            var self = this;
            var active_session = _.clone(session);
            active_session.state = 'open';
            var conv = this.apply_session(active_session, focus);
            if(session.state !== 'open'){
                conv.update_fold_state('open');
            }
            return conv;
        },
        delete_session: function(uuid){
            delete this.sessions[uuid];
            this.calc_positions();
        },
        received_message: function(message) {
            var self = this;
            var session_id = message.to_id[0];
            var uuid = message.to_id[1];
            if (! this.get("window_focus")) {
                this.set("waiting_messages", this.get("waiting_messages") + 1);
            }
            var conv = this.sessions[uuid];
            if(!conv){
                // fetch the session, and init it with the message
                var def_session = new openerp.Model("im_chat.session").call("session_info", [], {"ids" : [session_id]}).then(function(session){
                    conv = self.activate_session(session, false);
                    conv.received_message(message);
                });
            }else{
                conv.received_message(message);
            }
        },
        calc_positions: function() {
            var self = this;
            var current = this.get("right_offset");
            _.each(this.sessions, function(s) {
                s.set("bottom_position", self.get("bottom_offset"));
                s.set("right_position", current);
                current += s.$().outerWidth(true);
            });
        },
        destroy: function() {
            $(window).off("unload", this.unload);
            $(window).off("focus", this.window_focus);
            $(window).off("blur", this.window_blur);
            return this._super();
        }
    });

    im_chat.Conversation = openerp.Widget.extend({
        className: "openerp_style oe_im_chatview",
        events: {
            "keydown input": "keydown",
            "click .oe_im_chatview_close": "click_close",
            "click .oe_im_chatview_header": "click_header"
        },
        init: function(parent, c_manager, session, options) {
            this._super(parent);
            this.c_manager = c_manager;
            this.options = options || {};
            this.loading_history = true;
            this.set("messages", []);
            this.set("session", session);
            this.set("right_position", 0);
            this.set("bottom_position", 0);
            this.set("pending", 0);
            this.inputPlaceholder = this.options.defaultInputPlaceholder;
        },
        start: function() {
            var self = this;
            self.$().append(openerp.qweb.render("im_chat.Conversation", {widget: self}));
            self.$().hide();
            self.on("change:session", self, self.update_session);
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
            // messages business
            self.on("change:messages", this, this.render_messages);
            self.$('.oe_im_chatview_content').on('scroll',function(){
                if($(this).scrollTop() === 0){
                    self.load_history();
                }
            });
            self.load_history();
            self.$().show();
            // prepare the header and the correct state
            self.update_session();
        },
        show: function(){
            this.$().animate({
                height: this.full_height
            });
            this.set("pending", 0);
        },
        hide: function(){
            this.$().animate({
                height: this.$(".oe_im_chatview_header").outerHeight()
            });
        },
        calc_pos: function() {
            this.$().css("right", this.get("right_position"));
            this.$().css("bottom", this.get("bottom_position"));
        },
        update_fold_state: function(state){
            return new openerp.Model("im_chat.session").call("update_state", [], {"uuid" : this.get("session").uuid, "state" : state});
        },
        update_session: function(){
            // built the name
            var names = [];
            _.each(this.get("session").users, function(user){
                if( (openerp.session.uid !== user.id) && !(_.isUndefined(openerp.session.uid) && !user.id) ){
                    names.push(user.name);
                }
            });
            this.$(".oe_im_chatview_header_name").text(names.join(", "));
            this.$(".oe_im_chatview_header_name").attr('title', names.join(", "));
            // update the fold state
            if(this.get("session").state){
                if(this.get("session").state === 'closed'){
                    this.destroy();
                }else{
                    if(this.get("session").state === 'open'){
                        this.show();
                    }else{
                        this.hide();
                    }
                }
            }
        },
        load_history: function(){
            var self = this;
            if(this.loading_history){
                var data = {uuid: self.get("session").uuid, limit: NBR_LIMIT_HISTORY};
                var lastid = _.first(this.get("messages")) ? _.first(this.get("messages")).id : false;
                if(lastid){
                    data["last_id"] = lastid;
                }
                openerp.session.rpc("/im_chat/history", data).then(function(messages){
                    if(messages){
                        self.insert_messages(messages);
    					if(messages.length != NBR_LIMIT_HISTORY){
                            self.loading_history = false;
                        }
                    }else{
                        self.loading_history = false;
                    }
                });
            }
        },
        received_message: function(message) {
            if (this.get('session').state === 'open') {
                this.set("pending", 0);
            } else {
                this.set("pending", this.get("pending") + 1);
            }
            this.insert_messages([message]);
        },
        send_message: function(message, type) {
            var self = this;
            var send_it = function() {
                return openerp.session.rpc("/im_chat/post", {uuid: self.get("session").uuid, message_type: type, message_content: message});
            };
            var tries = 0;
            send_it().fail(function(error, e) {
                e.preventDefault();
                tries += 1;
                if (tries < 3)
                    return send_it();
            });
        },
        insert_messages: function(messages){
        	var self = this;
            // avoid duplicated messages
        	messages = _.filter(messages, function(m){ return !_.contains(_.pluck(self.get("messages"), 'id'), m.id) ; });
            // escape the message content and set the timezone
            _.map(messages, function(m){
                if(!m.from_id){
                    m.from_id = [false, self.options["defaultUsername"]];
                }
                m.message = self.escape_keep_url(m.message);
                m.message = self.smiley(m.message);
                m.create_date = Date.parse(m.create_date).setTimezone("UTC").toString("yyyy-MM-dd HH:mm:ss");
                return m;
            });
           	this.set("messages", _.sortBy(this.get("messages").concat(messages), function(m){ return m.id; }));
        },
        render_messages: function(){
            var self = this;
            var res = {};
            var last_date_day, last_user_id = -1;
            _.each(this.get("messages"), function(current){
                // add the url of the avatar for all users in the conversation
                current.from_id[2] = openerp.session.url(_.str.sprintf("/im_chat/image/%s/%s", self.get('session').uuid, current.from_id[0]));
                var date_day = current.create_date.split(" ")[0];
                if(date_day !== last_date_day){
                    res[date_day] = [];
                    last_user_id = -1;
                }
                last_date_day = date_day;
                if(current.type == "message"){ // traditionnal message
                    if(last_user_id === current.from_id[0]){
                        _.last(res[date_day]).push(current);
                    }else{
                        res[date_day].push([current]);
                    }
                    last_user_id = current.from_id[0];
                }else{ // meta message
                    res[date_day].push([current]);
                    last_user_id = -1;
                }
            });
            // render and set the content of the chatview
            this.$('.oe_im_chatview_content_bubbles').html($(openerp.qweb.render("im_chat.Conversation_content", {"list": res})));
            this._go_bottom();
        },
        keydown: function(e) {
            if(e && e.which !== 13) {
                return;
            }
            var mes = this.$("input").val();
            if (! mes.trim()) {
                return;
            }
            this.$("input").val("");
            this.send_message(mes, "message");
        },
        get_smiley_list: function(){
            var kitten = jQuery.deparam !== undefined && jQuery.deparam(jQuery.param.querystring()).kitten !== undefined;
            var smileys = {
                ":'(": "&#128546;",
                ":O" : "&#128561;",
                "3:)": "&#128520;",
                ":)" : "&#128522;",
                ":D" : "&#128517;",
                ";)" : "&#128521;",
                ":p" : "&#128523;",
                ":(" : "&#9785;",
                ":|" : "&#128528;",
                ":/" : "&#128527;",
                "8)" : "&#128563;",
                ":s" : "&#128534;",
                ":pinky" : "<img src='/im_chat/static/src/img/pinky.png'/>",
                ":musti" : "<img src='/im_chat/static/src/img/musti.png'/>",
            };
            if(kitten){
                _.extend(smileys, {
                    ":)" : "&#128570;",
                    ":D" : "&#128569;",
                    ";)" : "&#128572;",
                    ":p" : "&#128573;",
                    ":(" : "&#128576;",
                    ":|" : "&#128575;",
                });
            }
            return smileys;
        },
        smiley: function(str){
            var re_escape = function(str){
                return String(str).replace(/([.*+?=^!:${}()|[\]\/\\])/g, '\\$1');
             };
             var smileys = this.get_smiley_list();
            _.each(_.keys(smileys), function(key){
                str = str.replace( new RegExp("(?:^|\\s)(" + re_escape(key) + ")(?:\\s|$)"), ' <span class="smiley">'+smileys[key]+'</span> ');
            });
            return str;
        },
        escape_keep_url: function(str){
            var url_regex = /(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?/gi;
            var last = 0;
            var txt = "";
            while (true) {
                var result = url_regex.exec(str);
                if (! result)
                    break;
                txt += _.escape(str.slice(last, result.index));
                last = url_regex.lastIndex;
                var url = _.escape(result[0]);
                txt += '<a href="' + url + '" target="_blank">' + url + '</a>';
            }
            txt += _.escape(str.slice(last, str.length));
            return txt;
        },
        _go_bottom: function() {
            this.$(".oe_im_chatview_content").scrollTop(this.$(".oe_im_chatview_content").get(0).scrollHeight);
        },
        add_user: function(user){
            return new openerp.Model("im_chat.session").call("add_user", [this.get("session").uuid , user.id]);
        },
        focus: function() {
            this.$(".oe_im_chatview_input").focus();
        },
        click_header: function(){
            this.update_fold_state();
        },
        click_close: function(event) {
            event.stopPropagation();
            this.update_fold_state('closed');
        },
        destroy: function() {
            this.trigger("destroyed", this.get('session').uuid);
            return this._super();
        }
    });

    im_chat.UserWidget = openerp.Widget.extend({
        "template": "im_chat.UserWidget",
        events: {
            "click": "activate_user",
        },
        init: function(parent, user) {
            this._super(parent);
            this.set("id", user.id);
            this.set("name", user.name);
            this.set("im_status", user.im_status);
            this.set("image_url", user.image_url);
        },
        start: function() {
            this.$el.data("user", {id:this.get("id"), name:this.get("name")});
            this.$el.draggable({helper: "clone"});
            this.on("change:im_status", this, this.update_status);
            this.update_status();
        },
        update_status: function(){
            this.$(".oe_im_user_online").toggle(this.get('im_status') !== 'offline');
            var img_src = (this.get('im_status') == 'away' ? '/im_chat/static/src/img/yellow.png' : '/im_chat/static/src/img/green.png');
            this.$(".oe_im_user_online").attr('src', img_src);
        },
        activate_user: function() {
            this.trigger("activate_user", this.get("id"));
        },
    });

    im_chat.InstantMessaging = openerp.Widget.extend({
        template: "im_chat.InstantMessaging",
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
            this.widgets = {};

            this.c_manager = new openerp.im_chat.ConversationManager(this);
            this.on("change:right_offset", this.c_manager, _.bind(function() {
                this.c_manager.set("right_offset", this.get("right_offset"));
            }, this));
            this.user_search_dm = new openerp.web.DropMisordered();
        },
        start: function() {
            var self = this;
            this.$el.css("right", -this.$el.outerWidth());
            $(window).scroll(_.bind(this.calc_box, this));
            $(window).resize(_.bind(this.calc_box, this));
            this.calc_box();

            this.on("change:current_search", this, this.search_users_status);

            // add a drag & drop listener
            self.c_manager.on("im_session_activated", self, function(conv) {
                conv.$el.droppable({
                    drop: function(event, ui) {
                        conv.add_user(ui.draggable.data("user"));
                    }
                });
            });
            // add a listener for the update of users status
            this.c_manager.on("im_new_user_status", this, this.update_users_status);

            // fetch the unread message and the recent activity (e.i. to re-init in case of refreshing page)
            openerp.session.rpc("/im_chat/init",{}).then(function(notifications) {
                _.each(notifications, function(notif){
                    self.c_manager.on_notification(notif);
                });
                // start polling
                openerp.bus.bus.start_polling();
            });
            return;
        },
        calc_box: function() {
            var $topbar = window.$('#oe_main_menu_navbar'); // .oe_topbar is replaced with .navbar of bootstrap3
            var top = $topbar.offset().top + $topbar.height();
            top = Math.max(top - $(window).scrollTop(), 0);
            this.$el.css("top", top);
            this.$el.css("bottom", 0);
        },
        input_change: function() {
            this.set("current_search", this.$(".oe_im_searchbox").val());
        },
        search_users_status: function(e) {
            var user_model = new openerp.web.Model("res.users");
            var self = this;
            return this.user_search_dm.add(user_model.call("im_search", [this.get("current_search"),
                        USERS_LIMIT], {context:new openerp.web.CompoundContext()})).then(function(result) {
                self.$(".oe_im_input").val("");
                var old_widgets = self.widgets;
                self.widgets = {};
                self.users = [];
                _.each(result, function(user) {
                    user.image_url = openerp.session.url('/web/binary/image', {model:'res.users', field: 'image_small', id: user.id});
                    var widget = new openerp.im_chat.UserWidget(self, user);
                    widget.appendTo(self.$(".oe_im_users"));
                    widget.on("activate_user", self, self.activate_user);
                    self.widgets[user.id] = widget;
                    self.users.push(user);
                });
                _.each(old_widgets, function(w) {
                    w.destroy();
                });
            });
        },
        switch_display: function() {
            this.calc_box();
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
                if (! openerp.bus.bus.activated) {
                    this.do_warn("Instant Messaging is not activated on this server. Try later.", "");
                    return;
                }
                // update the list of user status when show the IM
                this.search_users_status();
                this.$el.animate({
                    right: 0,
                }, opt);
            }
            this.shown = ! this.shown;
        },
        activate_user: function(user_id) {
            var self = this;
            var sessions = new openerp.web.Model("im_chat.session");
            return sessions.call("session_get", [user_id]).then(function(session) {
                self.c_manager.activate_session(session, true);
            });
        },
        update_users_status: function(users_list){
            var self = this;
            _.each(users_list, function(el) {
                self.widgets[el.id] && self.widgets[el.id].set("im_status", el.im_status);
            });
        }
    });

    im_chat.ImTopButton = openerp.Widget.extend({
        template:'im_chat.ImTopButton',
        events: {
            "click": "clicked",
        },
        clicked: function(ev) {
            ev.preventDefault();
            this.trigger("clicked");
        },
    });

    if(openerp.web && openerp.web.UserMenu) {
        openerp.web.UserMenu.include({
            do_update: function(){
                var self = this;
                var Users = new openerp.web.Model('res.users');
                Users.call('has_group', ['base.group_user']).done(function(is_employee) {
                    if (is_employee) {
                        self.update_promise.then(function() {
                            var im = new openerp.im_chat.InstantMessaging(self);
                            openerp.im_chat.single = im;
                            im.appendTo(openerp.client.$el);
                            var button = new openerp.im_chat.ImTopButton(this);
                            button.on("clicked", im, im.switch_display);
                            button.appendTo(window.$('.oe_systray'));
                        });
                    }
                });
                return this._super.apply(this, arguments);
            },
        });
    }

    return im_chat;
})();
