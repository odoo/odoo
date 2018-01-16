odoo.define('mail.chat_mixin', function() {
"use strict";


var ChatMixin = {
    // return a deferred that resolves when chat manager is ready
    _chatReady: function() {
        var result;
        this.trigger_up('chat_manager_ready', {
            callback: function(def) { result = def;}
        });
        return $.when(result);
    },
    _getBus: function() {
        var result;
        this.trigger_up('get_bus', {
            callback: function(bus) { result = bus;}
        });
        return result;
    },
    _getCannedResponses: function() {
        var result;
        this.trigger_up('get_canned_responses', {
            callback: function(responses) { result = responses;}
        });
        return result;
    },
    _getEmojis: function() {
        var result;
        this.trigger_up('get_emojis', {
            callback: function(emojis) { result = emojis;}
        });
        return result;
    },
    _getMentionPartnerSuggestions: function(channel_id) {
        var result;
        this.trigger_up('get_mention_partner_suggestions', {
            channel_id: channel_id,
            callback: function(res) { result = res; },
        });
        return result;
    },
    _getMessages: function(options) {
        var result;
        this.trigger_up('get_messages', {
            options: options,
            callback: function(messages) { result = messages;}
        });
        return result ? result : $.when([]);
    },
    _joinChannel: function(channel_id) {
        var result;
        this.trigger_up('join_channel', {
            channel_id: channel_id,
            callback: function(def) { result = def; },
        });
        return $.when(result);
    },
    _postMessage: function(message, options) {
        var result;
        this.trigger_up('post_message', {
            message: message,
            options: options,
            callback: function(def) { result = def;}
        });
        return $.when(result);
    },
    _removeChatterMessages: function(model) {
        this.trigger_up('remove_chatter_messages', {
            model: model,
        });
    },
    _toggleStarStatus: function(message_id) {
        this.trigger_up('toggle_star_status', {
            message_id: message_id,
        });
    },
};

return ChatMixin;

});

odoo.define('mail.chat_service', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var web_client = require('web.web_client');

web_client.on('get_emojis', web_client, function(event) {
    event.data.callback(chat_manager.get_emojis());
});

web_client.on('get_canned_responses', web_client, function(event) {
    event.data.callback(chat_manager.get_canned_responses());
});

web_client.on('chat_manager_ready', web_client, function(event) {
    event.data.callback(chat_manager.is_ready);
});

web_client.on('get_messages', web_client, function(event) {
    event.data.callback(chat_manager.get_messages(event.data.options));
});

web_client.on('post_message', web_client, function(event) {
    event.data.callback(chat_manager.post_message(event.data.message, event.data.options));
});

web_client.on('get_bus', web_client, function(event) {
    event.data.callback(chat_manager.bus);
});

web_client.on('remove_chatter_messages', web_client, function(event) {
    chat_manager.remove_chatter_messages(event.data.model);
});

web_client.on('toggle_star_status', web_client, function(event) {
    chat_manager.toggle_star_status(event.data.message_id);
});

web_client.on('join_channel', web_client, function(event) {
    event.data.callback(chat_manager.join_channel(event.data.channel_id));
});

web_client.on('get_mention_partner_suggestions', web_client, function(event) {
    event.data.callback(chat_manager.get_mention_partner_suggestions(event.data.channel_id));
});

});