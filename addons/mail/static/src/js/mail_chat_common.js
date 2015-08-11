odoo.define('mail.chat_common', function (require) {
"use strict";

var bus = require('bus.bus');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var Widget = require('web.Widget');
var mail_utils = require('mail.utils');

var _t = core._t;
var QWeb = core.qweb;

var NBR_LIMIT_HISTORY = 20;


/**
 * Widget handeling the sessions/conversations
 *
 * Responsible to listen the bus and do the correct action according to the received notifications (fetch
 * conversation, add message, ...)
 **/
var ConversationManager = Widget.extend({
    init: function(parent, options) {
        var self = this;
        this._super(parent);
        this.options = _.clone(options) || {};
        _.defaults(this.options, {
            placeholder: _t("Say something..."),
            default_username: _t("Visitor"),
            load_history: true,
            focus: false,
        });
        this.emoji_list = [];
        // business
        this.sessions = {};
        this.bus = bus.bus;
        this.bus.on("notification", this, this.on_notification);
        // ui
        this.set("right_offset", 0);
        this.set("bottom_offset", 0);
        this.on("change:right_offset", this, this.calc_positions);
        this.on("change:bottom_offset", this, this.calc_positions);

        this.set("waiting_messages", 0);
        this.on("change:waiting_messages", this, this.window_title_change);
        $(window).on("focus", _.bind(this.window_focus, this));
        this.window_title_change();
        // session widgets deferred (for their creation)
        this._session_defs = {};
    },
    start: function(){
        var self = this;
        return $.when(session.rpc("/mail/chat_init"), this._super.apply(this, arguments)).then(function(result){
            self._setup(result);
        });
    },
    _setup: function(init_data){
        this.emoji_list = init_data['emoji'];
        this.options['emoji'] = mail_utils.shortcode_substitution(init_data['emoji']);
    },
    on_notification: function(notification, options) {
        var self = this;
        var channel = notification[0];
        var message = notification[1];
        var regex_uuid = new RegExp(/(\w{8}(-\w{4}){3}-\w{12}?)/g);
        var is_channel_uuid = regex_uuid.test(channel);

        // (dbname, 'res.partner', partner_id) receive only the new mail.channel header
        if((Array.isArray(channel) && (channel[1] === 'res.partner')) || is_channel_uuid){
            // activate the received session
            if(message.uuid){
                this.session_apply(message, options);
            }
        }
        // (dbname, 'mail.channel', channel_id) receive only the mail.message of the channel
        if((Array.isArray(channel) && (channel[1] === 'mail.channel')) || is_channel_uuid){
            // message to display in the chatview
            if (message.message_type) {
                self.message_receive(message);
            }
        }
    },
    // window focus unfocus beep and title
    window_focus: function() {
        this.set("waiting_messages", 0);
    },
    window_beep: function() {
        mail_utils.beep(session);
    },
    window_title_change: function() {
        var title = undefined;
        if (this.get("waiting_messages") !== 0) {
            this.window_beep();
        }
    },
    // sessions methods
    session_apply: function(session, options){
        // options used by this function : focus (load_history can be usefull)
        var self = this;
        options = _.defaults(options || {}, {
            'focus': true,
        }, this.options);
        // create/get the conversation widget
        var conv = this.sessions[session.id];
        if (! conv) {
            if(session.state !== 'closed'){
                conv = new Conversation(this, session, options);
                // store this deferred to apply next action (notifications) when it is resolved.
                this._session_defs[session.id] = conv.appendTo($("body"));
                this._session_defs[session.id].then(function() {
                    self.calc_positions();
                });
                conv.on("destroyed", this, _.bind(this.session_delete, this));
                this.sessions[session.id] = conv;
            }
        }else{
            // update the state only when the 'contruction' deferred is resolved.
            this._session_defs[session.id].then(function(){
                conv.set('session', session);
            });
        }
        return conv;
    },
    session_delete: function(channel_id){
        delete this.sessions[channel_id];
        this.calc_positions();
    },
    /**
     * Adding a message in all its channels
     * /!\ Suppose the channel are already loaded in the ConversationManager /!\
     * @param {Object} message : the received message (formatted server side)
     */
    message_receive: function(message){
        var self = this;
        _.each(message.channel_ids, function(channel_id){
            self.sessions[channel_id].message_receive(message);
        });
    },
    // others
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
        $(window).off("focus", this.window_focus);
        $(window).off("blur", this.window_blur);
        return this._super();
    }
});

/**
 * Widget Conversation
 *
 * Display the conversation in a 'portable' window, manage sending and receiving message,
 * and the fold state of the conversation.
 **/
var Conversation = Widget.extend({
    template: "mail.chat.im.Conversation",
    events: {
        "keydown input": "keydown",
        "click .o_mail_chat_im_window_close": "on_click_close",
        "click .o_mail_chat_im_window_header": "on_click_header"
    },
    init: function(parent, session, options) {
        this._super(parent);
        this.options = _.defaults(options || {}, {
            'emoji': {},
            'placeholder': _t('Write something ...'),
            'loading_history': true,
            'focus': true,
        });
        this.set("messages", []);
        this.set("session", session);
        this.set("pending", 0);
        this.set("right_position", 0);
        this.set("bottom_position", 0);
    },
    willStart: function(){
        if(this.options.loading_history){
            return $.when(this.message_history(), this._super.apply(this, arguments));
        }
        return this._super.apply(this, arguments);
    },
    start: function() {
        var self = this;
        // ui
        self.on("change:right_position", self, self.calc_pos);
        self.on("change:bottom_position", self, self.calc_pos);
        self.on("change:pending", self, self.message_pending_change);

        self.full_height = self.$().height();
        self.$('.o_mail_chat_im_window_content').on('scroll',function(){
            if($(this).scrollTop() === 0){
                self.message_history();
            }
        });
        // business
        self.on("change:session", self, self.session_change);
        self.on("change:messages", self, self.message_render);

        return self._super.apply(this, arguments).then(function(){
            // place the conversation window correctly on the screen
            self.calc_pos();
            // focus if needed
            if(self.options.focus){
                self.focus();
            }
            // re-apply the session to display the correct state
            self.set('session', _.clone(self.get('session')));
            self._go_bottom();
        });
    },
    // ui
    show: function(){
        this.$().animate({
            height: this.full_height
        });
        this.set("pending", 0);
    },
    hide: function(){
        this.$().animate({
            height: this.$(".o_mail_chat_im_window_header").outerHeight()
        });
    },
    calc_pos: function() {
        this.$().css("right", this.get("right_position"));
        this.$().css("bottom", this.get("bottom_position"));
    },
    // session
    /**
     * Set the fold state LOCALLY for the session. This will
     * trigger a ui update
     * @param {string} state : the fold state ('fold', 'closed' or 'open')
     */
    session_fold: function(state){
        var session = this.get('session');
        session.state = state;
        this.set('session', session);
    },
    /**
     * Triggered when the session has changed : it update the header name
     * and fold the window (ui) according to its state.
     */
    session_change: function(){
        // update conversation name in header
        var name = this.get("session").name || _t('Unknown Channel');
        this.$(".o_mail_chat_im_window_header_name").text(name);
        this.$(".o_mail_chat_im_window_header_name").attr('title', name);
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
    // messages
    /**
     * Load the history of the current session, and insert it into already loaded messages
     * @returns {Deferred} resolved with the new loaded messages (Object[])
     */
    message_history: function(){
        var self = this;
        if(this.options.loading_history){
            var data = {
                uuid: self.get("session").uuid,
                limit: NBR_LIMIT_HISTORY,
                last_id: _.first(this.get("messages")) ? _.first(this.get("messages")).id : false,
            };
            return session.rpc("/mail/chat_history", data).then(function(messages){
                if(messages){
                    self.message_insert(messages);
                    if(messages.length != NBR_LIMIT_HISTORY){
                        self.options.loading_history = false;
                    }
                }else{
                    self.options.loading_history = false;
                }
                return messages;
            });
        }
        return $.Deferred().resolve([]);
    },
    message_receive: function(message) {
        // don't add duplicated message (this can happen when refreshing and receiving already recieved
        // message that are still in the bus queue/buffer).
        if(!_.contains(_.pluck(this.get('messages'), 'id'), message.id)){
            // is pending message ?
            if (this.get('session').state === 'open') {
                this.set("pending", 0);
            } else {
                if(!this.message_am_i_author(message)){
                    this.set("pending", this.get("pending") + 1);
                }
            }
            // insert it
            this.message_insert([message]);
            this._go_bottom();
        }
    },
    message_send: function(message) {
        var self = this;
        var send_it = function() {
            return session.rpc("/mail/chat_post", {uuid: self.get("session").uuid, message_content: message});
        };
        var tries = 0;
        send_it().fail(function(error, e) {
            e.preventDefault();
            tries += 1;
            if (tries < 3)
                return send_it();
        });
    },
    /**
     * Preporcess the message (add informations in the Object, ...)
     * @param {Object[]} messages : server side formatted message (from message_format method)
     */
    _message_preprocess: function(raw_messages){
        var self = this;
        _.each(raw_messages, function(m){
            m.date = moment(time.str_to_datetime(m.date)).format('YYYY-MM-DD HH:mm:ss'); // set the date in the correct browser user timezone
            if(m.body){
                m.body = mail_utils.shortcode_apply(m.body, self.options.emoji);
            }
            _.each(m.attachment_ids, function(a){
                a.url = mail_utils.get_attachment_url(session, m.id, a.id);
                a.fa_class = mail_utils.attachment_filetype_to_fa_class(a.file_type_icon);
            });
        });
        return raw_messages;
    },
    /**
     * Insert new raw message into the current ones
     * @param {Object[]} messages : server side formatted message (from message_format method)
     */
    message_insert: function(raw_messages){
        var messages = this._message_preprocess(raw_messages);
        this.set("messages", _.sortBy(this.get("messages").concat(messages), function(m){ return m.id; }));
    },
    message_render: function(){
        var self = this;
        var message_html = $(QWeb.render("mail.chat.im.Conversation.messages", {"widget": this}));
        this.$('.o_mail_chat_im_window_content').html(message_html);
    },
    message_am_i_author: function(message){
        return message.author_id && message.author_id[0] === session.partner_id;
    },
    message_pending_change: function(event){
        if (this.get("pending") === 0) {
            this.$(".o_mail_chat_im_window_header_counter").text("");
        } else {
            this.$(".o_mail_chat_im_window_header_counter").text("(" + this.get("pending") + ")");
        }
    },
    // utils and event
    _go_bottom: function() {
        if(this.$(".o_mail_chat_im_window_content").length){
            this.$(".o_mail_chat_im_window_content").scrollTop(this.$(".o_mail_chat_im_window_content").get(0).scrollHeight);
        }
    },
    focus: function() {
        this.$(".o_mail_chat_im_window_input").focus();
    },
    keydown: function(e) {
        if(e && e.which == 27) {
            if(this.$el.prev().find('.o_mail_chat_im_window_input').length > 0){
                this.$el.prev().find('.o_mail_chat_im_window_input').focus();
            }else{
                this.$el.next().find('.o_mail_chat_im_window_input').focus();
            }
            e.stopPropagation();
            this.session_fold('closed');
        }
        if(e && e.which !== 13) {
            return;
        }
        var mes = this.$("input").val();
        if (! mes.trim()) {
            return;
        }
        this.$("input").val("");
        this.message_send(mes);
    },
    on_click_header: function(event){
        this.session_fold();
    },
    on_click_close: function(event) {
        event.stopPropagation(); // avoid triggering event for 'on_click_header'
        this.session_fold('closed');
    },
    destroy: function() {
        this.trigger("destroyed", this.get('session').id);
        return this._super();
    }
});


return {
    Conversation: Conversation,
    ConversationManager: ConversationManager,
};

});
