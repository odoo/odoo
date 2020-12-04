odoo.define('website_livechat.livechat_request', function (require) {
"use strict";

var utils = require('web.utils');
var session = require('web.session');
var LivechatButton = require('im_livechat.im_livechat').LivechatButton;


LivechatButton.include({

    /**
     * @override
     * This will will correctly format the livechat session cookie
     * that comes from server side (and that is not properly formatted)
     * This is used for chat request mechanism, when an operator send a chat request
     * from backend to a website visitor.
     */
    willStart: function () {
        var self = this;
        var cookie = utils.get_cookie('im_livechat_session');
        var ready;
        if (cookie) {
            var cleanedLivechatSessionCookie = this.decode_server_cookie(cookie);
            utils.set_cookie('im_livechat_session', cleanedLivechatSessionCookie, 60*60);
        }
        return this._super();
    },
	
	/**
     * @override
     * opening a longpolling to listen message post from backend
	*/
	start: function () {
        this._super();
		this.call('bus_service', 'addChannel', utils.get_cookie('visitor_uuid'));
		this.call('bus_service', 'startPolling');
    },
	
	_openlivechatImmediate: function (notification) {
		self = this 
		var channel = notification[0];
		var cookie_info = notification[1];
		if (channel === utils.get_cookie('visitor_uuid')){
			this._messages = [];
			utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(cookie_info)), 60*60*24);
			this.willStart().then(function () {
             if (self._history) {
            _.each(self._history.reverse(), self._addMessage.bind(self));
            self._openChat();
        }});
	};

	},
	
    _onNotification: function (notifications) {
        var self = this;
        _.each(notifications, function (notification) {
		self._openlivechatImmediate(notification);
        });
		this._super(notifications);
		},
    /**
     * @override
     * Called when the visitor closes the livechat chatter
     * (no matter the way : close, send feedback, ..)
     * this will deactivate the mail_channel, clean the chat request if any
     * and allow the operators to send the visitor a new chat request
     */
    _closeChat: function () {
        var self = this;
        var cookie = utils.get_cookie('im_livechat_session');
        if (cookie) {
            var channel = JSON.parse(cookie);
            var ready = session.rpc('/im_livechat/visitor_leave_session', {uuid: channel.uuid});
            ready.then(self._super());
        }
        else {
            this._super();
        }
    },

    /**
    * Utils to correctly re-encode json string sent by server.
    * Copied from StackOverflow.
    */
    decode_server_cookie: function (val) {
        if (val.indexOf('\\') === -1) {
            return val;  // not encoded
        }
        val = val.slice(1, -1).replace(/\\"/g, '"');
        val = val.replace(/\\(\d{3})/g, function(match, octal) {
            return String.fromCharCode(parseInt(octal, 8));
        });
        return val.replace(/\\\\/g, '\\');
    },
});

return {
    LivechatButton: LivechatButton,
};

});
