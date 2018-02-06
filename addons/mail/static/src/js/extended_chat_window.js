odoo.define('mail.ExtendedChatWindow', function (require) {
"use strict";

var ChatWindow = require('mail.ChatWindow');
var composer = require('mail.composer');

return ChatWindow.extend({
    template: "mail.ExtendedChatWindow",
    events: _.extend({}, ChatWindow.prototype.events, {
        "click .o_chat_window_expand": "on_click_expand",
    }),
    start: function () {
        var self = this;
        var def;
        if (self.options.thread_less) {
            this.$el.addClass('o_thread_less');
            this.$('.o_chat_search_input input')
                .autocomplete({
                    source: function (request, response) {
                        self.call('chat_manager', 'searchPartner', request.term, 10).done(response);
                    },
                    select: function (event, ui) {
                        self.trigger('open_dm_session', ui.item.id);
                    },
                })
                .focus();
        } else if (!self.options.input_less) {
            var basicComposer = new composer.BasicComposer(self, {mention_partners_restricted: true, isMini: true});
            basicComposer.on('post_message', self, function (message) {
                self.call('chat_manager', 'postMessage', message, {
                    channelID: self.channel_id,
                });
            });
            basicComposer.once('input_focused', self, function () {
                var channel = self.call('chat_manager', 'getChannel', self.channel_id);
                var commands = self.call('chat_manager', 'getCommands', channel);
                var partners = self.call('chat_manager', 'getMentionPartnerSuggestions', channel);
                basicComposer.mention_set_enabled_commands(commands);
                basicComposer.mention_set_prefetched_partners(partners);
            });
            def = basicComposer.replace(self.$('.o_chat_composer'));
        }
        return $.when(this._super(), def);
    },
    // Override on_keydown to only prevent jquery's blockUI to cancel event, but without sending
    // the message on ENTER keydown as this is handled by the BasicComposer
    on_keydown: function (event) {
        event.stopPropagation();
    },
    on_reverse_breadcrumb: function () {
        var chatBus = this.call('chat_manager', 'getChatBus');
        chatBus.trigger('discuss_open', false);
     },
    on_click_expand: _.debounce(function (event) {
        event.preventDefault();
        this.do_action('mail.mail_channel_action_client_chat', {
            clear_breadcrumbs: false,
            active_id: this.channel_id,
            on_reverse_breadcrumb: this.on_reverse_breadcrumb
        });
    }, 1000, true),
});

});
