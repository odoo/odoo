/*
    This file must compile in EcmaScript 3 and work in IE7.
*/

(function() {

    "use strict";

    var _t = openerp._t;
    var im_livechat = {};
    openerp.im_livechat = im_livechat;
    im_livechat.COOKIE_NAME = 'livechat_conversation';

    /*
    The state of anonymous session is hold by the client and not the server.
    Override the method managing the state of normal conversation.
    */
    openerp.im_chat.Conversation.include({
        init: function(){
            this._super.apply(this, arguments);
            this.shown = true;
            this.loading_history = true; // since the session is kept after a refresh, anonymous can reload their history
        },
        show: function(){
            this._super.apply(this, arguments);
            this.shown = true;
        },
        hide: function(){
            this._super.apply(this, arguments);
            this.shown = false;
        },
        update_fold_state: function(state){
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
            var session = this.get('session');
            session.state = state;
            this.set('session', session);
            openerp.set_cookie(im_livechat.COOKIE_NAME, JSON.stringify(session), 60*60);
        },
        click_close: function(e) {
            this._super(e);
            openerp.set_cookie(im_livechat.COOKIE_NAME, "", -1);
        },
    });

    // To avoid exeption when the anonymous has close his
    // conversation and when operator send him a message.
    openerp.im_chat.ConversationManager.include({
        received_message: function(message) {
            try{
                this._super(message);
            }catch(e){}
        }
    });

    // TODO move this to openerpframework.js, ask xmo
    openerp.set_cookie = function(name, value, ttl) {
        ttl = ttl || 24*60*60*365;
        document.cookie = [
            name + '=' + value,
            'path=/',
            'max-age=' + ttl,
            'expires=' + new Date(new Date().getTime() + ttl*1000).toGMTString()
        ].join(';');
    };

    im_livechat.LiveSupport = openerp.Widget.extend({
        init: function(server_url, db, channel, options) {
            var self = this;
            options = options || {};
            _.defaults(options, {
                buttonText: _t("Chat with one of our collaborators"),
                inputPlaceholder: null,
                defaultMessage: _t("How may I help you?"),
                defaultUsername: _t("Visitor"),
            });
            openerp.session = new openerp.Session(null, server_url, { use_cors: false });
            // load the qweb templates
            var defs = [];
            var templates = ['/im_livechat/static/src/xml/im_livechat.xml', '/im_chat/static/src/xml/im_chat.xml'];
            _.each(templates, function(tmpl){
                defs.push(openerp.session.rpc('/web/proxy/load', {path: tmpl}).then(function(xml) {
                    openerp.qweb.add_template(xml);
                }));
            });
            return $.when.apply($, defs).then(function() {
                self.setup(db, channel, options);
            });
        },
        setup: function(db, channel, options){
            var self = this;
            var session = openerp.get_cookie(im_livechat.COOKIE_NAME);
            if(session){
                self.build_button(channel, options, JSON.parse(session));
            }else{
                openerp.session.rpc("/im_livechat/available", {db: db, channel: channel}).then(function(activated) {
                    if(activated){
                        self.build_button(channel, options);
                    }
                });
            }
        },
        build_button: function(channel, options, session){
            var button = new im_livechat.ChatButton(null, channel, options, session);
            button.appendTo($("body"));
            if (options.auto){
                button.click();
            }
        }
    });

    im_livechat.ChatButton = openerp.Widget.extend({
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
            this.$().append(openerp.qweb.render("chatButton", {widget: this}));
            // set up the manager
            this.manager = new openerp.im_chat.ConversationManager(this, this.options);
            this.manager.set("bottom_offset", $('.oe_chat_button').outerHeight());
            this.manager.notification = function(notif){ // override the notification default function
                alert(notif);
            }
            if(this.session){
                this.set_conversation(this.session);
            }
        },
        click: function() {
            var self = this;
            if (!this.conv){
                openerp.session.rpc("/im_livechat/get_session", {"channel_id" : self.channel, "anonymous_name" : this.options["defaultUsername"]}, {shadow: true}).then(function(session) {
                    if (! session) {
                        self.manager.notification(self.no_session_message);
                        return;
                    }
                    session.state = 'open';
                    // save the session in a cookie
                    openerp.set_cookie(im_livechat.COOKIE_NAME, JSON.stringify(session), 60*60);
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
            this.conv = this.manager.apply_session(session);
            this.conv.on("destroyed", this, function() {
                openerp.bus.bus.stop_polling();
                delete self.conv;
                delete self.session;
            });
            // start the polling
            openerp.bus.bus.add_channel(session.uuid);
            openerp.bus.bus.start_polling();
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
                        self.conv.received_message({
                            id : 1,
                            type: "message",
                            message: self.options.defaultMessage,
                            create_date: openerp.datetime_to_str(new Date()),
                            from_id: [self.session.users[0].id, self.session.users[0].name],
                            to_id: [0, self.session.uuid]
                        });
                    }, 1000);
                }
            }
        }
    });

    return im_livechat;

})();
