/*
    This file must compile in EcmaScript 3 and work in IE7.
*/

(function() {

    "use strict";

    var _t = openerp._t;

    var im_livechat = {};
    openerp.im_livechat = im_livechat;

    /*
    The state of anonymous session is hold by the client and not the server.
    Override the method managing the state of normal conversation.
    */
    openerp.im_chat.Conversation.include({
        init: function(){
            this._super.apply(this, arguments);
            this.shown = true;
            this.loading_history = false; // unactivate the loading history
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
        },
    });

    im_livechat.LiveSupport = openerp.Widget.extend({
        init: function(server_url, db, channel, options) {
            options = options || {};
            _.defaults(options, {
                buttonText: _t("Chat with one of our collaborators"),
                inputPlaceholder: null,
                defaultMessage: _t("How may I help you?"),
                defaultUsername: _t("Anonymous"),
            });
            openerp.session = new openerp.Session();

            // load the qweb templates
            var defs = [];
            var templates = ['/im_livechat/static/src/xml/im_livechat.xml','/im_chat/static/src/xml/im_chat.xml'];
            _.each(templates, function(tmpl){
                defs.push(openerp.session.rpc('/web/proxy/load', {path: tmpl}).then(function(xml) {
                    openerp.qweb.add_template(xml);
                }));
            });
            return $.when.apply($, defs).then(function() {
                return openerp.session.rpc("/im_livechat/available", {db: db, channel: channel}).then(function(activated) {
                    if(activated){
                        var button = new im_livechat.ChatButton(null, channel, options);
                        button.appendTo($("body"));
                        if (options.auto){
                            button.click();
                        }
                    }
                });
            });
        },
    });

    im_livechat.ChatButton = openerp.Widget.extend({
        className: "openerp_style oe_chat_button",
        events: {
            "click": "click"
        },
        init: function(parent, channel, options) {
            this._super(parent);
            this.channel = channel;
            this.options = options;
            this.text = options.buttonText;
        },
        start: function() {
            this.$().append(openerp.qweb.render("chatButton", {widget: this}));
        },
        click: function() {
            if (! this.manager) {
                this.manager = new openerp.im_chat.ConversationManager(this, this.options);
                this.manager.set("bottom_offset", $('.oe_chat_button').outerHeight()); // TODO correct the value (no hardcode damned !)
                // override the notification default function
                this.manager.notification = function(notif){
                    alert(notif);
                }
            }
            return this.chat();
        },
        chat: function() {
            var self = this;
            if (_.keys(this.manager.sessions).length > 0)
                return;

            openerp.session.rpc("/im_livechat/get_session", {"channel_id" : self.channel, "anonymous_name" : this.options["defaultUsername"]}, {shadow: true}).then(function(session) {
                if (! session) {
                    self.manager.notification(_t("None of our collaborators seems to be available, please try again later."));
                    return;
                }
                var conv = self.manager.activate_session(session, [], true);
                // start the polling
                openerp.bus.bus.add_channel(session.uuid);
                openerp.bus.bus.start_polling();
                // add the automatic welcome message
                if(session.users.length > 0){
                    if (self.options.defaultMessage) {
                        setTimeout(function(){
                            conv.received_message({
                                id : 1,
                                type: "message",
                                message: self.options.defaultMessage,
                                create_date: openerp.datetime_to_str(new Date()),
                                from_id: [session.users[0].id, session.users[0].name],
                                to_id: [0, session.uuid]
                            });
                        }, 1000);
                    }
                }
            });
        }
    });

    return im_livechat;

})();
