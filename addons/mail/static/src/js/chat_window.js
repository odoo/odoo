odoo.define('mail.ChatWindow', function (require) {
"use strict";

var ChatThread = require('mail.ChatThread');

var core = require('web.core');
var Widget = require('web.Widget');

var _t = core._t;

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
            display_avatar: false,
            display_needactions: false,
            display_stars: this.options.display_stars,
        });
        this.thread.on('toggle_star_status', this, function (message_id) {
            this.trigger('toggle_star_status', message_id);
        });

        this.fold();
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
            height: this.folded ? "28px" : "333px"
        });
    },
    toggle_fold: function () {
        this.folded = !this.folded;
        if (!this.folded) {
            this.unread_msgs = 0;
            this.trigger('messages_read');
        }
        this.fold();
    },
    on_keydown: function (event) {
        if (event.which === $.ui.keyCode.ENTER) {
            var message = {
                content: this.$input.val(),
                attachment_ids: [],
                partner_ids: [],
                channel_id: this.channel_id,
            };
            this.$input.val('');
            this.trigger('post_message', message);
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
