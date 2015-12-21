odoo.define('mail.ChatWindow', function (require) {
"use strict";

var ChatThread = require('mail.ChatThread');

var core = require('web.core');
var Widget = require('web.Widget');

var _t = core._t;

var HEIGHT_OPEN = '400px';
var HEIGHT_FOLDED = '28px';

return Widget.extend({
    template: "mail.ChatWindow",
    events: {
        "keydown .o_chat_input": "on_keydown",
        "click .o_chat_window_close": "on_click_close",
        "click .o_chat_title": "on_click_fold",
    },

    init: function (parent, channel_id, title, is_folded, unread_msgs, options) {
        this._super(parent);
        this.title = title;
        this.channel_id = channel_id;
        this.placeholder = _t("Say something");
        this.folded = is_folded;
        this.options = _.defaults(options || {}, {
            display_stars: true,
        });
        this.unread_msgs = unread_msgs || 0;
    },
    start: function () {
        this.$content = this.$('.o_chat_content');
        this.$input = this.$('.o_chat_input input');

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
        }
        var def = this.thread.appendTo(this.$content);
        return $.when(this._super(), def);
    },
    render: function (messages) {
        this.update_header();
        this.thread.render(messages, {display_load_more: false});
    },
    update_header: function () {
        var title = this.unread_msgs > 0 ?
            this.title + ' (' + this.unread_msgs + ')' : this.title;
        this.$('.o_chat_title').text(title);
    },
    update_unread: function (counter) {
        this.unread_msgs = counter;
        this.update_header();
    },
    scrollBottom: function () {
        this.$content.scrollTop(this.$content[0].scrollHeight);
    },
    fold: function () {
        this.update_header();
        this.$el.animate({
            height: this.folded ? HEIGHT_FOLDED : HEIGHT_OPEN
        });
    },
    toggle_fold: function (fold) {
        this.folded = _.isBoolean(fold) ? fold : !this.folded;
        if (!this.folded) {
            this.unread_msgs = 0;
            this.trigger('messages_read');
        }
        this.fold();
    },
    on_keydown: function (event) {
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
        this.trigger("fold_channel", this.channel_id);
        this.toggle_fold();
    },
});

});
