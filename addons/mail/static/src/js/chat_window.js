odoo.define('mail.ChatWindow', function (require) {
"use strict";

var ChatThread = require('mail.ChatThread');

var config = require('web.config');
var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var HEIGHT_OPEN = '400px';
var HEIGHT_FOLDED = '28px';

return Widget.extend({
    template: "mail.ChatWindow",
    events: {
        "click .o_chat_input": "focus_input", // focus even if jquery's blockUI is enabled
        "keydown .o_chat_input": "on_keydown",
        "keypress .o_chat_input": "on_keypress",
        "click .o_chat_window_close": "on_click_close",
        "click .o_chat_title": "on_click_fold",
    },

    init: function (parent, channel_id, title, is_folded, unread_msgs, options) {
        this._super(parent);
        this.title = title;
        this.channel_id = channel_id;
        this.folded = is_folded;
        this.options = _.defaults(options || {}, {
            autofocus: true,
            display_stars: true,
            display_reply_icon: false,
            placeholder: _t("Say something"),
            input_less: false,
        });
        this.status = this.options.status;
        this.unread_msgs = unread_msgs || 0;
        this.is_hidden = false;
    },
    start: function () {
        this.$input = this.$('.o_chat_input input');
        this.$header = this.$('.o_chat_header');

        this.thread = new ChatThread(this, {
            channel_id: this.channel_id,
            display_needactions: false,
            display_stars: this.options.display_stars,
        });
        this.thread.on('toggle_star_status', null, this.trigger.bind(this, 'toggle_star_status'));
        this.thread.on('redirect_to_channel', null, this.trigger.bind(this, 'redirect_to_channel'));
        this.thread.on('redirect', null, this.trigger.bind(this, 'redirect'));

        if (this.folded) {
            this.$el.css('height', HEIGHT_FOLDED);
        } else if (this.options.autofocus) {
            this.focus_input();
        }
        var def = this.thread.replace(this.$('.o_chat_content'));
        return $.when(this._super(), def);
    },
    render: function (messages) {
        this.update_unread(this.unread_msgs);
        this.thread.render(messages, {display_load_more: false});
    },
    update_unread: function (counter) {
        this.unread_msgs = counter;
        this.render_header();
    },
    update_status: function (status) {
        this.status = status;
        this.render_header();
    },
    render_header: function () {
        this.$header.html(QWeb.render('mail.ChatWindowHeaderContent', {
            status: this.status,
            title: this.title,
            unread_counter: this.unread_msgs,
        }));
    },
    fold: function () {
        this.$el.animate({
            height: this.folded ? HEIGHT_FOLDED : HEIGHT_OPEN
        });
    },
    toggle_fold: function (fold) {
        this.folded = _.isBoolean(fold) ? fold : !this.folded;
        if (!this.folded) {
            this.thread.scroll_to();
            this.focus_input();
        }
        this.fold();
    },
    focus_input: function () {
        if (!config.device.touch) {
            this.$input.focus();
        }
    },
    do_show: function () {
        this.is_hidden = false;
        this._super.apply(this, arguments);
    },
    do_hide: function () {
        this.is_hidden = true;
        this._super.apply(this, arguments);
    },
    do_toggle: function (display) {
        this.is_hidden = _.isBoolean(display) ? !display : !this.is_hidden;
        this._super.apply(this, arguments);
    },
    on_keypress: function (event) {
        event.stopPropagation(); // to prevent jquery's blockUI to cancel event
    },
    on_keydown: function (event) {
        event.stopPropagation(); // to prevent jquery's blockUI to cancel event
        // ENTER key (avoid requiring jquery ui for external livechat)
        if (event.which === 13) {
            var content = _.str.trim(this.$input.val());
            var message = {
                content: content,
                attachment_ids: [],
                partner_ids: [],
            };
            this.$input.val('');
            if (content) {
                this.trigger('post_message', message, this.channel_id);
            }
        }
    },
    on_click_close: function (event) {
        event.stopPropagation();
        event.preventDefault();
        this.trigger("close_chat_session");
    },
    on_click_fold: function () {
        if (config.device.size_class !== config.device.SIZES.XS) {
            this.toggle_fold();
            this.trigger("fold_channel", this.channel_id, this.folded);
        }
    },
});

});
