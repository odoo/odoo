odoo.define('mail.ChatThread', function (require) {
"use strict";

var core = require('web.core');
var time = require('web.time');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var ORDER = {
    ASC: 1,
    DESC: -1,
};

var Thread = Widget.extend({
    className: 'o_mail_thread',

    events: {
        "click .o_mail_redirect": "on_click_redirect",
        "click .o_channel_redirect": "on_channel_redirect",
        "click .o_thread_show_more": "on_click_show_more",
        "click .o_thread_message_needaction": function (event) {
            event.stopPropagation();
            var message_id = $(event.currentTarget).data('message-id');
            this.trigger("mark_as_read", message_id);
        },
        "click .o_thread_message_star": function (event) {
            event.stopPropagation();
            var message_id = $(event.currentTarget).data('message-id');
            this.trigger("toggle_star_status", message_id);
        },
        "click .o_thread_message": function (event) {
            var selected = $(event.currentTarget).hasClass('o_thread_selected_message');
            this.$('.o_thread_message').removeClass('o_thread_selected_message');
            $(event.currentTarget).toggleClass('o_thread_selected_message', !selected);
        },
    },

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
            display_order: ORDER.ASC,
            display_needactions: true,
            display_stars: true,
            default_username: _t('Anonymous'),
            display_document_link: true,
            display_avatar: true,
        });
    },

    render: function (messages, options) {
        var msgs = _.map(messages, this._preprocess_message.bind(this));
        if (this.options.display_order === ORDER.DESC) {
            msgs.reverse();
        }

        // Hide avatar and info of a message if that message and the previous
        // one are both comments wrote by the same author at the same minute
        var prev_msg;
        _.each(msgs, function (msg) {
            if (!prev_msg || (Math.abs(moment(msg.date).diff(prev_msg.date)) > 60000) ||
                prev_msg.message_type !== 'comment' || msg.message_type !== 'comment' ||
                (prev_msg.author_id[0] !== msg.author_id[0])) {
                msg.display_author = true;
            }
            prev_msg = msg;
        });

        this.$el.html(QWeb.render('mail.ChatThread', {
            messages: msgs,
            options: _.extend({}, this.options, options),
            ORDER: ORDER,
        }));
    },

    on_click_redirect: function (event) {
        event.preventDefault();
        var res_id = $(event.target).data('oe-id');
        var res_model = $(event.target).data('oe-model');
        this.trigger('redirect', res_model, res_id);
    },

    on_channel_redirect: function (event) {
        event.preventDefault();
        var channel_id = $(event.target).data('channel-id');
        this.trigger('redirect_to_channel', channel_id);
    },

    on_click_show_more: function () {
        this.trigger('load_more_messages');
    },

    _preprocess_message: function (message) {
        var msg = _.extend({}, message);

        // Set the date in the browser timezone
        msg.date = moment(time.str_to_datetime(msg.date)).format('YYYY-MM-DD HH:mm:ss');

        // Compute displayed author name or email
        if ((!msg.author_id || !msg.author_id[0]) && msg.email_from) {
            msg.mailto = msg.email_from;
        } else {
            msg.displayed_author = msg.author_id && msg.author_id[1] ||
                                   msg.email_from ||
                                   this.options.default_username;
        }

        // Compute the avatar_url
        if (msg.author_id && msg.author_id[0]) {
            msg.avatar_src = "/web/image/res.partner/" + msg.author_id[0] + "/image_small";
        } else if (msg.message_type === 'email') {
            msg.avatar_src = "/mail/static/src/img/email_icon.png";
        } else {
            msg.avatar_src = "/mail/static/src/img/smiley/avatar.jpg";
        }

        // Compute url of attachments
        _.each(msg.attachment_ids, function(a) {
            a.url = '/web/content/' + a.id + '?download=true';
        });

        return msg;
    },

    /**
     * Removes a message and re-renders the thread
     * @param {int} [message_id] the id of the removed message
     * @param {array} [messages] the list of messages to display, without the removed one
     * @param {object} [options] options for the thread rendering
     */
    remove_message_and_render: function (message_id, messages, options) {
        var self = this;
        this.$('.o_thread_message[data-message-id=' + message_id + ']').fadeOut({
            done: function () { self.render(messages, options); }
        });
    },

    /**
     * Scrolls the thread to a given message or offset if any, to bottom otherwise
     * @param {int} [target.id] optional: the id of the message to scroll to
     * @param {int} [target.offset] optional: the number of pixels to scroll
     */
    scroll_to: function (target) {
        target = target || {};
        if (target.id !== undefined) {
            var $target = this.$('.o_thread_message[data-message-id=' + target.id + ']');
            if ($target.length) {
                this.$el.scrollTo($target);
            }
        } else if (target.offset !== undefined) {
            this.$el.scrollTop(target.offset);
        } else {
            this.$el.scrollTop(this.el.scrollHeight);
        }
    },
    get_scrolltop: function () {
        return this.$el.scrollTop();
    },
});

Thread.ORDER = ORDER;

return Thread;

});
