odoo.define('mail.ExtendedChatWindow', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var ChatWindow = require('mail.ChatWindow');

return ChatWindow.extend({
    template: "mail.ExtendedChatWindow",

    start: function () {
        var self = this;
        var direct_message_local_cache = {};
        return this._super().then(function () {
            if (self.options.thread_less) {
                self.$el.addClass('o_thread_less');
                self.$('.o_chat_search_input input')
                    .autocomplete({
                        source: function(request, response) {
                            var term = request.term;
                            if (term in direct_message_local_cache) {
                                response(direct_message_local_cache[term]);
                            } else {
                                chat_manager.search_partner(term, 10).done( function(result) {
                                    direct_message_local_cache[term] = result;
                                    response(result);
                                });
                            }
                        },
                        select: function(event, ui) {
                            self.trigger('open_dm_session', ui.item.id);
                        },
                    })
                    .focus();
            }
        });
    },
});

});
