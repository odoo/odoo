odoo.define('im_livechat.im_livechat', function (require) {
"use strict";

var bus = require('bus.bus');
var core = require('web.core');
var user_session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var Widget = require('web.Widget');
var mail_chat_common = require('mail.chat_common');

var _t = core._t;
var QWeb = core.qweb;


/*
 * Conversation Patch
 *
 * The state of anonymous session is hold by the client and not the
 * server. Override the method managing the state of normal conversation.
*/
mail_chat_common.Conversation.include({
    init: function(parent, session, options){
        this._super.apply(this, arguments);
        this.shown = true;
        this.feedback = false;
        this.options.default_username = session.anonymous_name || this.options.default_username;
    },
    show: function(){
        this._super.apply(this, arguments);
        this.shown = true;
    },
    hide: function(){
        this._super.apply(this, arguments);
        this.shown = false;
    },
    session_fold: function(state){
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
            // session and cookie update
            utils.set_cookie('im_livechat_session', JSON.stringify(this.get('session')), 60*60);
        }
        this._super(state);
    },
    on_click_close: function(event) {
        var self = this;
        event.stopPropagation();
        if(!this.feedback && (this.get('messages').length > 1)){
            this.feedback = new Feedback(this);
            this.$(".o_mail_chat_im_window_content").empty();
            this.$(".o_mail_chat_im_window_input").prop('disabled', true);
            this.feedback.appendTo(this.$(".o_mail_chat_im_window_content"));
            // bind event to close conversation
            var args = arguments;
            var _super = this._super;
            this.feedback.on("feedback_sent", this, function(){
                _super.apply(self, args);
            });
        }else{
            this._super.apply(this, arguments);
        }
    },
});

/*
 * Livechat Conversation Manager
 *
 * To avoid exeption when the anonymous has close his conversation and when operator send
 * him a message. Extending ConversationManager is better than monkey-patching it.
 */
var LivechatConversationManager = mail_chat_common.ConversationManager.extend({
    message_receive: function(message) {
        try{
            this._super(message);
        }catch(e){}
    }
});

/**
 * Livechat Button
 *
 * This widget is the Button to start a conversation with an operator on the livechat channel
 * (defined in options.channel_id). This will auto-popup if the rule say so, create the conversation
 * window if a session is saved in a cookie, ...
 */
var LivechatButton = Widget.extend({
    template: 'im_livechat.LivechatButton',
    events: {
        "click": "on_click"
    },
    init: function(parent, server_url, options, rule) {
        this._super.apply(this, arguments);
        this.server_url = server_url;
        this.options = _.defaults(options || {}, {
            placeholder: _t('Ask something ...'),
            default_username: _t("Visitor"),
            button_text: _t("Chat with one of our collaborators"),
            default_message: _t("How may I help you?"),
        });
        this.rule = rule || false;
        this.mail_channel = false;
    },
    willStart: function(){
        return $.when(this.load_qweb_template(), this._super());
    },
    start: function(){
        var self = this;
        return this._super.apply(this, arguments).then(function(){
            // set up the manager
            self.manager = new LivechatConversationManager(self, self.options);
            self.manager.set("bottom_offset", self.$el.outerHeight());
            // check if a session already exists in a cookie
            var cookie = utils.get_cookie('im_livechat_session');
            if(cookie){
                self.set_conversation(JSON.parse(cookie), false);
            }else{ // if not session, apply the rule
                var auto_popup_cookie = utils.get_cookie('im_livechat_auto_popup') ? JSON.parse(utils.get_cookie('im_livechat_auto_popup')) : true;
                self.auto_popup_cookie = auto_popup_cookie;
                if (self.rule.action === 'auto_popup' && auto_popup_cookie){
                    setTimeout(function() {
                        self.on_click();
                    }, self.rule.auto_popup_timer*1000);
                }
            }
        });
    },
    load_qweb_template: function(){
        var self = this;
        var defs = [];
        var templates = ['/mail/static/src/xml/mail_chat_common.xml', '/im_livechat/static/src/xml/im_livechat.xml'];
        _.each(templates, function(tmpl){
            defs.push(user_session.rpc('/web/proxy/load', {path: tmpl}).then(function(xml) {
                QWeb.add_template(xml);
            }));
        });
        return $.when.apply($, defs);
    },
    load_mail_channel: function(display_warning){
        var self = this;
        return user_session.rpc('/im_livechat/get_session', {
            "channel_id" : this.options.channel_id,
            "anonymous_name" : this.options.default_username,
        }, {shadow: true}).then(function(channel){
            if(channel){
                self.set_conversation(channel, true);
            }else{
                if(display_warning){
                    self.alert_available_message();
                }
            }
        });
    },
    on_click: function(event){
        var self = this;
        if(!this.mail_channel){
            this.load_mail_channel(event !== undefined);
        }
    },
    set_conversation: function(mail_channel, welcome_message){
        var self = this;
        // set the mail_channel and create the Conversation Window
        this.mail_channel = mail_channel;
        this.conv = this.manager.session_apply(mail_channel, {
            'load_history': !welcome_message,
            'focus': welcome_message
        });
        this.conv.on("destroyed", this, function() {
            bus.bus.stop_polling();
            delete self.conv;
            delete self.mail_channel;
            utils.set_cookie('im_livechat_session', "", -1); // delete the session cookie
        });
        // setup complet when the conversation window is appended
        this.manager._session_defs[mail_channel.id].then(function(){
            // start the polling
            bus.bus.add_channel(mail_channel.uuid);
            bus.bus.start_polling();
            // add the automatic welcome message
            if(welcome_message){
                self.send_welcome_message();
            }
            // create the cookies
            utils.set_cookie('im_livechat_auto_popup', JSON.stringify(false), 60*60);
            utils.set_cookie('im_livechat_session', JSON.stringify(mail_channel), 60*60);
        })
    },
    send_welcome_message: function(){
        var self = this;
        if(this.mail_channel.operator_pid && this.options.default_message) {
            setTimeout(function(){
                self.conv.message_receive({
                    id : 1,
                    message_type: "comment",
                    model: 'mail.channel',
                    body: self.options.default_message,
                    date: time.datetime_to_str(new Date()),
                    author_id: self.mail_channel.operator_pid,
                    channel_ids: [self.mail_channel.id],
                    tracking_value_ids: [],
                    attachment_ids: [],
                });
            }, 1000);
        }
    },
    alert_available_message: function(){
        alert(_t("None of our collaborators seems to be available, please try again later."));
    },
})

/*
 * Rating for Livechat
 *
 * This widget display the 3 rating smileys, and a textarea to add a reason (only for red
 * smileys), and sent the user feedback to the server.
 */
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
        this.$('.o_livechat_rating_choices img').on('click', _.bind(this.click_smiley, this));
        this.$('#rating_submit').on('click', _.bind(this.click_send, this));
    },
    click_smiley: function(ev){
        var self = this;
        this.rating = parseInt($(ev.currentTarget).data('value'));
        this.$('.o_livechat_rating_choices img').removeClass('selected');
        this.$('.o_livechat_rating_choices img[data-value="'+this.rating+'"]').addClass('selected');
        // only display textearea if bad smiley selected
        var close_conv = false;
        if(this.rating === 0){
            this.$('.o_livechat_rating_reason').show();
        }else{
            this.$('.o_livechat_rating_reason').hide();
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
        return user_session.rpc('/im_livechat/feedback', {uuid: uuid, rate: this.rating, reason : this.reason}).then(function(res) {
            if(close){
                self.trigger("feedback_sent"); // will close the conversation
                    self.conversation.message_send(_.str.sprintf(_t("I rated you with :rating_%d"), self.rating), "message");
            }
        });
    }
});

return {
    Feedback: Feedback,
    LivechatButton: LivechatButton,
};

});
