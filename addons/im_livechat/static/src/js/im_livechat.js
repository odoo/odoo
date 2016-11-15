odoo.define('im_livechat.im_livechat', function (require) {
"use strict";

var bus = require('bus.bus').bus;
var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var Widget = require('web.Widget');

var ChatWindow = require('mail.ChatWindow');

var _t = core._t;
var QWeb = core.qweb;

var LivechatButton = Widget.extend({
    className:"openerp o_livechat_button hidden-print",

    events: {
        "click": "open_chat"
    },

    init: function (parent, server_url, options) {
        this._super(parent);
        this.options = _.defaults(options || {}, {
            input_placeholder: _t('Ask something ...'),
            default_username: _t("Visitor"),
            button_text: _t("Chat with one of our collaborators"),
            default_message: _t("How may I help you?"),
        });
        this.channel = null;
        this.chat_window = null;
        this.messages = [];
    },

    willStart: function () {
        var self = this;
        var cookie = utils.get_cookie('im_livechat_session');
        var ready;
        if (!cookie) {
            ready = session.rpc("/im_livechat/init", {channel_id: this.options.channel_id}).then(function (result) {
                if (!result.available_for_me) {
                    return $.Deferred().reject();
                }
                self.rule = result.rule;
            });
        } else {
            var channel = JSON.parse(cookie);
            ready = session.rpc("/mail/chat_history", {uuid: channel.uuid, limit: 100}).then(function (history) {
                self.history = history;
            });
        }
        return ready.then(this.load_qweb_template.bind(this));
    },

    start: function () {
        this.$el.text(this.options.button_text);
        var small_screen = config.device.size_class === config.device.SIZES.XS;
        if (this.history) {
            _.each(this.history.reverse(), this.add_message.bind(this));
            this.open_chat();
        } else if (!small_screen && this.rule.action === 'auto_popup') {
            var auto_popup_cookie = utils.get_cookie('im_livechat_auto_popup');
            if (!auto_popup_cookie || JSON.parse(auto_popup_cookie)) {
                this.auto_popup_timeout = setTimeout(this.open_chat.bind(this), this.rule.auto_popup_timer*1000);
            }
        }
        bus.on('notification', this, function (notifications) {
            var self = this;
            _.each(notifications, function (notification) {
                if (self.channel && (notification[0] === self.channel.uuid)) {
                    self.add_message(notification[1]);
                    self.render_messages();
                    if (self.chat_window.folded || !self.chat_window.thread.is_at_bottom()) {
                        self.chat_window.update_unread(self.chat_window.unread_msgs+1);
                    }
                }
            });
        });
        return this._super();
    },

    load_qweb_template: function(){
        return $.when(
            $.get('/mail/static/src/xml/chat_window.xml'),
            $.get('/mail/static/src/xml/thread.xml'),
            $.get('/im_livechat/static/src/xml/im_livechat.xml')
        ).then(function (chat_window, mail_thread, livechat) {
            // results are triplets of [dom: XMLDocument, status: String, xhr: jqXHR]
            QWeb.add_template(chat_window[0]);
            QWeb.add_template(mail_thread[0]);
            QWeb.add_template(livechat[0]);
        });
    },

    open_chat: _.debounce(function () {
        if (this.opening_chat) {
            return;
        }
        var self = this;
        var cookie = utils.get_cookie('im_livechat_session');
        var def;
        this.opening_chat = true;
        clearTimeout(this.auto_popup_timeout);
        if (cookie) {
            def = $.when(JSON.parse(cookie));
        } else {
            this.messages = []; // re-initialize messages cache
            def = session.rpc('/im_livechat/get_session', {
                channel_id : this.options.channel_id,
                anonymous_name : this.options.default_username,
            }, {shadow: true});
        }
        def.then(function (channel) {
            if (!channel || !channel.operator_pid) {
                alert(_t("None of our collaborators seems to be available, please try again later."));
            } else {
                self.channel = channel;
                self.open_chat_window(channel);
                self.send_welcome_message();
                self.render_messages();

                bus.add_channel(channel.uuid);
                bus.start_polling();

                utils.set_cookie('im_livechat_session', JSON.stringify(channel), 60*60);
                utils.set_cookie('im_livechat_auto_popup', JSON.stringify(false), 60*60);
            }
        }).always(function () {
            self.opening_chat = false;
        });
    }, 200, true),

    open_chat_window: function (channel) {
        var self = this;
        var options = {
            display_stars: false,
            placeholder: this.options.input_placeholder || "",
        };
        var is_folded = (channel.state === 'folded');
        this.chat_window = new ChatWindow(this, channel.id, channel.name, is_folded, channel.message_unread_counter, options);
        this.chat_window.appendTo($('body')).then(function () {
            self.chat_window.$el.css({right: 0, bottom: 0});
            self.$el.hide();
        });
        this.chat_window.on("close_chat_session", this, function () {
            var input_disabled = this.chat_window.$(".o_chat_composer input").prop('disabled');
            var ask_fb = !input_disabled && _.find(this.messages, function (msg) {
                return msg.id !== '_welcome';
            });
            if (ask_fb) {
                this.chat_window.toggle_fold(false);
                this.ask_feedback();
            } else {
                this.close_chat();
            }
        });
        this.chat_window.on("post_message", this, function (message) {
            self.send_message(message).fail(function (error, e) {
                e.preventDefault();
                return self.send_message(message); // try again just in case
            });
        });
        this.chat_window.on("fold_channel", this, function () {
            this.channel.state = (this.channel.state === 'open') ? 'folded' : 'open';
            utils.set_cookie('im_livechat_session', JSON.stringify(this.channel), 60*60);
        });
        this.chat_window.thread.$el.on("scroll", null, _.debounce(function () {
            if (self.chat_window.thread.is_at_bottom()) {
                self.chat_window.update_unread(0);
            }
        }, 100));
    },

    close_chat: function () {
        this.chat_window.destroy();
        utils.set_cookie('im_livechat_session', "", -1); // remove cookie
    },

    send_message: function (message) {
        var self = this;
        return session
            .rpc("/mail/chat_post", {uuid: this.channel.uuid, message_content: message.content})
            .then(function () {
                self.chat_window.thread.scroll_to();
            });
    },

    add_message: function (data, options) {
        var msg = {
            id: data.id,
            attachment_ids: data.attachment_ids,
            author_id: data.author_id,
            body: data.body,
            date: moment(time.str_to_datetime(data.date)),
            is_needaction: false,
            is_note: data.is_note,
            customer_email_data: []
        };

        // Compute displayed author name or email
        msg.displayed_author = msg.author_id && msg.author_id[1] ||
                               this.options.default_username;

        // Compute the avatar_url
        if (msg.author_id && msg.author_id[0]) {
            msg.avatar_src = "/web/image/res.partner/" + msg.author_id[0] + "/image_small";
        } else {
            msg.avatar_src = "/mail/static/src/img/smiley/avatar.jpg";
        }

        if (options && options.prepend) {
            this.messages.unshift(msg);
        } else {
            this.messages.push(msg);
        }
    },

    render_messages: function () {
        var should_scroll = !this.chat_window.folded && this.chat_window.thread.is_at_bottom();
        this.chat_window.render(this.messages);
        if (should_scroll) {
            this.chat_window.thread.scroll_to();
        }
    },

    send_welcome_message: function () {
        if (this.options.default_message) {
            this.add_message({
                id: '_welcome',
                attachment_ids: [],
                author_id: this.channel.operator_pid,
                body: this.options.default_message,
                channel_ids: [this.channel.id],
                date: time.datetime_to_str(new Date()),
                tracking_value_ids: [],
            }, {prepend: true});
        }
    },

    ask_feedback: function () {
        this.chat_window.$(".o_chat_composer input").prop('disabled', true);

        var feedback = new Feedback(this, this.channel.uuid);
        feedback.replace(this.chat_window.thread.$el);

        feedback.on("send_message", this, this.send_message);
        feedback.on("feedback_sent", this, this.close_chat);
    }
});

/*
 * Rating for Livechat
 *
 * This widget displays the 3 rating smileys, and a textarea to add a reason
 * (only for red smiley), and sends the user feedback to the server.
 */
var Feedback = Widget.extend({
    template: "im_livechat.FeedBack",

    events: {
        'click .o_livechat_rating_choices img': 'on_click_smiley',
        'click .o_livechat_no_feedback em': 'on_click_no_feedback',
        'click .o_rating_submit_button': 'on_click_send',
    },

    init: function (parent, channel_uuid) {
        this._super(parent);
        this.channel_uuid = channel_uuid;
        this.server_origin = session.origin;
        this.rating = undefined;
    },

    on_click_smiley: function (ev) {
        this.rating = parseInt($(ev.currentTarget).data('value'));
        this.$('.o_livechat_rating_choices img').removeClass('selected');
        this.$('.o_livechat_rating_choices img[data-value="'+this.rating+'"]').addClass('selected');

        // only display textearea if bad smiley selected
        var close_chat = false;
        if (this.rating === 0) {
            this.$('.o_livechat_rating_reason').show();
        } else {
            this.$('.o_livechat_rating_reason').hide();
            close_chat = true;
        }
        this._send_feedback({close: close_chat});
    },

    on_click_no_feedback: function () {
        this.trigger("feedback_sent"); // will close the chat
    },

    on_click_send: function () {
        if (_.isNumber(this.rating)) {
            this._send_feedback({ reason: this.$('textarea').val(), close: true });
        }
    },

    _send_feedback: function (options) {
        var self = this;
        var args = {
            uuid: this.channel_uuid,
            rate: this.rating,
            reason : options.reason
        };
        return session.rpc('/im_livechat/feedback', args).then(function () {
            if (options.close) {
                var content = _.str.sprintf(_t("Rating: :rating_%d"), self.rating);
                if (options.reason) {
                    content += " \n" + options.reason;
                }
                self.trigger("send_message", {content: content});
                self.trigger("feedback_sent"); // will close the chat
            }
        });
    }
});

return {
    LivechatButton: LivechatButton,
    Feedback: Feedback,
};

});
