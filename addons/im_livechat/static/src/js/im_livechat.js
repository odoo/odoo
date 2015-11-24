odoo.define('im_livechat.im_livechat', function (require) {
"use strict";

var bus = require('bus.bus').bus;
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
            placeholder: _t('Ask something ...'),
            default_username: _t("Visitor"),
            button_text: _t("Chat with one of our collaborators"),
            default_message: _t("How may I help you?"),
        });
        this.channel = null;
        this.chat_window = null;
        this.messages = [];
    },

    willStart: function () {
        return this.load_qweb_template();
    },

    start: function () {
        this.$el.text(this.options.button_text);
        bus.on('notification', this, function (notification) {
            this.add_message(notification[1]);
            this.render_messages();
            if (this.chat_window.folded) {
                this.chat_window.update_unread(this.chat_window.unread_msgs+1);
            }
        });
        return this._super();
    },

    load_qweb_template: function () {
        var xml_files = ['/mail/static/src/xml/chat_window.xml',
                         '/mail/static/src/xml/thread.xml',
                         '/im_livechat/static/src/xml/im_livechat.xml'];
        var defs = _.map(xml_files, function (tmpl) {
            return session.rpc('/web/proxy/load', {path: tmpl}).then(function (xml) {
                QWeb.add_template(xml);
            });
        });
        return $.when.apply($, defs);
    },

    open_chat: function () {
        var self = this;
        var cookie = utils.get_cookie('im_livechat_session');
        var def;
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
                bus.poll();

                utils.set_cookie('im_livechat_session', JSON.stringify(channel), 60*60);
            }
        });
    },

    open_chat_window: function (channel) {
        var self = this;
        var options = {
            display_stars: false,
        };
        this.chat_window = new ChatWindow(this, channel.id, channel.name, false, channel.message_unread_counter, options);
        this.chat_window.appendTo($('body')).then(function () {
            self.chat_window.$el.css({right: 0, bottom: 0});
            self.$el.hide();
        });
        this.chat_window.on("close_chat_session", this, function () {
            if (this.messages.length > 1) {
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
    },

    close_chat: function () {
        this.chat_window.destroy();
        this.$el.show();
        utils.set_cookie('im_livechat_session', "", -1); // remove cookie
    },

    send_message: function (message) {
        return session.rpc("/mail/chat_post", {uuid: this.channel.uuid, message_content: message.content});
    },

    add_message: function (data) {
        this.messages.push({
            id: data.id,
            attachment_ids: data.attachment_ids,
            author_id: data.author_id,
            body: data.body,
            date: data.date,
            is_needaction: false,
            is_note: data.is_note,
        });
    },

    render_messages: function () {
        this.chat_window.render(this.messages);
        this.chat_window.scrollBottom();
    },

    send_welcome_message: function () {
        this.add_message({
            id: 1,
            attachment_ids: [],
            author_id: this.channel.operator_pid,
            body: this.options.default_message,
            channel_ids: [this.channel.id],
            date: time.datetime_to_str(new Date()),
            tracking_value_ids: [],
        });
    },

    ask_feedback: function () {
        this.chat_window.$(".o_chat_content").empty();
        this.chat_window.$(".o_chat_input input").prop('disabled', true);

        var feedback = new Feedback(this, this.channel.uuid);
        feedback.appendTo(this.chat_window.$(".o_chat_content"));

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
                var content = _.str.sprintf(_t("I rated you with :rating_%d"), self.rating);
                if (options.reason) {
                    content += _.str.sprintf(_t(" for the following reason: %s"), options.reason);
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
