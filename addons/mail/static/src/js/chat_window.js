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

    init: function (parent, channel_id, title, is_folded) {
        this._super(parent);
        this.title = title;
        this.channel_id = channel_id;
        this.placeholder = _t("Say something");
        this.folded = is_folded;
    },
    start: function () {
        this.$content = this.$('.o_chat_content');
        this.$input = this.$('.o_chat_input input');

        this.thread = new ChatThread(this, {
            display_avatar: false,
            display_needactions: false,
        });
        this.thread.on('toggle_star_status', this, function (message_id) {
            this.trigger('toggle_star_status', message_id);
        });

        this.fold();
        var def = this.thread.appendTo(this.$content);
        return $.when(this._super(), def);
    },
    render: function (messages) {
        this.thread.render(messages, {display_load_more: false});
    },
    scrollBottom: function () {
        this.$content.scrollTo('max');
    },
    fold: function () {
        this.$el.animate({
            height: this.folded ? "28px" : "333px"
        });
    },
    toggle_fold: function () {
        this.folded = !this.folded;
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
