odoo.define('im_livechat.im_livechat', function (require) {
"use strict";

require('bus.BusService');
var concurrency = require('web.concurrency');
var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var Widget = require('web.Widget');

var WebsiteLivechat = require('im_livechat.model.WebsiteLivechat');
var WebsiteLivechatMessage = require('im_livechat.model.WebsiteLivechatMessage');
var WebsiteLivechatWindow = require('im_livechat.WebsiteLivechatWindow');

var _t = core._t;
var QWeb = core.qweb;

// Constants
var LIVECHAT_COOKIE_HISTORY = 'im_livechat_history';
var HISTORY_LIMIT = 15;

var RATING_TO_EMOJI = {
    "10":"😊",
    "5":"😐",
    "1":"😞"
};

// History tracking
var page = window.location.href.replace(/^.*\/\/[^/]+/, '');
var pageHistory = utils.get_cookie(LIVECHAT_COOKIE_HISTORY);
var urlHistory = [];
if (pageHistory) {
    urlHistory = JSON.parse(pageHistory) || [];
}
if (!_.contains(urlHistory, page)) {
    urlHistory.push(page);
    while (urlHistory.length > HISTORY_LIMIT) {
        urlHistory.shift();
    }
    utils.set_cookie(LIVECHAT_COOKIE_HISTORY, JSON.stringify(urlHistory), 60*60*24); // 1 day cookie
}

var LivechatButton = Widget.extend({
    className:'openerp o_livechat_button d-print-none',
    custom_events: {
        'close_chat_window': '_onCloseChatWindow',
        'post_message_chat_window': '_onPostMessageChatWindow',
        'save_chat_window': '_onSaveChatWindow',
        'updated_typing_partners': '_onUpdatedTypingPartners',
        'updated_unread_counter': '_onUpdatedUnreadCounter',
    },
    events: {
        'click': '_openChat'
    },
    init: function (parent, serverURL, options) {
        this._super(parent);
        this.options = _.defaults(options || {}, {
            input_placeholder: _t("Ask something ..."),
            default_username: _t("Visitor"),
            button_text: _t("Chat with one of our collaborators"),
            default_message: _t("How may I help you?"),
        });

        this._history = null;
        // livechat model
        this._livechat = null;
        // livechat window
        this._chatWindow = null;
        this._messages = [];
        this._serverURL = serverURL;
    },
    willStart: function () {
        var self = this;
        var cookie = utils.get_cookie('im_livechat_session');
        var ready;
        if (!cookie) {
            ready = session.rpc('/im_livechat/init', {channel_id: this.options.channel_id})
                .then(function (result) {
                    if (!result.available_for_me) {
                        return $.Deferred().reject();
                    }
                    self._rule = result.rule;
                });
        } else {
            var channel = JSON.parse(cookie);
            ready = session.rpc('/mail/chat_history', {uuid: channel.uuid, limit: 100})
                .then(function (history) {
                    self._history = history;
                });
        }
        return ready.then(this._loadQWebTemplate.bind(this));
    },
    start: function () {
        this.$el.text(this.options.button_text);
        if (this._history) {
            _.each(this._history.reverse(), this._addMessage.bind(this));
            this._openChat();
        } else if (!config.device.isMobile && this._rule.action === 'auto_popup') {
            var autoPopupCookie = utils.get_cookie('im_livechat_auto_popup');
            if (!autoPopupCookie || JSON.parse(autoPopupCookie)) {
                this._autoPopupTimeout =
                    setTimeout(this._openChat.bind(this), this._rule.auto_popup_timer*1000);
            }
        }
        this.call('bus_service', 'onNotification', this, this._onNotification);
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------


    /**
     * @private
     * @param {Object} data
     * @param {Object} [options={}]
     */
    _addMessage: function (data, options) {
        options = _.extend({}, this.options, options, {
            serverURL: this._serverURL,
        });
        var message = new WebsiteLivechatMessage(this, data, options);
        if (this._livechat) {
            this._livechat.addMessage(message);
        }

        if (options && options.prepend) {
            this._messages.unshift(message);
        } else {
            this._messages.push(message);
        }
    },
    /**
     * @private
     */
    _askFeedback: function () {
        this._chatWindow.$('.o_thread_composer input').prop('disabled', true);

        var feedback = new Feedback(this, this._livechat);
        this._chatWindow.replaceContentWith(feedback);

        feedback.on('send_message', this, this._sendMessage);
        feedback.on('feedback_sent', this, this._closeChat);
    },
    /**
     * @private
     */
    _closeChat: function () {
        this._chatWindow.destroy();
        utils.set_cookie('im_livechat_session', "", -1); // remove cookie
    },
    /**
     * @private
     * @param {Array} notification
     */
    _handleNotification: function  (notification){
        if (this._livechat && (notification[0] === this._livechat.getUUID())) {
            if (notification[1]._type === 'history_command') { // history request
                var cookie = utils.get_cookie(LIVECHAT_COOKIE_HISTORY);
                var history = cookie ? JSON.parse(cookie) : [];
                session.rpc('/im_livechat/history', {
                    pid: this._livechat.getOperatorPID()[0],
                    channel_uuid: this._livechat.getUUID(),
                    page_history: history,
                });
            } else if (notification[1].info === 'typing_status') {
                var isWebsiteUser = notification[1].is_website_user;
                if (isWebsiteUser) {
                    return; // do not handle typing status notification of myself
                }
                var partnerID = notification[1].partner_id;
                if (notification[1].is_typing) {
                    this._livechat.registerTyping({ partnerID: partnerID });
                } else {
                    this._livechat.unregisterTyping({ partnerID: partnerID });
                }
            } else { // normal message
                this._addMessage(notification[1]);
                this._renderMessages();
                if (this._chatWindow.isFolded() || !this._chatWindow.isAtBottom()) {
                    this._livechat.incrementUnreadCounter();
                }
            }
        }
    },
    /**
     * @private
     */
    _loadQWebTemplate: function () {
        var xml_files = ['/mail/static/src/xml/abstract_thread_window.xml',
                         '/mail/static/src/xml/thread.xml',
                         '/im_livechat/static/src/xml/im_livechat.xml'];
        var defs = _.map(xml_files, function (tmpl) {
            return session.rpc('/web/proxy/load', { path: tmpl }).then(function (xml) {
                QWeb.add_template(xml);
            });
        });
        return $.when.apply($, defs);
    },
    /**
     * @private
     */
    _openChat: _.debounce(function () {
        if (this._openingChat) {
            return;
        }
        var self = this;
        var cookie = utils.get_cookie('im_livechat_session');
        var def;
        this._openingChat = true;
        clearTimeout(this._autoPopupTimeout);
        if (cookie) {
            def = $.when(JSON.parse(cookie));
        } else {
            this._messages = []; // re-initialize messages cache
            def = session.rpc('/im_livechat/get_session', {
                channel_id : this.options.channel_id,
                anonymous_name : this.options.default_username,
            }, {shadow: true});
        }
        def.then(function (livechatData) {
            if (!livechatData || !livechatData.operator_pid) {
                alert(_t("None of our collaborators seems to be available, please try again later."));
            } else {
                self._livechat = new WebsiteLivechat({
                    parent: self,
                    data: livechatData
                });
                self._openChatWindow();
                self._sendWelcomeMessage();
                self._renderMessages();

                self.call('bus_service', 'addChannel', self._livechat.getUUID());
                self.call('bus_service', 'startPolling');

                utils.set_cookie('im_livechat_session', JSON.stringify(self._livechat.toData()), 60*60);
                utils.set_cookie('im_livechat_auto_popup', JSON.stringify(false), 60*60);
            }
        }).always(function () {
            self._openingChat = false;
        });
    }, 200, true),
    /**
     * @private
     */
    _openChatWindow: function () {
        var self = this;
        var options = {
            displayStars: false,
            placeholder: this.options.input_placeholder || "",
        };
        this._chatWindow = new WebsiteLivechatWindow(this, this._livechat, options);
        this._chatWindow.appendTo($('body')).then(function () {
            var cssProps = {bottom: 0};
            cssProps[_t.database.parameters.direction === 'rtl' ? 'left' : 'right'] = 0;
            self._chatWindow.$el.css(cssProps);
            self.$el.hide();
        });
    },
    /**
     * @private
     */
    _renderMessages: function () {
        var shouldScroll = !this._chatWindow.isFolded() && this._chatWindow.isAtBottom();
        this._livechat.setMessages(this._messages);
        this._chatWindow.render();
        if (shouldScroll) {
            this._chatWindow.scrollToBottom();
        }
    },
    /**
     * @private
     * @param {Object} message
     * @return {$.Deferred}
     */
    _sendMessage: function (message) {
        var self = this;
        return session
            .rpc('/mail/chat_post', {uuid: this._livechat.getUUID(), message_content: message.content})
            .then(function () {
                self._chatWindow.scrollToBottom();
            });
    },
    /**
     * @private
     */
    _sendWelcomeMessage: function () {
        if (this.options.default_message) {
            this._addMessage({
                id: '_welcome',
                attachment_ids: [],
                author_id: this._livechat.getOperatorPID(),
                body: this.options.default_message,
                channel_ids: [this._livechat.getID()],
                date: time.datetime_to_str(new Date()),
                tracking_value_ids: [],
            }, {prepend: true});
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onCloseChatWindow: function (ev) {
        ev.stopPropagation();
        var isComposerDisabled = this._chatWindow.$('.o_thread_composer input').prop('disabled');
        var shouldAskFeedback = !isComposerDisabled && _.find(this._messages, function (message) {
            return message.getID() !== '_welcome';
        });
        if (shouldAskFeedback) {
            this._chatWindow.toggleFold(false);
            this._askFeedback();
        } else {
            this._closeChat();
        }
    },
    /**
     * @private
     * @param {Array[]} notifications
     */
    _onNotification: function (notifications) {
        var self = this;
        _.each(notifications, function (notification) {
            self._handleNotification(notification);
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data.messageData
     */
    _onPostMessageChatWindow: function (ev) {
        ev.stopPropagation();
        var self = this;
        var messageData = ev.data.messageData;
        this._sendMessage(messageData).fail(function (error, e) {
            e.preventDefault();
            return self._sendMessage(messageData); // try again just in case
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSaveChatWindow: function (ev) {
        ev.stopPropagation();
        utils.set_cookie('im_livechat_session', JSON.stringify(this._livechat.toData()), 60*60);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedTypingPartners: function (ev) {
        ev.stopPropagation();
        this._chatWindow.renderTypingNotificationBar();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedUnreadCounter: function (ev) {
        ev.stopPropagation();
        this._chatWindow.renderHeader();
    },
});

/*
 * Rating for Livechat
 *
 * This widget displays the 3 rating smileys, and a textarea to add a reason
 * (only for red smiley), and sends the user feedback to the server.
 */
var Feedback = Widget.extend({
    template: 'im_livechat.FeedBack',

    events: {
        'click .o_livechat_rating_choices img': '_onClickSmiley',
        'click .o_livechat_no_feedback span': '_onClickNoFeedback',
        'click .o_rating_submit_button': '_onClickSend',
    },

    /**
     * @param {?} parent
     * @param {im_livechat.model.WebsiteLivechat} livechat
     */
    init: function (parent, livechat) {
        this._super(parent);
        this._livechat = livechat;
        this.server_origin = session.origin;
        this.rating = undefined;
        this.dp = new concurrency.DropPrevious();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} options
     */
    _sendFeedback: function (options) {
        var self = this;
        var args = {
            uuid: this._livechat.getUUID(),
            rate: this.rating,
            reason : options.reason
        };
        this.dp.add(session.rpc('/im_livechat/feedback', args)).then(function () {
            if (options.close) {
                var emoji = RATING_TO_EMOJI[self.rating] || "??" ;
                var content = _.str.sprintf(_t("Rating: %s"), emoji);
                if (options.reason) {
                    content += " \n" + options.reason;
                }
                self.trigger('send_message', { content: content });
                self.trigger('feedback_sent'); // will close the chat
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickNoFeedback: function () {
        this.trigger('feedback_sent'); // will close the chat
    },
    /**
     * @private
     */
    _onClickSend: function () {
        if (_.isNumber(this.rating)) {
            this._sendFeedback({ reason: this.$('textarea').val(), close: true });
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSmiley: function (ev) {
        this.rating = parseInt($(ev.currentTarget).data('value'));
        this.$('.o_livechat_rating_choices img').removeClass('selected');
        this.$('.o_livechat_rating_choices img[data-value="'+this.rating+'"]').addClass('selected');

        // only display textearea if bad smiley selected
        var shouldCloseChatWindow = false;
        if (this.rating !== 10) {
            this.$('.o_livechat_rating_reason').show();
        } else {
            this.$('.o_livechat_rating_reason').hide();
            shouldCloseChatWindow = true;
        }
        this._sendFeedback({ close: shouldCloseChatWindow });
    },
});

return {
    LivechatButton: LivechatButton,
    Feedback: Feedback,
};

});
