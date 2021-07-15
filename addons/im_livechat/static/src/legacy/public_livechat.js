odoo.define('im_livechat.legacy.im_livechat.im_livechat', function (require) {
"use strict";

require('bus.BusService');
var concurrency = require('web.concurrency');
var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var Widget = require('web.Widget');

var WebsiteLivechat = require('im_livechat.legacy.im_livechat.model.WebsiteLivechat');
var WebsiteLivechatMessage = require('im_livechat.legacy.im_livechat.model.WebsiteLivechatMessage');
var WebsiteLivechatWindow = require('im_livechat.legacy.im_livechat.WebsiteLivechatWindow');

var _t = core._t;
var QWeb = core.qweb;

// Constants
var LIVECHAT_COOKIE_HISTORY = 'im_livechat_history';
var HISTORY_LIMIT = 15;

var RATING_TO_EMOJI = {
    "5": "😊",
    "3": "😐",
    "1": "😞"
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
    utils.set_cookie(LIVECHAT_COOKIE_HISTORY, JSON.stringify(urlHistory), 60 * 60 * 24); // 1 day cookie
}

var LivechatButton = Widget.extend({
    className: 'openerp o_livechat_button d-print-none',
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
            ready = session.rpc('/im_livechat/init', { channel_id: this.options.channel_id })
                .then(function (result) {
                    if (!result.available_for_me) {
                        return Promise.reject();
                    }
                    self._rule = result.rule;
                });
        } else {
            var channel = JSON.parse(cookie);
            ready = session.rpc('/mail/chat_history', { uuid: channel.uuid, limit: 100 })
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
                    setTimeout(this._openChat.bind(this), this._rule.auto_popup_timer * 1000);
            }
        }
        this.call('bus_service', 'onNotification', this, this._onNotification);
        if (this.options.button_background_color) {
            this.$el.css('background-color', this.options.button_background_color);
        }
        if (this.options.button_text_color) {
            this.$el.css('color', this.options.button_text_color);
        }

        // If website_event_track installed, put the livechat banner above the PWA banner.
        var pwaBannerHeight = $('.o_pwa_install_banner').outerHeight(true);
        if (pwaBannerHeight) {
            this.$el.css('bottom', pwaBannerHeight + 'px');
        }

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

        var hasAlreadyMessage = _.some(this._messages, function (msg) {
            return message.getID() === msg.getID();
        });
        if (hasAlreadyMessage) {
            return;
        }

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
    _handleNotification: function (notification) {
        const [livechatUUID, notificationData] = notification;
        if (this._livechat && (livechatUUID === this._livechat.getUUID())) {
            if (notificationData._type === 'history_command') { // history request
                const cookie = utils.get_cookie(LIVECHAT_COOKIE_HISTORY);
                const history = cookie ? JSON.parse(cookie) : [];
                session.rpc('/im_livechat/history', {
                    pid: this._livechat.getOperatorPID()[0],
                    channel_uuid: this._livechat.getUUID(),
                    page_history: history,
                });
            } else if (notificationData.info === 'typing_status') {
                const partnerID = notificationData.partner_id;
                if (partnerID === this.options.current_partner_id) {
                    // ignore typing display of current partner.
                    return;
                }
                if (notificationData.is_typing) {
                    this._livechat.registerTyping({ partnerID });
                } else {
                    this._livechat.unregisterTyping({ partnerID });
                }
            } else if ('body' in notificationData) { // normal message
                // If message from notif is already in chatter messages, stop handling
                if (this._messages.some(message => message.getID() === notificationData.id)) {
                    return;
                }
                this._addMessage(notificationData);
                if (this._chatWindow.isFolded() || !this._chatWindow.isAtBottom()) {
                    this._livechat.incrementUnreadCounter();
                }
                this._renderMessages();
            }
        }
    },
    /**
     * @private
     */
    _loadQWebTemplate: function () {
        return session.rpc('/im_livechat/load_templates').then(function (templates) {
            _.each(templates, function (template) {
                QWeb.add_template(template);
            });
        });
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
            def = Promise.resolve(JSON.parse(cookie));
        } else {
            this._messages = []; // re-initialize messages cache
            def = session.rpc('/im_livechat/get_session', {
                channel_id: this.options.channel_id,
                anonymous_name: this.options.default_username,
                previous_operator_id: this._get_previous_operator_id(),
            }, { shadow: true });
        }
        def.then(function (livechatData) {
            if (!livechatData || !livechatData.operator_pid) {
                try {
                    self.displayNotification({
                        message: _t("No available collaborator, please try again later."),
                        sticky: true,
                    });
                } catch (err) {
                    /**
                     * Failure in displaying notification happens when
                     * notification service doesn't exist, which is the case in
                     * external lib. We don't want notifications in external
                     * lib at the moment because they use bootstrap toast and
                     * we don't want to include boostrap in external lib.
                     */
                    console.warn(_t("No available collaborator, please try again later."));
                }
            } else {
                self._livechat = new WebsiteLivechat({
                    parent: self,
                    data: livechatData
                });
                return self._openChatWindow().then(function () {
                    if (!self._history) {
                        self._sendWelcomeMessage();
                    }
                    self._renderMessages();
                    self.call('bus_service', 'addChannel', self._livechat.getUUID());
                    self.call('bus_service', 'startPolling');

                    utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(self._livechat.toData())), 60 * 60);
                    utils.set_cookie('im_livechat_auto_popup', JSON.stringify(false), 60 * 60);
                    if (livechatData.operator_pid[0]) {
                        // livechatData.operator_pid contains a tuple (id, name)
                        // we are only interested in the id
                        var operatorPidId = livechatData.operator_pid[0];
                        var oneWeek = 7 * 24 * 60 * 60;
                        utils.set_cookie('im_livechat_previous_operator_pid', operatorPidId, oneWeek);
                    }
                });
            }
        }).then(function () {
            self._openingChat = false;
        }).guardedCatch(function () {
            self._openingChat = false;
        });
    }, 200, true),
    /**
     * Will try to get a previous operator for this visitor.
     * If the visitor already had visitor A, it's better for his user experience
     * to get operator A again.
     *
     * The information is stored in the 'im_livechat_previous_operator_pid' cookie.
     *
     * @private
     * @return {integer} operator_id.partner_id.id if the cookie is set
     */
    _get_previous_operator_id: function () {
        var cookie = utils.get_cookie('im_livechat_previous_operator_pid');
        if (cookie) {
            return cookie;
        }

        return null;
    },
    /**
     * @private
     * @return {Promise}
     */
    _openChatWindow: function () {
        var self = this;
        var options = {
            displayStars: false,
            headerBackgroundColor: this.options.header_background_color,
            placeholder: this.options.input_placeholder || "",
            titleColor: this.options.title_color,
        };
        this._chatWindow = new WebsiteLivechatWindow(this, this._livechat, options);
        return this._chatWindow.appendTo($('body')).then(function () {
            var cssProps = { bottom: 0 };
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
     * @return {Promise}
     */
    _sendMessage: function (message) {
        var self = this;
        this._livechat._notifyMyselfTyping({ typing: false });
        return session
            .rpc('/mail/chat_post', { uuid: this._livechat.getUUID(), message_content: message.content })
            .then(function (messageId) {
                if (!messageId) {
                    try {
                        self.displayNotification({
                            message: _t("Session expired... Please refresh and try again."),
                            sticky: true,
                        });
                    } catch (err) {
                        /**
                         * Failure in displaying notification happens when
                         * notification service doesn't exist, which is the case
                         * in external lib. We don't want notifications in
                         * external lib at the moment because they use bootstrap
                         * toast and we don't want to include boostrap in
                         * external lib.
                         */
                        console.warn(_t("Session expired... Please refresh and try again."));
                    }
                    self._closeChat();
                }
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
            }, { prepend: true });
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
        this._sendMessage(messageData).guardedCatch(function (reason) {
            reason.event.preventDefault();
            return self._sendMessage(messageData); // try again just in case
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSaveChatWindow: function (ev) {
        ev.stopPropagation();
        utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(this._livechat.toData())), 60 * 60);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedTypingPartners(ev) {
        ev.stopPropagation();
        this._chatWindow.renderHeader();
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
    template: 'im_livechat.legacy.im_livechat.FeedBack',

    events: {
        'click .o_livechat_rating_choices img': '_onClickSmiley',
        'click .o_livechat_no_feedback span': '_onClickNoFeedback',
        'click .o_rating_submit_button': '_onClickSend',
        'click .o_email_chat_button': '_onEmailChat',
        'click .o_livechat_email_error .alert-link': '_onTryAgain',
    },

    /**
     * @param {?} parent
     * @param {im_livechat.legacy.im_livechat.model.WebsiteLivechat} livechat
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
    _sendFeedback: function (reason) {
        var self = this;
        var args = {
            uuid: this._livechat.getUUID(),
            rate: this.rating,
            reason: reason,
        };
        this.dp.add(session.rpc('/im_livechat/feedback', args)).then(function () {
            var emoji = RATING_TO_EMOJI[self.rating] || "??";
            var content = _.str.sprintf(_t("Rating: %s"), emoji);
            if (reason) {
                content += " \n" + reason;
            }
            self.trigger('send_message', { content: content, isFeedback: true });
        });
    },
    /**
    * @private
    */
    _showThanksMessage: function () {
        this.$('.o_livechat_rating_box').empty().append($('<div />', {
            text: _t('Thank you for your feedback'),
            class: 'text-muted'
        }));
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
        this.$('.o_livechat_rating_reason').hide();
        this._showThanksMessage();
        if (_.isNumber(this.rating)) {
            this._sendFeedback(this.$('textarea').val());
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSmiley: function (ev) {
        this.rating = parseInt($(ev.currentTarget).data('value'));
        this.$('.o_livechat_rating_choices img').removeClass('selected');
        this.$('.o_livechat_rating_choices img[data-value="' + this.rating + '"]').addClass('selected');

        // only display textearea if bad smiley selected
        if (this.rating !== 5) {
            this.$('.o_livechat_rating_reason').show();
        } else {
            this.$('.o_livechat_rating_reason').hide();
            this._showThanksMessage();
            this._sendFeedback();
        }
    },
    /**
    * @private
    */
    _onEmailChat: function () {
        var self = this;
        var $email = this.$('#o_email');

        if (utils.is_email($email.val())) {
            $email.removeAttr('title').removeClass('is-invalid').prop('disabled', true);
            this.$('.o_email_chat_button').prop('disabled', true);
            this._rpc({
                route: '/im_livechat/email_livechat_transcript',
                params: {
                    uuid: this._livechat.getUUID(),
                    email: $email.val(),
                }
            }).then(function () {
                self.$('.o_livechat_email').html($('<strong />', { text: _t('Conversation Sent') }));
            }).guardedCatch(function () {
                self.$('.o_livechat_email').hide();
                self.$('.o_livechat_email_error').show();
            });
        } else {
            $email.addClass('is-invalid').prop('title', _t('Invalid email address'));
        }
    },
    /**
    * @private
    */
    _onTryAgain: function () {
        this.$('#o_email').prop('disabled', false);
        this.$('.o_email_chat_button').prop('disabled', false);
        this.$('.o_livechat_email_error').hide();
        this.$('.o_livechat_email').show();
    },
});

return {
    LivechatButton: LivechatButton,
    Feedback: Feedback,
};

});

odoo.define('im_livechat.legacy.im_livechat.model.WebsiteLivechat', function (require) {
"use strict";

var AbstractThread = require('im_livechat.legacy.mail.model.AbstractThread');
var ThreadTypingMixin = require('im_livechat.legacy.mail.model.ThreadTypingMixin');

var session = require('web.session');

/**
 * Thread model that represents a livechat on the website-side. This livechat
 * is not linked to the mail service.
 */
var WebsiteLivechat = AbstractThread.extend(ThreadTypingMixin, {

    /**
     * @override
     * @private
     * @param {Object} params
     * @param {Object} params.data
     * @param {boolean} [params.data.folded] states whether the livechat is
     *   folded or not. It is considered only if this is defined and it is a
     *   boolean.
     * @param {integer} params.data.id the ID of this livechat.
     * @param {integer} [params.data.message_unread_counter] the unread counter
     *   of this livechat.
     * @param {Array} params.data.operator_pid
     * @param {string} params.data.name the name of this livechat.
     * @param {string} [params.data.state] if 'folded', the livechat is folded.
     *   This is ignored if `folded` is provided and is a boolean value.
     * @param {string} params.data.uuid the UUID of this livechat.
     * @param {im_livechat.legacy.im_livechat.im_livechat:LivechatButton} params.parent
     */
    init: function (params) {
        this._super.apply(this, arguments);
        ThreadTypingMixin.init.call(this, arguments);

        this._members = [];
        this._operatorPID = params.data.operator_pid;
        this._uuid = params.data.uuid;

        if (params.data.message_unread_counter !== undefined) {
            this._unreadCounter = params.data.message_unread_counter;
        }

        if (_.isBoolean(params.data.folded)) {
            this._folded = params.data.folded;
        } else {
            this._folded = params.data.state === 'folded';
        }

        // Necessary for thread typing mixin to display is typing notification
        // bar text (at least, for the operator in the members).
        this._members.push({
            id: this._operatorPID[0],
            name: this._operatorPID[1]
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {im_livechat.legacy.im_livechat.model.WebsiteLivechatMessage[]}
     */
    getMessages: function () {
        return this._messages;
    },
    /**
     * @returns {Array}
     */
    getOperatorPID: function () {
        return this._operatorPID;
    },
    /**
     * @returns {string}
     */
    getUUID: function () {
        return this._uuid;
    },
    /**
     * Increments the unread counter of this livechat by 1 unit.
     *
     * Note: this public method makes sense because the management of messages
     * for website livechat is external. This method should be dropped when
     * this class handles messages by itself.
     */
    incrementUnreadCounter: function () {
        this._incrementUnreadCounter();
    },
    /**
     * AKU: hack for the moment
     *
     * @param {im_livechat.legacy.im_livechat.model.WebsiteLivechatMessage[]} messages
     */
    setMessages: function (messages) {
        this._messages = messages;
    },
    /**
     * @returns {Object}
     */
    toData: function () {
        return {
            folded: this.isFolded(),
            id: this.getID(),
            message_unread_counter: this.getUnreadCounter(),
            operator_pid: this.getOperatorPID(),
            name: this.getName(),
            uuid: this.getUUID(),
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {Object} params
     * @param {boolean} params.isWebsiteUser
     * @returns {boolean}
     */
    _isTypingMyselfInfo: function (params) {
        return params.isWebsiteUser;
    },
    /**
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {Object} params
     * @param {boolean} params.typing
     * @returns {Promise}
     */
    _notifyMyselfTyping: function (params) {
        return session.rpc('/im_livechat/notify_typing', {
            uuid: this.getUUID(),
            is_typing: params.typing,
        }, { shadow: true });
    },
    /**
     * Warn views that the list of users that are currently typing on this
     * livechat has been updated.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @private
     */
    _warnUpdatedTypingPartners: function () {
        this.trigger_up('updated_typing_partners');
    },
    /**
     * Warn that the unread counter has been updated on this livechat
     *
     * @override
     * @private
     */
    _warnUpdatedUnreadCounter: function () {
        this.trigger_up('updated_unread_counter');
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Override so that it only unregister typing operators.
     *
     * Note that in the frontend, there is no way to identify a message that is
     * from the current user, because there is no partner ID in the session and
     * a message with an author sets the partner ID of the author.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {mail.model.AbstractMessage} message
     */
    _onTypingMessageAdded: function (message) {
        var operatorID = this.getOperatorPID()[0];
        if (message.hasAuthor() && message.getAuthorID() === operatorID) {
            this.unregisterTyping({ partnerID: operatorID });
        }
    },
});

return WebsiteLivechat;

});

odoo.define('im_livechat.legacy.im_livechat.model.WebsiteLivechatMessage', function (require) {
"use strict";

var AbstractMessage = require('im_livechat.legacy.mail.model.AbstractMessage');

/**
 * This is a message that is handled by im_livechat, without making use of the
 * mail.Manager. The purpose of this is to make im_livechat compatible with
 * mail.widget.Thread.
 *
 * @see im_livechat.legacy.mail.model.AbstractMessage for more information.
 */
var WebsiteLivechatMessage = AbstractMessage.extend({

    /**
     * @param {im_livechat.legacy.im_livechat.im_livechat.LivechatButton} parent
     * @param {Object} data
     * @param {Object} options
     * @param {string} options.default_username
     * @param {string} options.serverURL
     */
    init: function (parent, data, options) {
        this._super.apply(this, arguments);

        this._defaultUsername = options.default_username;
        this._serverURL = options.serverURL;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the relative url of the avatar to display next to the message
     *
     * @override
     * @return {string}
     */
    getAvatarSource: function () {
        var source = this._serverURL;
        if (this.hasAuthor()) {
            source += '/web/partner_image/' + this.getAuthorID();
        } else {
            source += '/mail/static/src/img/smiley/avatar.jpg';
        }
        return source;
    },
    /**
     * Get the text to display for the author of the message
     *
     * Rule of precedence for the displayed author::
     *
     *      author name > default usernane
     *
     * @override
     * @return {string}
     */
    getDisplayedAuthor: function () {
        return this._super.apply(this, arguments) || this._defaultUsername;
    },

});

return WebsiteLivechatMessage;

});

odoo.define('im_livechat.legacy.im_livechat.WebsiteLivechatWindow', function (require) {
"use strict";

var AbstractThreadWindow = require('im_livechat.legacy.mail.AbstractThreadWindow');

/**
 * This is the widget that represent windows of livechat in the frontend.
 *
 * @see im_livechat.legacy.mail.AbstractThreadWindow for more information
 */
var LivechatWindow = AbstractThreadWindow.extend({
    events: _.extend(AbstractThreadWindow.prototype.events, {
        'input .o_composer_text_field': '_onInput',
    }),
    /**
     * @override
     * @param {im_livechat.legacy.im_livechat.im_livechat:LivechatButton} parent
     * @param {im_livechat.legacy.im_livechat.model.WebsiteLivechat} thread
     * @param {Object} [options={}]
     * @param {string} [options.headerBackgroundColor]
     * @param {string} [options.titleColor]
     */
    init(parent, thread, options = {}) {
        this._super.apply(this, arguments);
        this._thread = thread;
    },
    /**
     * @override
     * @return {Promise}
     */
    async start() {
        await this._super(...arguments);
        if (this.options.headerBackgroundColor) {
            this.$('.o_thread_window_header').css('background-color', this.options.headerBackgroundColor);
        }
        if (this.options.titleColor) {
            this.$('.o_thread_window_header').css('color', this.options.titleColor);
        }
    },


    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    close: function () {
        this.trigger_up('close_chat_window');
    },
    /**
     * Replace the thread content with provided new content
     *
     * @param {$.Element} $element
     */
    replaceContentWith: function ($element) {
        $element.replace(this._threadWidget.$el);
    },
    /**
     * Warn the parent widget (LivechatButton)
     *
     * @override
     * @param {boolean} folded
     */
    toggleFold: function () {
        this._super.apply(this, arguments);
        this.trigger_up('save_chat_window');
        this.updateVisualFoldState();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {Object} messageData
     */
    _postMessage: function (messageData) {
        this.trigger_up('post_message_chat_window', { messageData: messageData });
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the input in the composer changes
     *
     * @private
     */
    _onInput: function () {
        if (this.hasThread() && this._thread.hasTypingNotification()) {
            var isTyping = this.$input.val().length > 0;
            this._thread.setMyselfTyping({ typing: isTyping });
        }
    },
});

return LivechatWindow;

});

odoo.define('im_livechat.legacy.mail.model.AbstractThread', function (require) {
"use strict";

var Class = require('web.Class');
var Mixins = require('web.mixins');

/**
 * Abstract thread is the super class of all threads, either backend threads
 * (which are compatible with mail service) or website livechats.
 *
 * Abstract threads contain abstract messages
 */
var AbstractThread = Class.extend(Mixins.EventDispatcherMixin, {
    /**
     * @param {Object} params
     * @param {Object} params.data
     * @param {integer|string} params.data.id the ID of this thread
     * @param {string} params.data.name the name of this thread
     * @param {string} [params.data.status=''] the status of this thread
     * @param {Object} params.parent Object with the event-dispatcher mixin
     *   (@see {web.mixins.EventDispatcherMixin})
     */
    init: function (params) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(params.parent);

        this._folded = false; // threads are unfolded by default
        this._id = params.data.id;
        this._name = params.data.name;
        this._status = params.data.status || '';
        this._unreadCounter = 0; // amount of messages not yet been read
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a message to this thread.
     *
     * @param {im_livechat.legacy.mail.model.AbstractMessage} message
     */
    addMessage: function (message) {
        this._addMessage.apply(this, arguments);
        this.trigger('message_added', message);
    },
    /**
     * Updates the folded state of the thread
     *
     * @param {boolean} folded
     */
    fold: function (folded) {
        this._folded = folded;
    },
    /**
     * Get the ID of this thread
     *
     * @returns {integer|string}
     */
    getID: function () {
        return this._id;
    },
    /**
     * @abstract
     * @returns {im_livechat.legacy.mail.model.AbstractMessage[]}
     */
    getMessages: function () {},
    /**
     * Get the name of this thread. If the name of the thread has been created
     * by the user from an input, it may be escaped.
     *
     * @returns {string}
     */
    getName: function () {
        return this._name;
    },
    /**
     * Get the status of the thread (e.g. 'online', 'offline', etc.)
     *
     * @returns {string}
     */
    getStatus: function () {
        return this._status;
    },
    /**
     * Returns the title to display in thread window's headers.
     *
     * @returns {string} the name of the thread by default (see @getName)
     */
    getTitle: function () {
        return this.getName();
    },
    getType: function () {},
    /**
     * @returns {integer}
     */
    getUnreadCounter: function () {
        return this._unreadCounter;
    },
    /**
     * @returns {boolean}
     */
    hasMessages: function () {
        return !_.isEmpty(this.getMessages());
    },
    /**
     * States whether this thread is compatible with the 'seen' feature.
     * By default, threads do not have thsi feature active.
     * @see {im_livechat.legacy.mail.model.ThreadSeenMixin} to enable this feature on a thread.
     *
     * @returns {boolean}
     */
    hasSeenFeature: function () {
        return false;
    },
    /**
     * States whether this thread is folded or not.
     *
     * @return {boolean}
     */
    isFolded: function () {
        return this._folded;
    },
    /**
     * Mark the thread as read, which resets the unread counter to 0. This is
     * only performed if the unread counter is not 0.
     *
     * @returns {Promise}
     */
    markAsRead: function () {
        if (this._unreadCounter > 0) {
            return this._markAsRead();
        }
        return Promise.resolve();
    },
    /**
     * Post a message on this thread
     *
     * @returns {Promise} resolved with the message object to be sent to the
     *   server
     */
    postMessage: function () {
        return this._postMessage.apply(this, arguments)
                                .then(this.trigger.bind(this, 'message_posted'));
    },
    /**
     * Resets the unread counter of this thread to 0.
     */
    resetUnreadCounter: function () {
        this._unreadCounter = 0;
        this._warnUpdatedUnreadCounter();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a message to this thread.
     *
     * @abstract
     * @private
     * @param {im_livechat.legacy.mail.model.AbstractMessage} message
     */
    _addMessage: function (message) {},
    /**
     * Increments the unread counter of this thread by 1 unit.
     *
     * @private
     */
    _incrementUnreadCounter: function () {
        this._unreadCounter++;
    },
    /**
     * Mark the thread as read
     *
     * @private
     * @returns {Promise}
     */
    _markAsRead: function () {
        this.resetUnreadCounter();
        return Promise.resolve();
    },
    /**
     * Post a message on this thread
     *
     * @abstract
     * @private
     * @returns {Promise} resolved with the message object to be sent to the
     *   server
     */
    _postMessage: function () {
        return Promise.resolve();
    },
    /**
     * Warn views (e.g. discuss app, thread window, etc.) to update visually
     * the unread counter of this thread.
     *
     * @abstract
     * @private
     */
    _warnUpdatedUnreadCounter: function () {},
});

return AbstractThread;

});

odoo.define('im_livechat.legacy.mail.model.ThreadTypingMixin', function (require) {
"use strict";

var CCThrottleFunction = require('im_livechat.legacy.mail.model.CCThrottleFunction');
var Timer = require('im_livechat.legacy.mail.model.Timer');
var Timers = require('im_livechat.legacy.mail.model.Timers');

var core = require('web.core');

var _t = core._t;

/**
 * Mixin for enabling the "is typing..." notification on a type of thread.
 */
var ThreadTypingMixin = {
    // Default partner infos
    _DEFAULT_TYPING_PARTNER_ID: '_default',
    _DEFAULT_TYPING_PARTNER_NAME: 'Someone',

    /**
     * Initialize the internal data for typing feature on threads.
     *
     * Also listens on some internal events of the thread:
     *
     * - 'message_added': when a message is added, remove the author in the
     *     typing partners.
     * - 'message_posted': when a message is posted, let the user have the
     *     possibility to immediately notify if he types something right away,
     *     instead of waiting for a throttle behaviour.
     */
    init: function () {
        // Store the last "myself typing" status that has been sent to the
        // server. This is useful in order to not notify the same typing
        // status multiple times.
        this._lastNotifiedMyselfTyping = false;

        // Timer of current user that is typing a very long text. When the
        // receivers do not receive any typing notification for a long time,
        // they assume that the related partner is no longer typing
        // something (e.g. they have closed the browser tab).
        // This is a timer to let others know that we are still typing
        // something, so that they do not assume we stopped typing
        // something.
        this._myselfLongTypingTimer = new Timer({
            duration: 50 * 1000,
            onTimeout: this._onMyselfLongTypingTimeout.bind(this),
        });

        // Timer of current user that was currently typing something, but
        // there is no change on the input for several time. This is used
        // in order to automatically notify other users that we have stopped
        // typing something, due to making no changes on the composer for
        // some time.
        this._myselfTypingInactivityTimer = new Timer({
            duration: 5 * 1000,
            onTimeout: this._onMyselfTypingInactivityTimeout.bind(this),
        });

        // Timers of users currently typing in the thread. This is useful
        // in order to automatically unregister typing users when we do not
        // receive any typing notification after a long time. Timers are
        // internally indexed by partnerID. The current user is ignored in
        // this list of timers.
        this._othersTypingTimers = new Timers({
            duration: 60 * 1000,
            onTimeout: this._onOthersTypingTimeout.bind(this),
        });

        // Clearable and cancellable throttled version of the
        // `doNotifyMyselfTyping` method. (basically `notifyMyselfTyping`
        // with slight pre- and post-processing)
        // @see {mail.model.ResetableThrottleFunction}
        // This is useful when the user posts a message and types something
        // else: he must notify immediately that he is typing something,
        // instead of waiting for the throttle internal timer.
        this._throttleNotifyMyselfTyping = CCThrottleFunction({
            duration: 2.5 * 1000,
            func: this._onNotifyMyselfTyping.bind(this),
        });

        // This is used to track the order of registered partners typing
        // something, in order to display the oldest typing partners.
        this._typingPartnerIDs = [];

        this.on('message_added', this, this._onTypingMessageAdded);
        this.on('message_posted', this, this._onTypingMessagePosted);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the text to display when some partners are typing something on the
     * thread:
     *
     * - single typing partner:
     *
     *   A is typing...
     *
     * - two typing partners:
     *
     *   A and B are typing...
     *
     * - three or more typing partners:
     *
     *   A, B and more are typing...
     *
     * The choice of the members name for display is not random: it displays
     * the user that have been typing for the longest time. Also, this function
     * is hard-coded to display at most 2 partners. This limitation comes from
     * how translation works in Odoo, for which unevaluated string cannot be
     * translated.
     *
     * @returns {string} list of members that are typing something on the thread
     *   (excluding the current user).
     */
    getTypingMembersToText: function () {
        var typingPartnerIDs = this._typingPartnerIDs;
        var typingMembers = _.filter(this._members, function (member) {
            return _.contains(typingPartnerIDs, member.id);
        });
        var sortedTypingMembers = _.sortBy(typingMembers, function (member) {
            return _.indexOf(typingPartnerIDs, member.id);
        });
        var displayableTypingMembers = sortedTypingMembers.slice(0, 3);

        if (displayableTypingMembers.length === 0) {
            return '';
        } else if (displayableTypingMembers.length === 1) {
            return _.str.sprintf(_t("%s is typing..."), displayableTypingMembers[0].name);
        } else if (displayableTypingMembers.length === 2) {
            return _.str.sprintf(_t("%s and %s are typing..."),
                                    displayableTypingMembers[0].name,
                                    displayableTypingMembers[1].name);
        } else {
            return _.str.sprintf(_t("%s, %s and more are typing..."),
                                    displayableTypingMembers[0].name,
                                    displayableTypingMembers[1].name);
        }
    },
    /**
     * Threads with this mixin have the typing notification feature
     *
     * @returns {boolean}
     */
    hasTypingNotification: function () {
        return true;
    },
    /**
     * Tells if someone other than current user is typing something on this
     * thread.
     *
     * @returns {boolean}
     */
    isSomeoneTyping: function () {
        return !(_.isEmpty(this._typingPartnerIDs));
    },
    /**
     * Register someone that is currently typing something in this thread.
     * If this is the current user that is typing something, don't do anything
     * (we do not have to display anything)
     *
     * This method is ignored if we try to register the current user.
     *
     * @param {Object} params
     * @param {integer} params.partnerID ID of the partner linked to the user
     *   currently typing something on the thread.
     */
    registerTyping: function (params) {
        if (this._isTypingMyselfInfo(params)) {
            return;
        }
        var partnerID = params.partnerID;
        this._othersTypingTimers.registerTimer({
            timeoutCallbackArguments: [partnerID],
            timerID: partnerID,
        });
        if (_.contains(this._typingPartnerIDs, partnerID)) {
            return;
        }
        this._typingPartnerIDs.push(partnerID);
        this._warnUpdatedTypingPartners();
    },
    /**
     * This method must be called when the user starts or stops typing something
     * in the composer of the thread.
     *
     * @param {Object} params
     * @param {boolean} params.typing tell whether the current is typing or not.
     */
    setMyselfTyping: function (params) {
        var typing = params.typing;
        if (this._lastNotifiedMyselfTyping === typing) {
            this._throttleNotifyMyselfTyping.cancel();
        } else {
            this._throttleNotifyMyselfTyping(params);
        }

        if (typing) {
            this._myselfTypingInactivityTimer.reset();
        } else {
            this._myselfTypingInactivityTimer.clear();
        }
    },
    /**
     * Unregister someone from currently typing something in this thread.
     *
     * @param {Object} params
     * @param {integer} params.partnerID ID of the partner related to the user
     *   that is currently typing something
     */
    unregisterTyping: function (params) {
        var partnerID = params.partnerID;
        this._othersTypingTimers.unregisterTimer({ timerID: partnerID });
        if (!_.contains(this._typingPartnerIDs, partnerID)) {
            return;
        }
        this._typingPartnerIDs = _.reject(this._typingPartnerIDs, function (id) {
            return id === partnerID;
        });
        this._warnUpdatedTypingPartners();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Tells whether the provided information on a partner is related to the
     * current user or not.
     *
     * @abstract
     * @private
     * @param {Object} params
     * @param {integer} params.partner ID of partner to check
     */
    _isTypingMyselfInfo: function (params) {
        return false;
    },
    /**
     * Notify to the server that the current user either starts or stops typing
     * something.
     *
     * @abstract
     * @private
     * @param {Object} params
     * @param {boolean} params.typing whether we are typing something or not
     * @returns {Promise} resolved if the server is notified, rejected
     *   otherwise
     */
    _notifyMyselfTyping: function (params) {
        return Promise.resolve();
    },
    /**
     * Warn views that the list of users that are currently typing on this
     * thread has been updated.
     *
     * @abstract
     * @private
     */
    _warnUpdatedTypingPartners: function () {},

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when current user is typing something for a long time. In order
     * to not let other users assume that we are no longer typing something, we
     * must notify again that we are typing something.
     *
     * @private
     */
    _onMyselfLongTypingTimeout: function () {
        this._throttleNotifyMyselfTyping.clear();
        this._throttleNotifyMyselfTyping({ typing: true });
    },
    /**
     * Called when current user has something typed in the composer, but is
     * inactive for some time. In this case, he automatically notifies that he
     * is no longer typing something
     *
     * @private
     */
    _onMyselfTypingInactivityTimeout: function () {
        this._throttleNotifyMyselfTyping.clear();
        this._throttleNotifyMyselfTyping({ typing: false });
    },
    /**
     * Called by throttled version of notify myself typing
     *
     * Notify to the server that the current user either starts or stops typing
     * something. Remember last notified stuff from the server, and update
     * related typing timers.
     *
     * @private
     * @param {Object} params
     * @param {boolean} params.typing whether we are typing something or not.
     */
    _onNotifyMyselfTyping: function (params) {
        var typing = params.typing;
        this._lastNotifiedMyselfTyping = typing;
        this._notifyMyselfTyping(params);
        if (typing) {
            this._myselfLongTypingTimer.reset();
        } else {
            this._myselfLongTypingTimer.clear();
        }
    },
    /**
     * Called when current user do not receive a typing notification of someone
     * else typing for a long time. In this case, we assume that this person is
     * no longer typing something.
     *
     * @private
     * @param {integer} partnerID partnerID of the person we assume he is no
     *   longer typing something.
     */
    _onOthersTypingTimeout: function (partnerID) {
        this.unregisterTyping({ partnerID: partnerID });
    },
    /**
     * Called when a new message is added to the thread
     * On receiving a message from a typing partner, unregister this partner
     * from typing partners (otherwise, it will still display it until timeout).
     *
     * @private
     * @param {mail.model.AbstractMessage} message
     */
    _onTypingMessageAdded: function (message) {
        var partnerID = message.hasAuthor() ?
                        message.getAuthorID() :
                        this._DEFAULT_TYPING_PARTNER_ID;
        this.unregisterTyping({ partnerID: partnerID });
    },
    /**
     * Called when current user has posted a message on this thread.
     *
     * The current user receives the possibility to immediately notify the
     * other users if he is typing something else.
     *
     * Refresh the context for the current user to notify that he starts or
     * stops typing something. In other words, when this function is called and
     * then the current user types something, it immediately notifies the
     * server as if it is the first time he is typing something.
     *
     * @private
     */
    _onTypingMessagePosted: function () {
        this._lastNotifiedMyselfTyping = false;
        this._throttleNotifyMyselfTyping.clear();
        this._myselfLongTypingTimer.clear();
        this._myselfTypingInactivityTimer.clear();
    },
};

return ThreadTypingMixin;

});

odoo.define('im_livechat.legacy.mail.model.AbstractMessage', function (require) {
"use strict";

var mailUtils = require('mail.utils');

var Class = require('web.Class');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');

var _t = core._t;

/**
 * This is an abstract class for modeling messages in JS.
 * The purpose of this interface is to make im_livechat compatible with
 * mail.widget.Thread, as this widget was designed to work with messages that
 * are instances of mail.model.Messages.
 *
 * Ideally, im_livechat should also handle mail.model.Message, but this is not
 * feasible for the moment, as mail.model.Message requires mail.Manager to work,
 * and this module should not leak outside of the backend, hence the use of
 * mail.model.AbstractMessage as a work-around.
 */
var AbstractMessage = Class.extend({

    /**
     * @param {Widget} parent
     * @param {Object} data
     * @param {Array} [data.attachment_ids=[]]
     * @param {Array} [data.author_id]
     * @param {string} [data.body = ""]
     * @param {string} [data.date] the server-format date time of the message.
     *   If not provided, use current date time for this message.
     * @param {integer} data.id
     * @param {boolean} [data.is_discussion = false]
     * @param {boolean} [data.is_notification = false]
     * @param {string} [data.message_type = undefined]
     */
    init: function (parent, data) {
        this._attachmentIDs = data.attachment_ids || [];
        this._body = data.body || "";
        // by default: current datetime
        this._date = data.date ? moment(time.str_to_datetime(data.date)) : moment();
        this._id = data.id;
        this._isDiscussion = data.is_discussion;
        this._isNotification = data.is_notification;
        this._serverAuthorID = data.author_id;
        this._type = data.message_type || undefined;

        this._processAttachmentURL();
        this._attachmentIDs.forEach(function (attachment) {
            attachment.filename = attachment.filename || attachment.name || _t("unnamed");
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the list of files attached to this message.
     * Note that attachments are stored with server-format
     *
     * @return {Object[]}
     */
    getAttachments: function () {
        return this._attachmentIDs;
    },
    /**
     * Get the server ID (number) of the author of this message
     * If there are no author, return -1;
     *
     * @return {integer}
     */
    getAuthorID: function () {
        if (!this.hasAuthor()) {
            return -1;
        }
        return this._serverAuthorID[0];
    },
    /**
     * Threads do not have an im status by default
     *
     * @return {undefined}
     */
    getAuthorImStatus: function () {
        return undefined;
    },
    /**
     * Get the relative url of the avatar to display next to the message
     *
     * @abstract
     * @return {string}
     */
    getAvatarSource: function () {
        if (this.hasAuthor()) {
            return '/web/image/res.partner/' + this.getAuthorID() + '/image_128';
        }
    },
    /**
     * Get the body content of this message
     *
     * @return {string}
     */
    getBody: function () {
        return this._body;
    },
    /**
     * @return {moment}
     */
    getDate: function () {
        return this._date;
    },
    /**
     * Get the date day of this message
     *
     * @return {string}
     */
    getDateDay: function () {
        var date = this.getDate().format('YYYY-MM-DD');
        if (date === moment().format('YYYY-MM-DD')) {
            return _t("Today");
        } else if (date === moment().subtract(1, 'days').format('YYYY-MM-DD')) {
            return _t("Yesterday");
        }
        return this.getDate().format('LL');
    },
    /**
     * Get the name of the author, if there is an author of this message
     * If there are no author of this message, returns 'null'
     *
     * @return {string}
     */
    getDisplayedAuthor: function () {
        return this.hasAuthor() ? this._getAuthorName() : null;
    },
    /**
     * Get the server ID (number) of this message
     *
     * @override
     * @return {integer}
     */
    getID: function () {
        return this._id;
    },
    /**
     * Get the list of images attached to this message.
     * Note that attachments are stored with server-format
     *
     * @return {Object[]}
     */
    getImageAttachments: function () {
        return _.filter(this.getAttachments(), function (attachment) {
            return attachment.mimetype && attachment.mimetype.split('/')[0] === 'image';
        });
    },
    /**
     * Get the list of non-images attached to this message.
     * Note that attachments are stored with server-format
     *
     * @return {Object[]}
     */
    getNonImageAttachments: function () {
        return _.difference(this.getAttachments(), this.getImageAttachments());
    },
    /**
     * Gets the class to use as the notification icon.
     *
     * @returns {string}
     */
    getNotificationIcon() {
        if (!this.hasNotificationsError()) {
            return 'fa fa-envelope-o';
        }
        return 'fa fa-envelope';
    },
    /**
     * Gets the list of notifications of this message, in no specific order.
     * By default messages do not have notifications.
     *
     * @returns {Object[]}
     */
    getNotifications() {
        return [];
    },
    /**
     * Gets the text to display next to the notification icon.
     *
     * @returns {string}
     */
    getNotificationText() {
        return '';
    },
    /**
     * Get the time elapsed between sent message and now
     *
     * @return {string}
     */
    getTimeElapsed: function () {
        return mailUtils.timeFromNow(this.getDate());
    },
    /**
     * Get the type of message (e.g. 'comment', 'email', 'notification', ...)
     * By default, messages are of type 'undefined'
     *
     * @override
     * @return {string|undefined}
     */
    getType: function () {
        return this._type;
    },
    /**
     * State whether this message contains some attachments.
     *
     * @override
     * @return {boolean}
     */
    hasAttachments: function () {
        return this.getAttachments().length > 0;
    },
    /**
     * State whether this message has an author
     *
     * @return {boolean}
     */
    hasAuthor: function () {
        return !!(this._serverAuthorID && this._serverAuthorID[0]);
    },
    /**
     * State whether this message has an email of its sender.
     * By default, messages do not have any email of its sender.
     *
     * @return {string}
     */
    hasEmailFrom: function () {
        return false;
    },
    /**
     * State whether this image contains images attachments
     *
     * @return {boolean}
     */
    hasImageAttachments: function () {
        return _.some(this.getAttachments(), function (attachment) {
            return attachment.mimetype && attachment.mimetype.split('/')[0] === 'image';
        });
    },
    /**
     * State whether this image contains non-images attachments
     *
     * @return {boolean}
     */
    hasNonImageAttachments: function () {
        return _.some(this.getAttachments(), function (attachment) {
            return !(attachment.mimetype && attachment.mimetype.split('/')[0] === 'image');
        });
    },
    /**
     * States whether this message has some notifications.
     *
     * @returns {boolean}
     */
    hasNotifications() {
        return this.getNotifications().length > 0;
    },
    /**
     * States whether this message has notifications that are in error.
     *
     * @returns {boolean}
     */
    hasNotificationsError() {
        return this.getNotifications().some(notif =>
            notif.notification_status === 'exception' ||
            notif.notification_status === 'bounce'
        );
    },
    /**
     * State whether this message originates from a channel.
     * By default, messages do not originate from a channel.
     *
     * @override
     * @return {boolean}
     */
    originatesFromChannel: function () {
        return false;
    },
    /**
     * State whether this message has a subject
     * By default, messages do not have any subject.
     *
     * @return {boolean}
     */
    hasSubject: function () {
        return false;
    },
    /**
     * State whether this message is empty
     *
     * @return {boolean}
     */
    isEmpty: function () {
        return !this.hasTrackingValues() &&
        !this.hasAttachments() &&
        !this.getBody();
    },
    /**
     * By default, messages do not have any subtype description
     *
     * @return {boolean}
     */
    hasSubtypeDescription: function () {
        return false;
    },
    /**
     * State whether this message contains some tracking values
     * By default, messages do not have any tracking values.
     *
     * @return {boolean}
     */
    hasTrackingValues: function () {
        return false;
    },
    /**
     * State whether this message is a discussion
     *
     * @return {boolean}
     */
    isDiscussion: function () {
        return this._isDiscussion;
    },
    /**
     * State whether this message is linked to a document thread
     * By default, messages are not linked to a document thread.
     *
     * @return {boolean}
     */
    isLinkedToDocumentThread: function () {
        return false;
    },
    /**
     * State whether this message is needaction
     * By default, messages are not needaction.
     *
     * @return {boolean}
     */
    isNeedaction: function () {
        return false;
    },
    /**
     * State whether this message is a note (i.e. a message from "Log note")
     *
     * @return {boolean}
     */
    isNote: function () {
        return this._isNote;
    },
    /**
     * State whether this message is a notification
     *
     * User notifications are defined as either
     *      - notes
     *      - pushed to user Inbox or email through classic notification process
     *      - not linked to any document, meaning model and res_id are void
     *
     * This is useful in order to display white background for user
     * notifications in chatter
     *
     * @returns {boolean}
     */
    isNotification: function () {
        return this._isNotification;
    },
    /**
     * State whether this message is starred
     * By default, messages are not starred.
     *
     * @return {boolean}
     */
    isStarred: function () {
        return false;
    },
    /**
     * State whether this message is a system notification
     * By default, messages are not system notifications
     *
     * @override
     * @return {boolean}
     */
    isSystemNotification: function () {
        return false;
    },
    /**
     * States whether the current message needs moderation in general.
     * By default, messages do not require any moderation.
     *
     * @returns {boolean}
     */
    needsModeration: function () {
        return false;
    },
    /**
     * @params {integer[]} attachmentIDs
     */
    removeAttachments: function (attachmentIDs) {
        this._attachmentIDs = _.reject(this._attachmentIDs, function (attachment) {
            return _.contains(attachmentIDs, attachment.id);
        });
    },
    /**
     * State whether this message should redirect to the author
     * when clicking on the author of this message.
     *
     * Do not redirect on author clicked of self-posted messages.
     *
     * @return {boolean}
     */
    shouldRedirectToAuthor: function () {
        return !this._isMyselfAuthor();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get the name of the author of this message.
     * If there are no author of this messages, returns '' (empty string).
     *
     * @private
     * @returns {string}
     */
    _getAuthorName: function () {
        if (!this.hasAuthor()) {
            return "";
        }
        return this._serverAuthorID[1];
    },
    /**
     * State whether the current user is the author of this message
     *
     * @private
     * @return {boolean}
     */
    _isMyselfAuthor: function () {
        return this.hasAuthor() && (this.getAuthorID() === session.partner_id);
    },
    /**
     * Compute url of attachments of this message
     *
     * @private
     */
    _processAttachmentURL: function () {
        _.each(this.getAttachments(), function (attachment) {
            attachment.url = '/web/content/' + attachment.id + '?download=true';
        });
    },

});

return AbstractMessage;

});

odoo.define('im_livechat.legacy.mail.AbstractThreadWindow', function (require) {
"use strict";

var ThreadWidget = require('im_livechat.legacy.mail.widget.Thread');

var config = require('web.config');
var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

/**
 * This is an abstract widget for rendering thread windows.
 * AbstractThreadWindow is kept for legacy reasons. 
 */
var AbstractThreadWindow = Widget.extend({
    template: 'im_livechat.legacy.mail.AbstractThreadWindow',
    custom_events: {
        document_viewer_closed: '_onDocumentViewerClose',
    },
    events: {
        'click .o_thread_window_close': '_onClickClose',
        'click .o_thread_window_title': '_onClickFold',
        'click .o_composer_text_field': '_onComposerClick',
        'click .o_mail_thread': '_onThreadWindowClicked',
        'keydown .o_composer_text_field': '_onKeydown',
        'keypress .o_composer_text_field': '_onKeypress',
    },
    FOLD_ANIMATION_DURATION: 200, // duration in ms for (un)fold transition
    HEIGHT_OPEN: '400px', // height in px of thread window when open
    HEIGHT_FOLDED: '34px', // height, in px, of thread window when folded
    /**
     * Children of this class must make use of `thread`, which is an object that
     * represent the thread that is linked to this thread window.
     *
     * If no thread is provided, this will represent the "blank" thread window.
     *
     * @abstract
     * @param {Widget} parent
     * @param {im_livechat.legacy.mail.model.AbstractThread} [thread=null] the thread that this
     *   thread window is linked to. If not set, it is the "blank" thread
     *   window.
     * @param {Object} [options={}]
     * @param {im_livechat.legacy.mail.model.AbstractThread} [options.thread]
     */
    init: function (parent, thread, options) {
        this._super(parent);

        this.options = _.defaults(options || {}, {
            autofocus: true,
            displayStars: true,
            displayReplyIcons: false,
            displayNotificationIcons: false,
            placeholder: _t("Say something"),
        });

        this._hidden = false;
        this._thread = thread || null;

        this._debouncedOnScroll = _.debounce(this._onScroll.bind(this), 100);

        if (!this.hasThread()) {
            // internal fold state of thread window without any thread
            this._folded = false;
        }
    },
    start: function () {
        var self = this;
        this.$input = this.$('.o_composer_text_field');
        this.$header = this.$('.o_thread_window_header');
        var options = {
            displayMarkAsRead: false,
            displayStars: this.options.displayStars,
        };
        if (this._thread && this._thread._type === 'document_thread') {
            options.displayDocumentLinks = false;
        }
        this._threadWidget = new ThreadWidget(this, options);

        // animate the (un)folding of thread windows
        this.$el.css({ transition: 'height ' + this.FOLD_ANIMATION_DURATION + 'ms linear' });
        if (this.isFolded()) {
            this.$el.css('height', this.HEIGHT_FOLDED);
        } else if (this.options.autofocus) {
            this._focusInput();
        }
        if (!config.device.isMobile) {
            var margin_dir = _t.database.parameters.direction === "rtl" ? "margin-left" : "margin-right";
            this.$el.css(margin_dir, $.position.scrollbarWidth());
        }
        var def = this._threadWidget.replace(this.$('.o_thread_window_content')).then(function () {
            self._threadWidget.$el.on('scroll', self, self._debouncedOnScroll);
        });
        return Promise.all([this._super(), def]);
    },
    /**
     * @override
     */
    do_hide: function () {
        this._hidden = true;
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    do_show: function () {
        this._hidden = false;
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    do_toggle: function (display) {
        this._hidden = _.isBoolean(display) ? !display : !this._hidden;
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Close this window
     *
     * @abstract
     */
    close: function () {},
    /**
     * Get the ID of the thread window, which is equivalent to the ID of the
     * thread related to this window
     *
     * @returns {integer|string}
     */
    getID: function () {
        return this._getThreadID();
    },
    /**
     * @returns {mail.model.Thread|undefined}
     */
    getThread: function () {
        if (!this.hasThread()) {
            return undefined;
        }
        return this._thread;
    },
    /**
     * Get the status of the thread, such as the im status of a DM chat
     * ('online', 'offline', etc.). If this window has no thread, returns
     * `undefined`.
     *
     * @returns {string|undefined}
     */
    getThreadStatus: function () {
        if (!this.hasThread()) {
            return undefined;
        }
        return this._thread.getStatus();
    },
    /**
     * Get the title of the thread window, which usually contains the name of
     * the thread.
     *
     * @returns {string}
     */
    getTitle: function () {
        if (!this.hasThread()) {
            return _t("Undefined");
        }
        return this._thread.getTitle();
    },
    /**
     * Get the unread counter of the related thread. If there are no thread
     * linked to this window, returns 0.
     *
     * @returns {integer}
     */
    getUnreadCounter: function () {
        if (!this.hasThread()) {
            return 0;
        }
        return this._thread.getUnreadCounter();
    },
    /**
     * States whether this thread window is related to a thread or not.
     *
     * This is useful in order to provide specific behaviour for thread windows
     * without any thread, e.g. let them open a thread from this "blank" thread
     * window.
     *
     * @returns {boolean}
     */
    hasThread: function () {
        return !! this._thread;
    },
    /**
     * Tells whether the bottom of the thread in the thread window is visible
     * or not.
     *
     * @returns {boolean}
     */
    isAtBottom: function () {
        return this._threadWidget.isAtBottom();
    },
    /**
     * State whether the related thread is folded or not. If there are no
     * thread related to this window, it means this is the "blank" thread
     * window, therefore we use the internal folded state.
     *
     * @returns {boolean}
     */
    isFolded: function () {
        if (!this.hasThread()) {
            return this._folded;
        }
        return this._thread.isFolded();
    },
    /**
     * States whether the current environment is in mobile or not. This is
     * useful in order to customize the template rendering for mobile view.
     *
     * @returns {boolean}
     */
    isMobile: function () {
        return config.device.isMobile;
    },
    /**
     * States whether the thread window is hidden or not.
     *
     * @returns {boolean}
     */
    isHidden: function () {
        return this._hidden;
    },
    /**
     * States whether the input of the thread window should be displayed or not.
     * By default, any thread window with a thread needs a composer.
     *
     * @returns {boolean}
     */
    needsComposer: function () {
        return this.hasThread();
    },
    /**
     * Render the thread window
     */
    render: function () {
        this.renderHeader();
        if (this.hasThread()) {
            this._threadWidget.render(this._thread, { displayLoadMore: false });
        }
    },
    /**
     * Render the header of this thread window.
     * This is useful when some information on the header have be updated such
     * as the status or the title of the thread that have changed.
     *
     * @private
     */
    renderHeader: function () {
        var options = this._getHeaderRenderingOptions();
        this.$header.html(
            QWeb.render('im_livechat.legacy.mail.AbstractThreadWindow.HeaderContent', options));
    },
    /**
     * Scroll to the bottom of the thread in the thread window
     */
    scrollToBottom: function () {
        this._threadWidget.scrollToBottom();
    },
    /**
     * Toggle the fold state of this thread window. Also update the fold state
     * of the thread model. If the boolean parameter `folded` is provided, it
     * folds/unfolds the window when it is set/unset.
     *
     * @param {boolean} [folded] if not a boolean, toggle the fold state.
     *   Otherwise, fold/unfold the window if set/unset.
     */
    toggleFold: function (folded) {
        if (!_.isBoolean(folded)) {
            folded = !this.isFolded();
        }
        this._updateThreadFoldState(folded);
    },
    /**
     * Update the visual state of the window so that it matched the internal
     * fold state. This is useful in case the related thread has its fold state
     * that has been changed.
     */
    updateVisualFoldState: function () {
        if (!this.isFolded()) {
            this._threadWidget.scrollToBottom();
            if (this.options.autofocus) {
                this._focusInput();
            }
        }
        var height = this.isFolded() ? this.HEIGHT_FOLDED : this.HEIGHT_OPEN;
        this.$el.css({ height: height });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Set the focus on the composer of the thread window. This operation is
     * ignored in mobile context.
     *
     * @private
     * Set the focus on the input of the window
     */
    _focusInput: function () {
        if (
            config.device.touch &&
            config.device.size_class <= config.device.SIZES.SM
        ) {
            return;
        }
        this.$input.focus();
    },
    /**
     * Returns the options used by the rendering of the window's header
     *
     * @private
     * @returns {Object}
     */
    _getHeaderRenderingOptions: function () {
        return {
            status: this.getThreadStatus(),
            thread: this.getThread(),
            title: this.getTitle(),
            unreadCounter: this.getUnreadCounter(),
            widget: this,
        };
    },
    /**
     * Get the ID of the related thread.
     * If this window is not related to a thread, it means this is the "blank"
     * thread window, therefore it returns "_blank" as its ID.
     *
     * @private
     * @returns {integer|string} the threadID, or '_blank' for the window that
     *   is not related to any thread.
     */
    _getThreadID: function () {
        if (!this.hasThread()) {
            return '_blank';
        }
        return this._thread.getID();
    },
    /**
     * Tells whether there is focus on this thread. Note that a thread that has
     * the focus means the input has focus.
     *
     * @private
     * @returns {boolean}
     */
    _hasFocus: function () {
        return this.$input.is(':focus');
    },
    /**
     * Post a message on this thread window, and auto-scroll to the bottom of
     * the thread.
     *
     * @private
     * @param {Object} messageData
     */
    _postMessage: function (messageData) {
        var self = this;
        if (!this.hasThread()) {
            return;
        }
        this._thread.postMessage(messageData)
            .then(function () {
                self._threadWidget.scrollToBottom();
            });
    },
    /**
     * Update the fold state of the thread.
     *
     * This function is called when toggling the fold state of this window.
     * If there is no thread linked to this window, it means this is the
     * "blank" thread window, therefore we use the internal state 'folded'
     *
     * @private
     * @param {boolean} folded
     */
    _updateThreadFoldState: function (folded) {
        if (this.hasThread()) {
            this._thread.fold(folded);
        } else {
            this._folded = folded;
            this.updateVisualFoldState();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Close the thread window.
     * Mark the thread as read if the thread window was open.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (
            this.hasThread() &&
            this._thread.getUnreadCounter() > 0 &&
            !this.isFolded()
        ) {
            this._thread.markAsRead();
        }
        this.close();
    },
    /**
     * Fold/unfold the thread window.
     * Also mark the thread as read.
     *
     * @private
     */
    _onClickFold: function () {
        if (!config.device.isMobile) {
            this.toggleFold();
        }
    },
    /**
     * Called when the composer is clicked -> forces focus on input even if
     * jquery's blockUI is enabled.
     *
     * @private
     * @param {Event} ev
     */
    _onComposerClick: function (ev) {
        if ($(ev.target).closest('a, button').length) {
            return;
        }
        this._focusInput();
    },
    /**
     * @private
     */
    _onDocumentViewerClose: function () {
        this._focusInput();
    },
    /**
     * Called when typing something on the composer of this thread window.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown: function (ev) {
        ev.stopPropagation(); // to prevent jquery's blockUI to cancel event
        // ENTER key (avoid requiring jquery ui for external livechat)
        if (ev.which === 13) {
            var content = _.str.trim(this.$input.val());
            var messageData = {
                content: content,
                attachment_ids: [],
                partner_ids: [],
            };
            this.$input.val('');
            if (content) {
                this._postMessage(messageData);
            }
        }
    },
    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeypress: function (ev) {
        ev.stopPropagation(); // to prevent jquery's blockUI to cancel event
    },
    /**
     * @private
     */
    _onScroll: function () {
        if (this.hasThread() && this.isAtBottom()) {
            this._thread.markAsRead();
        }
    },
    /**
     * When a thread window is clicked on, we want to give the focus to the main
     * input. An exception is made when the user is selecting something.
     *
     * @private
     */
    _onThreadWindowClicked: function () {
        var selectObj = window.getSelection();
        if (selectObj.anchorOffset === selectObj.focusOffset) {
            this.$input.focus();
        }
    },
});

return AbstractThreadWindow;

});

odoo.define('im_livechat.legacy.mail.model.CCThrottleFunctionObject', function (require) {
"use strict";

var Class = require('web.Class');

/**
 * This object models the behaviour of the clearable and cancellable (CC)
 * throttle version of a provided function.
 */
var CCThrottleFunctionObject = Class.extend({

    /**
     * @param {Object} params
     * @param {integer} params.duration duration of the 'cooldown' phase, i.e.
     *   the minimum duration between the most recent function call that has
     *   been made and the following function call.
     * @param {function} params.func provided function for making the CC
     *   throttled version.
     */
    init: function (params) {
        this._arguments = undefined;
        this._cooldownTimeout = undefined;
        this._duration = params.duration;
        this._func = params.func;
        this._shouldCallFunctionAfterCD = false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Cancel any buffered function call, but keep the cooldown phase running.
     */
    cancel: function () {
        this._arguments = undefined;
        this._shouldCallFunctionAfterCD = false;
    },
    /**
     * Clear the internal throttle timer, so that the following function call
     * is immediate. For instance, if there is a cooldown stage, it is aborted.
     */
    clear: function () {
        if (this._cooldownTimeout) {
            clearTimeout(this._cooldownTimeout);
            this._onCooldownTimeout();
        }
    },
    /**
     * Called when there is a call to the function. This function is throttled,
     * so the time it is called depends on whether the "cooldown stage" occurs
     * or not:
     *
     * - no cooldown stage: function is called immediately, and it starts
     *      the cooldown stage when successful.
     * - in cooldown stage: function is called when the cooldown stage has
     *      ended from timeout.
     *
     * Note that after the cooldown stage, only the last attempted function
     * call will be considered.
     */
    do: function () {
        this._arguments = Array.prototype.slice.call(arguments);
        if (this._cooldownTimeout === undefined) {
            this._callFunction();
        } else {
            this._shouldCallFunctionAfterCD = true;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Immediately calls the function with arguments of last buffered function
     * call. It initiates the cooldown stage after this function call.
     *
     * @private
     */
    _callFunction: function () {
        this._func.apply(null, this._arguments);
        this._cooldown();
    },
    /**
     * Called when the function has been successfully called. The following
     * calls to the function with this object should suffer a "cooldown stage",
     * which prevents the function from being called until this stage has ended.
     *
     * @private
     */
    _cooldown: function () {
        this.cancel();
        this._cooldownTimeout = setTimeout(
            this._onCooldownTimeout.bind(this),
            this._duration
        );
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the cooldown stage ended from timeout. Calls the function if
     * a function call was buffered.
     *
     * @private
     */
    _onCooldownTimeout: function () {
        if (this._shouldCallFunctionAfterCD) {
            this._callFunction();
        } else {
            this._cooldownTimeout = undefined;
        }
    },
});

return CCThrottleFunctionObject;

});

odoo.define('im_livechat.legacy.mail.model.CCThrottleFunction', function (require) {
"use strict";

var CCThrottleFunctionObject = require('im_livechat.legacy.mail.model.CCThrottleFunctionObject');

/**
 * A function that creates a cancellable and clearable (CC) throttle version
 * of a provided function.
 *
 * This throttle mechanism allows calling a function at most once during a
 * certain period:
 *
 * - When a function call is made, it enters a 'cooldown' phase, in which any
 *     attempt to call the function is buffered until the cooldown phase ends.
 * - At most 1 function call can be buffered during the cooldown phase, and the
 *     latest one in this phase will be considered at its end.
 * - When a cooldown phase ends, any buffered function call will be performed
 *     and another cooldown phase will follow up.
 *
 * This throttle version has the following interesting properties:
 *
 * - cancellable: it allows removing a buffered function call during the
 *     cooldown phase, but it keeps the cooldown phase running.
 * - clearable: it allows to clear the internal clock of the throttled function,
 *     so that any cooldown phase is immediately ending.
 *
 * @param {Object} params
 * @param {integer} params.duration a duration for the throttled behaviour,
 *   in milli-seconds.
 * @param {function} params.func the function to throttle
 * @returns {function} the cancellable and clearable throttle version of the
 *   provided function in argument.
 */
var CCThrottleFunction = function (params) {
    var duration = params.duration;
    var func = params.func;

    var throttleFunctionObject = new CCThrottleFunctionObject({
        duration: duration,
        func: func,
    });

    var callable = function () {
        return throttleFunctionObject.do.apply(throttleFunctionObject, arguments);
    };
    callable.cancel = function () {
        throttleFunctionObject.cancel();
    };
    callable.clear = function () {
        throttleFunctionObject.clear();
    };

    return callable;
};

return CCThrottleFunction;

});

odoo.define('im_livechat.legacy.mail.model.Timer', function (require) {
"use strict";

var Class = require('web.Class');

/**
 * This class creates a timer which, when times out, calls a function.
 */
var Timer = Class.extend({

    /**
     * Instantiate a new timer. Note that the timer is not started on
     * initialization (@see start method).
     *
     * @param {Object} params
     * @param {number} params.duration duration of timer before timeout in
     *   milli-seconds.
     * @param {function} params.onTimeout function that is called when the
     *   timer times out.
     */
    init: function (params) {
        this._duration = params.duration;
        this._timeout = undefined;
        this._timeoutCallback = params.onTimeout;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Clears the countdown of the timer.
     */
    clear: function () {
        clearTimeout(this._timeout);
    },
    /**
     * Resets the timer, i.e. resets its duration.
     */
    reset: function () {
        this.clear();
        this.start();
    },
    /**
     * Starts the timer, i.e. after a certain duration, it times out and calls
     * a function back.
     */
    start: function () {
        this._timeout = setTimeout(this._onTimeout.bind(this), this._duration);
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Called when the timer times out, calls back a function on timeout.
     *
     * @private
     */
    _onTimeout: function () {
        this._timeoutCallback();
    },

});

return Timer;

});

odoo.define('im_livechat.legacy.mail.model.Timers', function (require) {
"use strict";

var Timer = require('im_livechat.legacy.mail.model.Timer');

var Class = require('web.Class');

/**
 * This class lists several timers that use a same callback and duration.
 */
var Timers = Class.extend({

    /**
     * Instantiate a new list of timers
     *
     * @param {Object} params
     * @param {integer} params.duration duration of the underlying timers from
     *   start to timeout, in milli-seconds.
     * @param {function} params.onTimeout a function to call back for underlying
     *   timers on timeout.
     */
    init: function (params) {
        this._duration = params.duration;
        this._timeoutCallback = params.onTimeout;
        this._timers = {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Register a timer with ID `timerID` to start.
     *
     * - an already registered timer with this ID is reset.
     * - (optional) can provide a list of arguments that is passed to the
     *   function callback when timer times out.
     *
     * @param {Object} params
     * @param {Array} [params.timeoutCallbackArguments]
     * @param {integer} params.timerID
     */
    registerTimer: function (params) {
        var timerID = params.timerID;
        if (this._timers[timerID]) {
            this._timers[timerID].clear();
        }
        var timerParams = {
            duration: this._duration,
            onTimeout: this._timeoutCallback,
        };
        if ('timeoutCallbackArguments' in params) {
            timerParams.onTimeout = this._timeoutCallback.bind.apply(
                this._timeoutCallback,
                [null].concat(params.timeoutCallbackArguments)
            );
        } else {
            timerParams.onTimeout = this._timeoutCallback;
        }
        this._timers[timerID] = new Timer(timerParams);
        this._timers[timerID].start();
    },
    /**
     * Unregister a timer with ID `timerID`. The unregistered timer is aborted
     * and will not time out.
     *
     * @param {Object} params
     * @param {integer} params.timerID
     */
    unregisterTimer: function (params) {
        var timerID = params.timerID;
        if (this._timers[timerID]) {
            this._timers[timerID].clear();
            delete this._timers[timerID];
        }
    },

});

return Timers;

});

odoo.define('im_livechat.legacy.mail.widget.Thread', function (require) {
"use strict";

var DocumentViewer = require('im_livechat.legacy.mail.DocumentViewer');
var mailUtils = require('mail.utils');

var core = require('web.core');
var time = require('web.time');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _lt = core._lt;

var ORDER = {
    ASC: 1, // visually, ascending order of message IDs (from top to bottom)
    DESC: -1, // visually, descending order of message IDs (from top to bottom)
};

var READ_MORE = _lt("read more");
var READ_LESS = _lt("read less");

/**
 * This is a generic widget to render a thread.
 * Any thread that extends mail.model.AbstractThread can be used with this
 * widget.
 */
var ThreadWidget = Widget.extend({
    className: 'o_mail_thread',

    events: {
        'click a': '_onClickRedirect',
        'click img': '_onClickRedirect',
        'click strong': '_onClickRedirect',
        'click .o_thread_show_more': '_onClickShowMore',
        'click .o_attachment_download': '_onAttachmentDownload',
        'click .o_attachment_view': '_onAttachmentView',
        'click .o_attachment_delete_cross': '_onDeleteAttachment',
        'click .o_thread_message_needaction': '_onClickMessageNeedaction',
        'click .o_thread_message_star': '_onClickMessageStar',
        'click .o_thread_message_reply': '_onClickMessageReply',
        'click .oe_mail_expand': '_onClickMailExpand',
        'click .o_thread_message': '_onClickMessage',
        'click': '_onClick',
        'click .o_thread_message_notification_error': '_onClickMessageNotificationError',
        'click .o_thread_message_moderation': '_onClickMessageModeration',
        'change .moderation_checkbox': '_onChangeModerationCheckbox',
    },

    /**
     * @override
     * @param {widget} parent
     * @param {Object} options
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.attachments = [];
        // options when the thread is enabled (e.g. can send message,
        // interact on messages, etc.)
        this._enabledOptions = _.defaults(options || {}, {
            displayOrder: ORDER.ASC,
            displayMarkAsRead: true,
            displayModerationCommands: false,
            displayStars: true,
            displayDocumentLinks: true,
            displayAvatars: true,
            squashCloseMessages: true,
            displayNotificationIcons: true,
            displayReplyIcons: false,
            loadMoreOnScroll: false,
            hasMessageAttachmentDeletable: false,
        });
        // options when the thread is disabled
        this._disabledOptions = {
            displayOrder: this._enabledOptions.displayOrder,
            displayMarkAsRead: false,
            displayModerationCommands: false,
            displayStars: false,
            displayDocumentLinks: false,
            displayAvatars: this._enabledOptions.displayAvatars,
            squashCloseMessages: false,
            displayNotificationIcons: false,
            displayReplyIcons: false,
            loadMoreOnScroll: this._enabledOptions.loadMoreOnScroll,
            hasMessageAttachmentDeletable: false,
        };
        this._selectedMessageID = null;
        this._currentThreadID = null;
        this._messageMailPopover = null;
        this._messageSeenPopover = null;
        // used to track popover IDs to destroy on re-rendering of popovers
        this._openedSeenPopoverIDs = [];
    },
    /**
     * The message mail popover may still be shown at this moment. If we do not
     * remove it, it stays visible on the page until a page reload.
     *
     * @override
     */
    destroy: function () {
        clearInterval(this._updateTimestampsInterval);
        if (this._messageMailPopover) {
            this._messageMailPopover.popover('hide');
        }
        if (this._messageSeenPopover) {
            this._messageSeenPopover.popover('hide');
        }
        this._destroyOpenSeenPopoverIDs();
        this._super();
    },
    /**
     * @param {im_livechat.legacy.mail.model.AbstractThread} thread the thread to render.
     * @param {Object} [options]
     * @param {integer} [options.displayOrder=ORDER.ASC] order of displaying
     *    messages in the thread:
     *      - ORDER.ASC: last message is at the bottom of the thread
     *      - ORDER.DESC: last message is at the top of the thread
     * @param {boolean} [options.displayLoadMore]
     * @param {Array} [options.domain=[]] the domain for the messages in the
     *    thread.
     * @param {boolean} [options.isCreateMode]
     * @param {boolean} [options.scrollToBottom=false]
     * @param {boolean} [options.squashCloseMessages]
     */
    render: function (thread, options) {
        var self = this;

        var shouldScrollToBottomAfterRendering = false;
        if (this._currentThreadID === thread.getID() && this.isAtBottom()) {
            shouldScrollToBottomAfterRendering = true;
        }
        this._currentThreadID = thread.getID();

        // copy so that reverse do not alter order in the thread object
        var messages = _.clone(thread.getMessages({ domain: options.domain || [] }));

        var modeOptions = options.isCreateMode ? this._disabledOptions :
                                                    this._enabledOptions;

        // attachments ordered by messages order (increasing ID)
        this.attachments = _.uniq(_.flatten(_.map(messages, function (message) {
            return message.getAttachments();
        })));

        options = _.extend({}, modeOptions, options, {
            selectedMessageID: this._selectedMessageID,
        });

        // dict where key is message ID, and value is whether it should display
        // the author of message or not visually
        var displayAuthorMessages = {};

        // Hide avatar and info of a message if that message and the previous
        // one are both comments wrote by the same author at the same minute
        // and in the same document (users can now post message in documents
        // directly from a channel that follows it)
        var prevMessage;
        _.each(messages, function (message) {
            if (
                // is first message of thread
                !prevMessage ||
                // more than 1 min. elasped
                (Math.abs(message.getDate().diff(prevMessage.getDate())) > 60000) ||
                prevMessage.getType() !== 'comment' ||
                message.getType() !== 'comment' ||
                // from a different author
                (prevMessage.getAuthorID() !== message.getAuthorID()) ||
                (
                    // messages are linked to a document thread
                    (
                        prevMessage.isLinkedToDocumentThread() &&
                        message.isLinkedToDocumentThread()
                    ) &&
                    (
                        // are from different documents
                        prevMessage.getDocumentModel() !== message.getDocumentModel() ||
                        prevMessage.getDocumentID() !== message.getDocumentID()
                    )
                )
            ) {
                displayAuthorMessages[message.getID()] = true;
            } else {
                displayAuthorMessages[message.getID()] = !options.squashCloseMessages;
            }
            prevMessage = message;
        });

        if (modeOptions.displayOrder === ORDER.DESC) {
            messages.reverse();
        }

        this.$el.html(QWeb.render('im_livechat.legacy.mail.widget.Thread', {
            thread: thread,
            displayAuthorMessages: displayAuthorMessages,
            options: options,
            ORDER: ORDER,
            dateFormat: time.getLangDatetimeFormat(),
        }));

        _.each(messages, function (message) {
            var $message = self.$('.o_thread_message[data-message-id="' + message.getID() + '"]');
            $message.find('.o_mail_timestamp').data('date', message.getDate());

            self._insertReadMore($message);
        });

        if (shouldScrollToBottomAfterRendering) {
            this.scrollToBottom();
        }

        if (!this._updateTimestampsInterval) {
            this.updateTimestampsInterval = setInterval(function () {
                self._updateTimestamps();
            }, 1000 * 60);
        }

        this._renderMessageNotificationPopover(messages);
        if (thread.hasSeenFeature()) {
            this._renderMessageSeenPopover(thread, messages);
        }
    },

    /**
     * Render thread widget when loading, i.e. when messaging is not yet ready.
     * @see /mail/init_messaging
     */
    renderLoading: function () {
        this.$el.html(QWeb.render('im_livechat.legacy.mail.widget.ThreadLoading'));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    getScrolltop: function () {
        return this.$el.scrollTop();
    },
    /**
     * State whether the bottom of the thread is visible or not,
     * with a tolerance of 5 pixels
     *
     * @return {boolean}
     */
    isAtBottom: function () {
        var fullHeight = this.el.scrollHeight;
        var topHiddenHeight = this.$el.scrollTop();
        var visibleHeight = this.$el.outerHeight();
        var bottomHiddenHeight = fullHeight - topHiddenHeight - visibleHeight;
        return bottomHiddenHeight < 5;
    },
    /**
     * Removes a message and re-renders the thread
     *
     * @param {integer} [messageID] the id of the removed message
     * @param {mail.model.AbstractThread} thread the thread which contains
     *   updated list of messages (so it does not contain any message with ID
     *   `messageID`).
     * @param {Object} [options] options for the thread rendering
     */
    removeMessageAndRender: function (messageID, thread, options) {
        var self = this;
        this._currentThreadID = thread.getID();
        return new Promise(function (resolve, reject) {
            self.$('.o_thread_message[data-message-id="' + messageID + '"]')
            .fadeOut({
                done: function () {
                    if (self._currentThreadID === thread.getID()) {
                        self.render(thread, options);
                    }
                    resolve();
                },
                duration: 200,
            });
        });
    },
    /**
     * Scroll to the bottom of the thread
     */
    scrollToBottom: function () {
        this.$el.scrollTop(this.el.scrollHeight);
    },
    /**
     * Scrolls the thread to a given message
     *
     * @param {integer} options.msgID the ID of the message to scroll to
     * @param {integer} [options.duration]
     * @param {boolean} [options.onlyIfNecessary]
     */
    scrollToMessage: function (options) {
        var $target = this.$('.o_thread_message[data-message-id="' + options.messageID + '"]');
        if (options.onlyIfNecessary) {
            var delta = $target.parent().height() - $target.height();
            var offset = delta < 0 ?
                            0 :
                            delta - ($target.offset().top - $target.offsetParent().offset().top);
            offset = - Math.min(offset, 0);
            this.$el.scrollTo("+=" + offset + "px", options.duration);
        } else if ($target.length) {
            this.$el.scrollTo($target);
        }
    },
    /**
     * Scroll to the specific position in pixel
     *
     * If no position is provided, scroll to the bottom of the thread
     *
     * @param {integer} [position] distance from top to position in pixels.
     *    If not provided, scroll to the bottom.
     */
    scrollToPosition: function (position) {
        if (position) {
            this.$el.scrollTop(position);
        } else {
            this.scrollToBottom();
        }
    },
    /**
     * Toggle all the moderation checkboxes in the thread
     *
     * @param {boolean} checked if true, check the boxes,
     *      otherwise uncheck them.
     */
    toggleModerationCheckboxes: function (checked) {
        this.$('.moderation_checkbox').prop('checked', checked);
    },
    /**
     * Unselect the selected message
     */
    unselectMessage: function () {
        this.$('.o_thread_message').removeClass('o_thread_selected_message');
        this._selectedMessageID = null;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _destroyOpenSeenPopoverIDs: function () {
        _.each(this._openedSeenPopoverIDs, function (popoverID) {
            $('#' + popoverID).remove();
        });
        this._openedSeenPopoverIDs = [];
    },
    /**
     * Modifies $element to add the 'read more/read less' functionality
     * All element nodes with 'data-o-mail-quote' attribute are concerned.
     * All text nodes after a ``#stopSpelling`` element are concerned.
     * Those text nodes need to be wrapped in a span (toggle functionality).
     * All consecutive elements are joined in one 'read more/read less'.
     *
     * @private
     * @param {jQuery} $element
     */
    _insertReadMore: function ($element) {
        var self = this;

        var groups = [];
        var readMoreNodes;

        // nodeType 1: element_node
        // nodeType 3: text_node
        var $children = $element.contents()
            .filter(function () {
                return this.nodeType === 1 ||
                        this.nodeType === 3 &&
                        this.nodeValue.trim();
            });

        _.each($children, function (child) {
            var $child = $(child);

            // Hide Text nodes if "stopSpelling"
            if (
                child.nodeType === 3 &&
                $child.prevAll('[id*="stopSpelling"]').length > 0
            ) {
                // Convert Text nodes to Element nodes
                $child = $('<span>', {
                    text: child.textContent,
                    'data-o-mail-quote': '1',
                });
                child.parentNode.replaceChild($child[0], child);
            }

            // Create array for each 'read more' with nodes to toggle
            if (
                $child.attr('data-o-mail-quote') ||
                (
                    $child.get(0).nodeName === 'BR' &&
                    $child.prev('[data-o-mail-quote="1"]').length > 0
                )
            ) {
                if (!readMoreNodes) {
                    readMoreNodes = [];
                    groups.push(readMoreNodes);
                }
                $child.hide();
                readMoreNodes.push($child);
            } else {
                readMoreNodes = undefined;
                self._insertReadMore($child);
            }
        });

        _.each(groups, function (group) {
            // Insert link just before the first node
            var $readMore = $('<a>', {
                class: 'o_mail_read_more',
                href: '#',
                text: READ_MORE,
            }).insertBefore(group[0]);

            // Toggle All next nodes
            var isReadMore = true;
            $readMore.click(function (e) {
                e.preventDefault();
                isReadMore = !isReadMore;
                _.each(group, function ($child) {
                    $child.hide();
                    $child.toggle(!isReadMore);
                });
                $readMore.text(isReadMore ? READ_MORE : READ_LESS);
            });
        });
    },
    /**
    * @private
    * @param {MouseEvent} ev
    */
    _onDeleteAttachment: function (ev) {
        ev.stopPropagation();
        var $target = $(ev.currentTarget);
        this.trigger_up('delete_attachment', {
            attachmentId: $target.data('id'),
            attachmentName: $target.data('name')
        });
        },
    /**
     * @private
     * @param {Object} options
     * @param {integer} [options.channelID]
     * @param {string} options.model
     * @param {integer} options.id
     */
    _redirect: _.debounce(function (options) {
        if ('channelID' in options) {
            this.trigger('redirect_to_channel', options.channelID);
        } else {
            this.trigger('redirect', options.model, options.id);
        }
    }, 500, true),
    /**
     * Render the popover when mouse-hovering on the notification icon of a
     * message in the thread.
     * There is at most one such popover at any given time.
     *
     * @private
     * @param {im_livechat.legacy.mail.model.AbstractMessage[]} messages list of messages in the
     *   rendered thread, for which popover on mouseover interaction is
     *   permitted.
     */
    _renderMessageNotificationPopover(messages) {
        if (this._messageMailPopover) {
            this._messageMailPopover.popover('hide');
        }
        if (!this.$('.o_thread_tooltip').length) {
            return;
        }
        this._messageMailPopover = this.$('.o_thread_tooltip').popover({
            html: true,
            boundary: 'viewport',
            placement: 'auto',
            trigger: 'hover',
            offset: '0, 1',
            content: function () {
                var messageID = $(this).data('message-id');
                var message = _.find(messages, function (message) {
                    return message.getID() === messageID;
                });
                return QWeb.render('im_livechat.legacy.mail.widget.Thread.Message.MailTooltip', {
                    notifications: message.getNotifications(),
                });
            },
        });
    },
    /**
     * Render the popover when mouse hovering on the seen icon of a message
     * in the thread. Only seen icons in non-squashed message have popover,
     * because squashed messages hides this icon on message mouseover.
     *
     * @private
     * @param {im_livechat.legacy.mail.model.AbstractThread} thread with thread seen mixin,
     *   @see {im_livechat.legacy.mail.model.ThreadSeenMixin}
     * @param {im_livechat.legacy.mail.model.Message[]} messages list of messages in the
     *   rendered thread.
     */
    _renderMessageSeenPopover: function (thread, messages) {
        var self = this;
        this._destroyOpenSeenPopoverIDs();
        if (this._messageSeenPopover) {
            this._messageSeenPopover.popover('hide');
        }
        if (!this.$('.o_thread_message_core .o_mail_thread_message_seen_icon').length) {
            return;
        }
        this._messageSeenPopover = this.$('.o_thread_message_core .o_mail_thread_message_seen_icon').popover({
            html: true,
            boundary: 'viewport',
            placement: 'auto',
            trigger: 'hover',
            offset: '0, 1',
            content: function () {
                var $this = $(this);
                self._openedSeenPopoverIDs.push($this.attr('aria-describedby'));
                var messageID = $this.data('message-id');
                var message = _.find(messages, function (message) {
                    return message.getID() === messageID;
                });
                return QWeb.render('im_livechat.legacy.mail.widget.Thread.Message.SeenIconPopoverContent', {
                    thread: thread,
                    message: message,
                });
            },
        });
    },
    /**
     * @private
     */
    _updateTimestamps: function () {
        var isAtBottom = this.isAtBottom();
        this.$('.o_mail_timestamp').each(function () {
            var date = $(this).data('date');
            $(this).html(mailUtils.timeFromNow(date));
        });
        if (isAtBottom && !this.isAtBottom()) {
            this.scrollToBottom();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAttachmentDownload: function (event) {
        event.stopPropagation();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAttachmentView: function (event) {
        event.stopPropagation();
        var activeAttachmentID = $(event.currentTarget).data('id');
        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, this.attachments, activeAttachmentID);
            attachmentViewer.appendTo($('body'));
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeModerationCheckbox: function (ev) {
        this.trigger_up('update_moderation_buttons');
    },
    /**
     * @private
     */
    _onClick: function () {
        if (this._selectedMessageID) {
            this.unselectMessage();
            this.trigger('unselect_message');
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMailExpand: function (ev) {
        ev.preventDefault();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessage: function (ev) {
        $(ev.currentTarget).toggleClass('o_thread_selected_message');
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageNeedaction: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        this.trigger('mark_as_read', messageID);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageNotificationError(ev) {
        const messageID = $(ev.currentTarget).data('message-id');
        this.do_action('mail.mail_resend_message_action', {
            additional_context: {
                mail_message_to_resend: messageID,
            }
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageReply: function (ev) {
        this._selectedMessageID = $(ev.currentTarget).data('message-id');
        this.$('.o_thread_message').removeClass('o_thread_selected_message');
        this.$('.o_thread_message[data-message-id="' + this._selectedMessageID + '"]')
            .addClass('o_thread_selected_message');
        this.trigger('select_message', this._selectedMessageID);
        ev.stopPropagation();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageStar: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        this.trigger('toggle_star_status', messageID);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageModeration: function (ev) {
        var $button = $(ev.currentTarget);
        var messageID = $button.data('message-id');
        var decision = $button.data('decision');
        this.trigger_up('message_moderation', {
            messageID: messageID,
            decision: decision,
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRedirect: function (ev) {
        // ignore inherited branding
        if ($(ev.target).data('oe-field') !== undefined) {
            return;
        }
        var id = $(ev.target).data('oe-id');
        if (id) {
            ev.preventDefault();
            var model = $(ev.target).data('oe-model');
            var options;
            if (model && (model !== 'mail.channel')) {
                options = {
                    model: model,
                    id: id
                };
            } else {
                options = { channelID: id };
            }
            this._redirect(options);
        }
    },
    /**
     * @private
     */
    _onClickShowMore: function () {
        this.trigger('load_more_messages');
    },
});

ThreadWidget.ORDER = ORDER;

return ThreadWidget;

});

odoo.define('im_livechat.legacy.mail.DocumentViewer', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var SCROLL_ZOOM_STEP = 0.1;
var ZOOM_STEP = 0.5;

var DocumentViewer = Widget.extend({
    template: "im_livechat.legacy.mail.DocumentViewer",
    events: {
        'click .o_download_btn': '_onDownload',
        'click .o_viewer_img': '_onImageClicked',
        'click .o_viewer_video': '_onVideoClicked',
        'click .move_next': '_onNext',
        'click .move_previous': '_onPrevious',
        'click .o_rotate': '_onRotate',
        'click .o_zoom_in': '_onZoomIn',
        'click .o_zoom_out': '_onZoomOut',
        'click .o_zoom_reset': '_onZoomReset',
        'click .o_close_btn, .o_viewer_img_wrapper': '_onClose',
        'click .o_print_btn': '_onPrint',
        'DOMMouseScroll .o_viewer_content': '_onScroll', // Firefox
        'mousewheel .o_viewer_content': '_onScroll', // Chrome, Safari, IE
        'keydown': '_onKeydown',
        'keyup': '_onKeyUp',
        'mousedown .o_viewer_img': '_onStartDrag',
        'mousemove .o_viewer_content': '_onDrag',
        'mouseup .o_viewer_content': '_onEndDrag'
    },
    /**
     * The documentViewer takes an array of objects describing attachments in
     * argument, and the ID of an active attachment (the one to display first).
     * Documents that are not of type image or video are filtered out.
     *
     * @override
     * @param {Array<Object>} attachments list of attachments
     * @param {integer} activeAttachmentID
     */
    init: function (parent, attachments, activeAttachmentID) {
        this._super.apply(this, arguments);
        this.attachment = _.filter(attachments, function (attachment) {
            var match = attachment.type === 'url' ? attachment.url.match("(youtu|.png|.jpg|.gif)") : attachment.mimetype.match("(image|video|application/pdf|text)");
            if (match) {
                attachment.fileType = match[1];
                if (match[1].match("(.png|.jpg|.gif)")) {
                    attachment.fileType = 'image';
                }
                if (match[1] === 'youtu') {
                    var youtube_array = attachment.url.split('/');
                    var youtube_token = youtube_array[youtube_array.length - 1];
                    if (youtube_token.indexOf('watch') !== -1) {
                        youtube_token = youtube_token.split('v=')[1];
                        var amp = youtube_token.indexOf('&');
                        if (amp !== -1) {
                            youtube_token = youtube_token.substring(0, amp);
                        }
                    }
                    attachment.youtube = youtube_token;
                }
                return true;
            }
        });
        this.activeAttachment = _.findWhere(attachments, { id: activeAttachmentID });
        this.modelName = 'ir.attachment';
        this._reset();
    },
    /**
     * Open a modal displaying the active attachment
     * @override
     */
    start: function () {
        this.$el.modal('show');
        this.$el.on('hidden.bs.modal', _.bind(this._onDestroy, this));
        this.$('.o_viewer_img').on("load", _.bind(this._onImageLoaded, this));
        this.$('[data-toggle="tooltip"]').tooltip({ delay: 0 });
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.isDestroyed()) {
            return;
        }
        this.trigger_up('document_viewer_closed');
        this.$el.modal('hide');
        this.$el.remove();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------------

    /**
     * @private
     */
    _next: function () {
        var index = _.findIndex(this.attachment, this.activeAttachment);
        index = (index + 1) % this.attachment.length;
        this.activeAttachment = this.attachment[index];
        this._updateContent();
    },
    /**
     * @private
     */
    _previous: function () {
        var index = _.findIndex(this.attachment, this.activeAttachment);
        index = index === 0 ? this.attachment.length - 1 : index - 1;
        this.activeAttachment = this.attachment[index];
        this._updateContent();
    },
    /**
     * @private
     */
    _reset: function () {
        this.scale = 1;
        this.dragStartX = this.dragstopX = 0;
        this.dragStartY = this.dragstopY = 0;
    },
    /**
     * Render the active attachment
     *
     * @private
     */
    _updateContent: function () {
        this.$('.o_viewer_content').html(QWeb.render('im_livechat.legacy.mail.DocumentViewer.Content', {
            widget: this
        }));
        this.$('.o_viewer_img').on("load", _.bind(this._onImageLoaded, this));
        this.$('[data-toggle="tooltip"]').tooltip({ delay: 0 });
        this._reset();
    },
    /**
     * Get CSS transform property based on scale and angle
     *
     * @private
     * @param {float} scale
     * @param {float} angle
     */
    _getTransform: function (scale, angle) {
        return 'scale3d(' + scale + ', ' + scale + ', 1) rotate(' + angle + 'deg)';
    },
    /**
     * Rotate image clockwise by provided angle
     *
     * @private
     * @param {float} angle
     */
    _rotate: function (angle) {
        this._reset();
        var new_angle = (this.angle || 0) + angle;
        this.$('.o_viewer_img').css('transform', this._getTransform(this.scale, new_angle));
        this.$('.o_viewer_img').css('max-width', new_angle % 180 !== 0 ? $(document).height() : '100%');
        this.$('.o_viewer_img').css('max-height', new_angle % 180 !== 0 ? $(document).width() : '100%');
        this.angle = new_angle;
    },
    /**
     * Zoom in/out image by provided scale
     *
     * @private
     * @param {integer} scale
     */
    _zoom: function (scale) {
        if (scale > 0.5) {
            this.$('.o_viewer_img').css('transform', this._getTransform(scale, this.angle || 0));
            this.scale = scale;
        }
        this.$('.o_zoom_reset').add('.o_zoom_out').toggleClass('disabled', scale === 1);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} e
     */
    _onClose: function (e) {
        e.preventDefault();
        this.destroy();
    },
    /**
     * When popup close complete destroyed modal even DOM footprint too
     *
     * @private
     */
    _onDestroy: function () {
        this.destroy();
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onDownload: function (e) {
        e.preventDefault();
        window.location = '/web/content/' + this.modelName + '/' + this.activeAttachment.id + '/' + 'datas' + '?download=true';
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onDrag: function (e) {
        e.preventDefault();
        if (this.enableDrag) {
            var $image = this.$('.o_viewer_img');
            var $zoomer = this.$('.o_viewer_zoomer');
            var top = $image.prop('offsetHeight') * this.scale > $zoomer.height() ? e.clientY - this.dragStartY : 0;
            var left = $image.prop('offsetWidth') * this.scale > $zoomer.width() ? e.clientX - this.dragStartX : 0;
            $zoomer.css("transform", "translate3d(" + left + "px, " + top + "px, 0)");
            $image.css('cursor', 'move');
        }
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onEndDrag: function (e) {
        e.preventDefault();
        if (this.enableDrag) {
            this.enableDrag = false;
            this.dragstopX = e.clientX - this.dragStartX;
            this.dragstopY = e.clientY - this.dragStartY;
            this.$('.o_viewer_img').css('cursor', '');
        }
    },
    /**
     * On click of image do not close modal so stop event propagation
     *
     * @private
     * @param {MouseEvent} e
     */
    _onImageClicked: function (e) {
        e.stopPropagation();
    },
    /**
     * Remove loading indicator when image loaded
     * @private
     */
    _onImageLoaded: function () {
        this.$('.o_loading_img').hide();
    },
    /**
     * Move next previous attachment on keyboard right left key
     *
     * @private
     * @param {KeyEvent} e
     */
    _onKeydown: function (e) {
        switch (e.which) {
            case $.ui.keyCode.RIGHT:
                e.preventDefault();
                this._next();
                break;
            case $.ui.keyCode.LEFT:
                e.preventDefault();
                this._previous();
                break;
        }
    },
    /**
     * Close popup on ESCAPE keyup
     *
     * @private
     * @param {KeyEvent} e
     */
    _onKeyUp: function (e) {
        switch (e.which) {
            case $.ui.keyCode.ESCAPE:
                e.preventDefault();
                this._onClose(e);
                break;
        }
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onNext: function (e) {
        e.preventDefault();
        this._next();
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onPrevious: function (e) {
        e.preventDefault();
        this._previous();
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onPrint: function (e) {
        e.preventDefault();
        var src = this.$('.o_viewer_img').prop('src');
        var script = QWeb.render('im_livechat.legacy.mail.PrintImage', {
            src: src
        });
        var printWindow = window.open('about:blank', "_new");
        printWindow.document.open();
        printWindow.document.write(script);
        printWindow.document.close();
    },
    /**
     * Zoom image on scroll
     *
     * @private
     * @param {MouseEvent} e
     */
    _onScroll: function (e) {
        var scale;
        if (e.originalEvent.wheelDelta > 0 || e.originalEvent.detail < 0) {
            scale = this.scale + SCROLL_ZOOM_STEP;
            this._zoom(scale);
        } else {
            scale = this.scale - SCROLL_ZOOM_STEP;
            this._zoom(scale);
        }
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onStartDrag: function (e) {
        e.preventDefault();
        this.enableDrag = true;
        this.dragStartX = e.clientX - (this.dragstopX || 0);
        this.dragStartY = e.clientY - (this.dragstopY || 0);
    },
    /**
     * On click of video do not close modal so stop event propagation
     * and provide play/pause the video instead of quitting it
     *
     * @private
     * @param {MouseEvent} e
     */
    _onVideoClicked: function (e) {
        e.stopPropagation();
        var videoElement = e.target;
        if (videoElement.paused) {
            videoElement.play();
        } else {
            videoElement.pause();
        }
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onRotate: function (e) {
        e.preventDefault();
        this._rotate(90);
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onZoomIn: function (e) {
        e.preventDefault();
        var scale = this.scale + ZOOM_STEP;
        this._zoom(scale);
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onZoomOut: function (e) {
        e.preventDefault();
        var scale = this.scale - ZOOM_STEP;
        this._zoom(scale);
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onZoomReset: function (e) {
        e.preventDefault();
        this.$('.o_viewer_zoomer').css("transform", "");
        this._zoom(1);
    },
});
return DocumentViewer;
});
