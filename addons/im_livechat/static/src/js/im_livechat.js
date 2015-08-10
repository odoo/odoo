odoo.define('im_livechat.im_livechat', function (require) {
"use strict";

var bus = require('bus.bus');
var core = require('web.core');
var user_session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var Widget = require('web.Widget');
var im_chat_common = require('mail.chat_common');

var _t = core._t;
var QWeb = core.qweb;


var COOKIE_NAME = 'livechat_conversation';

/*
The state of anonymous session is hold by the client and not the server.
Override the method managing the state of normal conversation.
*/
im_chat_common.Conversation.include({
    init: function(){
        this._super.apply(this, arguments);
        this.shown = true;
        this.feedback = false;
    },
    show: function(){
        this._super.apply(this, arguments);
        this.shown = true;
    },
    hide: function(){
        this._super.apply(this, arguments);
        this.shown = false;
    },
    session_update_state: function(state){
        // set manually the new state
        if(state === 'closed'){
            this.destroy();
        }else{
            if(state === 'open'){
                this.show();
            }else{
                if(this.shown){
                    state = 'fold';
                    this.hide();
                }else{
                    state = 'open';
                    this.show();
                }
            }
        }
        // session and cookie update
        this._super(state);
        utils.set_cookie(COOKIE_NAME, JSON.stringify(this.get('session')), 60*60);
    },
    click_close: function(event) {
        if(!this.feedback && (this.get('messages').length > 1)){
            this.feedback = new Feedback(this);
            this.$(".oe_im_chatview_content").empty();
            this.$(".oe_im_chatview_input").prop('disabled', true);
            this.feedback.appendTo( this.$(".oe_im_chatview_content"));
            // bind event to close conversation
            this.feedback.on("feedback_sent", this, this.click_close);
        }else{
            this._super.apply(this, arguments);
            utils.set_cookie(COOKIE_NAME, "", -1);
            utils.set_cookie('im_livechat_auto_popup', JSON.stringify(false), 60*60);
        }
    },
});

// To avoid exeption when the anonymous has close his
// conversation and when operator send him a message.
im_chat_common.ConversationManager.include({
    message_receive: function(message) {
        try{
            this._super(message);
        }catch(e){}
    }
});


var LiveSupport = Widget.extend({
    init: function(server_url, db, channel, options, rule) {
        this._super();
        options = options || {};
        _.defaults(options, {
            buttonText: _t("Chat with one of our collaborators"),
            inputPlaceholder: null,
            defaultMessage: _t("How may I help you?"),
            defaultUsername: _t("Visitor"),
        });
        user_session.setup(server_url, {use_cors: false});
        this.load_template(db, channel, options, rule);
    },
    _get_template_list: function(){
        return ['/im_livechat/static/src/xml/im_livechat.xml', '/im_chat/static/src/xml/im_chat.xml'];
    },
    load_template: function(db, channel, options, rule){
        var self = this;
        // load the qweb templates
        var defs = [];
        var templates = this._get_template_list();
        _.each(templates, function(tmpl){
            defs.push(user_session.rpc('/web/proxy/load', {path: tmpl}).then(function(xml) {
                QWeb.add_template(xml);
            }));
        });
        return $.when.apply($, defs).then(function() {
            self.setup(db, channel, options, rule);
        });
    },
    setup: function(db, channel, options, rule){
        var self = this;
        var cookie = utils.get_cookie(COOKIE_NAME);
        if(cookie){
            self.build_button(channel, options, JSON.parse(cookie), rule);
        }else{
            user_session.rpc("/im_livechat/available", {db: db, channel: channel}).then(function(activated) {
                if(activated){
                    self.build_button(channel, options, false, rule);
                }
            });
        }
    },
    build_button: function(channel, options, session, rule){
        var button = new ChatButton(null, channel, options, session);
        button.appendTo($("body"));
        var auto_popup_cookie = utils.get_cookie('im_livechat_auto_popup') ? JSON.parse(utils.get_cookie('im_livechat_auto_popup')) : true;
        if (rule.action === 'auto_popup' && auto_popup_cookie){
            setTimeout(function() {
                button.click();
            }, rule.auto_popup_timer*1000);
        }
    }
});

var ChatButton = Widget.extend({
    className: "openerp_style oe_chat_button hidden-print",
    events: {
        "click": "click"
    },
    init: function(parent, channel, options, session) {
        this._super(parent);
        this.channel = channel;
        this.options = options;
        this.text = options.buttonText;
        this.session = session || false;
        this.conv = false;
        this.no_session_message = _t("None of our collaborators seems to be available, please try again later.");
    },
    start: function() {
        this.$().append(QWeb.render("im_livechat.chatButton", {widget: this}));
        // set up the manager
        this.manager = new im_chat_common.ConversationManager(this, this.options);
        this.manager.set("bottom_offset", $('.oe_chat_button').outerHeight());
        if(this.session){
            this.set_conversation(this.session);
        }
    },
    click: function() {
        var self = this;
        if (!this.conv){
            user_session.rpc("/im_livechat/get_session", {
                "channel_id" : self.channel,
                "anonymous_name" : this.options.defaultUsername
            }, {shadow: true}).then(function(session) {
                if (! session) {
                    alert(self.no_session_message);
                    return;
                }
                session.state = 'open';
                // save the session in a cookie
                utils.set_cookie(COOKIE_NAME, JSON.stringify(session), 60*60);
                // create the conversation with the received session
                self.set_conversation(session, true);
            });
        }
    },
    set_conversation: function(session, welcome_message){
        var self = this;
        this.session = session;
        if(session.state === 'closed'){
            return;
        }
        this.conv = this.manager.session_apply(session);
        this.conv.on("destroyed", this, function() {
            bus.bus.stop_polling();
            delete self.conv;
            delete self.session;
        });
        // start the polling
        bus.bus.add_channel(session.uuid);
        bus.bus.start_polling();
        // add the automatic welcome message
        if(welcome_message){
            this.send_welcome_message();
        }
    },
    send_welcome_message: function(){
        var self = this;
        if(this.session.users.length > 0){
            if (self.options.defaultMessage) {
                setTimeout(function(){
                    var operator = _.last(_.filter(self.session.users, function(user){return user.is_operator}));
                    self.conv.message_receive({
                        id : 1,
                        type: "message",
                        message: self.options.defaultMessage,
                        create_date: time.datetime_to_str(new Date()),
                        from_id: [operator.id, operator.name],
                        to_id: [0, self.session.uuid]
                    });
                }, 1000);
            }
        }
    }
});

/* Rating livechat object */
var Feedback = Widget.extend({
    template : "im_livechat.feedback",
    init: function(parent){
        this._super(parent);
        this.conversation = parent;
        this.reason = false;
        this.rating = false;
        this.server_origin = user_session.origin;
    },
    start: function(){
        this._super.apply(this.arguments);
        // bind events
        this.$('.oe_livechat_rating_choices img').on('click', _.bind(this.click_smiley, this));
        this.$('#rating_submit').on('click', _.bind(this.click_send, this));
    },
    click_smiley: function(ev){
        var self = this;
        this.rating = parseInt($(ev.currentTarget).data('value'));
        this.$('.oe_livechat_rating_choices img').removeClass('selected');
        this.$('.oe_livechat_rating_choices img[data-value="'+this.rating+'"]').addClass('selected');
        // only display textearea if bad smiley selected
        var close_conv = false;
        if(this.rating === 0){
            this.$('.oe_livechat_rating_reason').show();
        }else{
            this.$('.oe_livechat_rating_reason').hide();
            close_conv = true;
        }
        this._send_feedback(close_conv).then(function(){
            self.$('textarea').val(''); // empty the reason each time a click on a smiley is done
        });
    },
    click_send: function(ev){
        this.reason = this.$('textarea').val();
        if(_.contains([0,5,10], this.rating)){ // need to use contains, since the rating can 0, evaluate to false
            this._send_feedback(true);
        }
    },
    _send_feedback: function(close){
        var self = this;
        var uuid = this.conversation.get('session').uuid;
        return user_session.rpc('/rating/livechat/feedback', {uuid: uuid, rate: this.rating, reason : this.reason}).then(function(res) {
            if(close){
                self.trigger("feedback_sent"); // will close the conversation
                    self.conversation.message_send(_.str.sprintf(_t("I rated you with :rating_%d"), self.rating), "message");
            }
        });
    }
});

return {
    Feedback: Feedback,
    LiveSupport: LiveSupport,
};

});
