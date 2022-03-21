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
    async willStart() {
        var cookie = utils.get_cookie('im_livechat_session');
        if (cookie) {
            var channel = JSON.parse(cookie);
            this._history = await session.rpc('/mail/chat_history', {uuid: channel.uuid, limit: 100});
            this._history.reverse().forEach(message => { message.body = utils.Markup(message.body); });
        } else {
            const result = await session.rpc('/im_livechat/init', {channel_id: this.options.channel_id});
            if (!result.available_for_me) {
                return Promise.reject();
            }
            this._rule = result.rule;
        }
        return this._loadQWebTemplate();
    },
    start: function () {
        this.$el.text(this.options.button_text);
        if (this._history) {
            this._history.forEach(m => this._addMessage(m));
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
     * @param {Object} notification
     * @param {Object} notification.payload
     * @param {string} notification.type
     */
    _handleNotification: function ({ payload, type }) {
        switch (type) {
            case 'im_livechat.history_command': {
                if (payload.id !== this._livechat._id) {
                    return;
                }
                const cookie = utils.get_cookie(LIVECHAT_COOKIE_HISTORY);
                const history = cookie ? JSON.parse(cookie) : [];
                session.rpc('/im_livechat/history', {
                    pid: this._livechat.getOperatorPID()[0],
                    channel_uuid: this._livechat.getUUID(),
                    page_history: history,
                });
                return;
            }
            case 'mail.channel.partner/typing_status': {
                if (payload.channel_id !== this._livechat._id) {
                    return;
                }
                const partnerID = payload.partner_id;
                if (partnerID === this.options.current_partner_id) {
                    // ignore typing display of current partner.
                    return;
                }
                if (payload.is_typing) {
                    this._livechat.registerTyping({ partnerID });
                } else {
                    this._livechat.unregisterTyping({ partnerID });
                }
                return;
            }
            case 'mail.channel/new_message': {
                if (payload.id !== this._livechat._id) {
                    return;
                }
                const notificationData = payload.message;
                // If message from notif is already in chatter messages, stop handling
                if (this._messages.some(message => message.getID() === notificationData.id)) {
                    return;
                }
                notificationData.body = utils.Markup(notificationData.body);
                this._addMessage(notificationData);
                if (this._chatWindow.isFolded() || !this._chatWindow.isAtBottom()) {
                    this._livechat.incrementUnreadCounter();
                }
                this._renderMessages();
                return;
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
                } catch (_err) {
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

                    utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(self._livechat.toData()), true), 60 * 60);
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
                    } catch (_err) {
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
                date: time.datetime_to_str(new Date()),
                model: "mail.channel",
                res_id: this._livechat.getID(),
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
        this._visitorLeaveSession();
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
        utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(this._livechat.toData()), true), 60 * 60);
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
    /**
     * @private
     * Called when the visitor leaves the livechat chatter the first time (first click on X button)
     * this will deactivate the mail_channel, notify operator that visitor has left the channel.
     */
    _visitorLeaveSession: function () {
        var cookie = utils.get_cookie('im_livechat_session');
        if (cookie) {
            var channel = JSON.parse(cookie);
            session.rpc('/im_livechat/visitor_leave_session', {uuid: channel.uuid});
            utils.set_cookie('im_livechat_session', "", -1); // remove cookie
        }
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
        this.dp.add(session.rpc('/im_livechat/feedback', args)).then(function (response) {
            var emoji = RATING_TO_EMOJI[self.rating] || "??";
            if (!reason) {
                var content = _.str.sprintf(_t("Rating: %s"), emoji);
            }
            else {
                var content = "Rating reason: \n" + reason;
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
            this._sendFeedback();
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
var mailUtils = require('@mail/js/utils');

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

