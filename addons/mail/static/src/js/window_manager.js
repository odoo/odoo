odoo.define('mail.window_manager', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var ChatWindow = require('mail.ChatWindow');

var core = require('web.core');
var web_client = require('web.web_client');


// chat window management
//----------------------------------------------------------------
var chat_sessions = [];
var CHAT_WINDOW_WIDTH = 300;

function open_chat (session) {
    if (!_.findWhere(chat_sessions, {id: session.id})) {
        var channel = chat_manager.get_channel(session.id);
        var chat_session = {
            id: session.id,
            uuid: session.uuid,
            name: session.name,
            window: new ChatWindow(web_client, session.id, session.name, session.is_folded, channel.unread_counter),
        };
        if (!session.is_folded) {
            chat_manager.mark_channel_as_seen(channel);
        }
        chat_session.window.on("close_chat_session", null, function () {
            close_chat(chat_session);
            chat_manager.close_chat_session(chat_session.id);
        });
        chat_session.window.on("toggle_star_status", null, function (message_id) {
            chat_manager.toggle_star_status(message_id);
        });

        chat_session.window.on("fold_channel", null, function (channel_id) {
            chat_manager.fold_channel(channel_id);
        });

        chat_session.window.on("post_message", null, function (message, channel_id) {
            message.content = _.escape(message.content);
            chat_manager.post_message(message, {channel_id: channel_id});
        });
        chat_session.window.on("messages_read", null, function () {
            chat_manager.mark_channel_as_seen(channel);
        });
        chat_session.window.on("redirect", null, function (res_model, res_id) {
            chat_manager.redirect(res_model, res_id, open_chat);
        });
        chat_session.window.on("redirect_to_channel", null, function (channel_id) {
            var session = _.findWhere(chat_sessions, {id: channel_id});
            if (!session) {
                chat_manager.join_channel(channel_id).then(function (channel) {
                    chat_manager.detach_channel(channel);
                });
            } else {
                session.window.toggle_fold(false);
            }
        });

        chat_sessions.push(chat_session);
        chat_session.window.appendTo($('body'))
            .then(reposition_windows)
            .then(function () {
                return chat_manager.get_messages({channel_id: chat_session.id});
            }).then(function (messages) {
                chat_session.window.render(messages);
                chat_session.window.scrollBottom();
            });
    }
}

function close_chat (chat_session) {
    var session = _.find(chat_sessions, {id: chat_session.id});
    if (session) {
        chat_sessions = _.without(chat_sessions, session);
        session.window.destroy();
        reposition_windows();
    }
}

function toggle_fold_chat (channel) {
    var session = _.find(chat_sessions, {id: channel.id});
    if (session) {
        session.window.toggle_fold();
    }
}

function reposition_windows () {
    _.each(chat_sessions, function (session, index) {
        session.window.$el.css({right: (CHAT_WINDOW_WIDTH + 5) * index, bottom: 0});
    });
}

function update_sessions (message, scrollBottom) {
    _.each(chat_sessions, function (session) {
        if (_.contains(message.channel_ids, session.id)) {
            if (!session.window.folded) {
                chat_manager.mark_channel_as_seen(chat_manager.get_channel(session.id));
            }
            chat_manager.get_messages({channel_id: session.id}).then(function (messages) {
                session.window.render(messages);
                if (scrollBottom) {
                    session.window.scrollBottom();
                }
            });
        }
    });
}


core.bus.on('web_client_ready', null, function () {
    chat_manager.bus.on('open_chat', null, open_chat);
    chat_manager.bus.on('close_chat', null, close_chat);
    chat_manager.bus.on('channel_toggle_fold', null, toggle_fold_chat);

    chat_manager.bus.on('new_message', null, function (message) {
        update_sessions(message, true);
    });

    chat_manager.bus.on('update_message', null, function (message) {
        update_sessions(message, false);
    });

    chat_manager.bus.on('anyone_listening', null, function (channel, query) {
        _.each(chat_sessions, function (session) {
            if (channel.id === session.id) {
                query.is_displayed = true;
            }
        });
    });

    chat_manager.bus.on('unsubscribe_from_channel', null, function (channel_id) {
        _.each(chat_sessions, function (session) {
            if (channel_id === session.id) {
                close_chat(session);
            }
        });
    });

    chat_manager.bus.on('update_channel_unread_counter', null, function (channel) {
        _.each(chat_sessions, function (session) {
            if (channel.id === session.id) {
                session.window.update_unread(channel.unread_counter);
            }
        });
    });

    chat_manager.is_ready.then(function() {
        _.each(chat_manager.get_channels(), function (channel) {
            if (channel.is_detached) {
                open_chat(channel);
            }
        });
    });
});

});
