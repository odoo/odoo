odoo.define('im_livechat.im_livechat', function (require) {
"use strict";

var bus = require('bus.bus').bus;

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var Widget = require('web.Widget');

var LivechatMessage = require('im_livechat.model.LivechatMessage');
var LivechatWindow = require('im_livechat.LivechatWindow');

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
    className:'openerp o_livechat_button hidden-print',
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
        this._channel = null;
        this._chatWindow = null;
        this._messages = [];
        this._serverURL = serverURL;
        this._busBus = bus;
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
        this._busBus.on('notification', this, this._onNotification);
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
        options = _.extend({}, options, {
            serverURL: this._serverURL,
        });
        var message = new LivechatMessage(this, data, options);

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

        var feedback = new Feedback(this, this._channel);
        feedback.replace(this._chatWindow.threadWidget.$el);

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
        if (this._channel && (notification[0] === this._channel.uuid)) {
            if (notification[1]._type === 'history_command') { // history request
                var cookie = utils.get_cookie(LIVECHAT_COOKIE_HISTORY);
                var history = cookie ? JSON.parse(cookie) : [];
                session.rpc('/im_livechat/history', {
                    pid: this._channel.operator_pid[0],
                    channel_uuid: this._channel.uuid,
                    page_history: history,
                });
            } else { // normal message
                this._addMessage(notification[1]);
                this._renderMessages();
                if (this._chatWindow.isFolded() || !this._chatWindow.threadWidget.isAtBottom()) {
                    this._chatWindow.incrementUnreadCounter();
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
        def.then(function (channel) {
            if (!channel || !channel.operator_pid) {
                alert(_t("None of our collaborators seems to be available, please try again later."));
            } else {
                self._channel = channel;
                self._openChatWindow(channel);
                self._sendWelcomeMessage();
                self._renderMessages();

                self._busBus.add_channel(channel.uuid);
                self._busBus.start_polling();

                utils.set_cookie('im_livechat_session', JSON.stringify(channel), 60*60);
                utils.set_cookie('im_livechat_auto_popup', JSON.stringify(false), 60*60);
            }
        }).always(function () {
            self._openingChat = false;
        });
    }, 200, true),
    /**
     * @private
     * @param {Object} channel
     */
    _openChatWindow: function (channel) {
        var self = this;
        var options = {
            displayStars: false,
            placeholder: this.options.input_placeholder || "",
        };
        this._chatWindow = new LivechatWindow(this, channel, options);
        this._chatWindow.appendTo($('body')).then(function () {
            self._chatWindow.$el.css({right: 0, bottom: 0});
            self.$el.hide();
        });
        this._chatWindow.on('close', this, function () {
            var input_disabled = this._chatWindow.$('.o_thread_composer input').prop('disabled');
            var ask_fb = !input_disabled && _.find(this._messages, function (message) {
                return message.getID() !== '_welcome';
            });
            if (ask_fb) {
                this._chatWindow.toggleFold(false);
                this._askFeedback();
            } else {
                this._closeChat();
            }
        });
        this._chatWindow.on('post_message', this, function (message) {
            self._sendMessage(message).fail(function (error, e) {
                e.preventDefault();
                return self._sendMessage(message); // try again just in case
            });
        });
        this._chatWindow.on('save_chat', this, this._onSaveChat);
        this._chatWindow.threadWidget.$el.on('scroll', null, _.debounce(function () {
            if (self._chatWindow.threadWidget.isAtBottom()) {
                self._chatWindow.resetUnreadCounter();
            }
        }, 100));
    },
    /**
     * @private
     */
    _renderMessages: function () {
        var shouldScroll = !this._chatWindow.isFolded() && this._chatWindow.threadWidget.isAtBottom();
        this._chatWindow.render(this._messages);
        if (shouldScroll) {
            this._chatWindow.threadWidget.scrollToBottom();
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
            .rpc('/mail/chat_post', {uuid: this._channel.uuid, message_content: message.content})
            .then(function () {
                self._chatWindow.threadWidget.scrollToBottom();
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
                author_id: this._channel.operator_pid,
                body: this.options.default_message,
                channel_ids: [this._channel.id],
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
     */
    _onSaveChat: function () {
        utils.set_cookie('im_livechat_session', JSON.stringify(this._channel), 60*60);
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

    init: function (parent, channel) {
        this._super(parent);
        this._channel = channel;
        this.server_origin = session.origin;
        this.rating = undefined;
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
            uuid: this._channel.uuid,
            rate: this.rating,
            reason : options.reason
        };
        return session.rpc('/im_livechat/feedback', args).then(function () {
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
