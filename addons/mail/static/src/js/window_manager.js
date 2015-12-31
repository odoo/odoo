odoo.define('mail.window_manager', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var ChatWindow = require('mail.ChatWindow');

var core = require('web.core');
var utils = require('web.utils');
var web_client = require('web.web_client');

var QWeb = core.qweb;

// chat window management
//----------------------------------------------------------------
var CHAT_WINDOW_WIDTH = 300 + 5;  // 5 pixels between windows
var chat_sessions = [];
var display_state = {
    hidden_sessions: [],
    hidden_unread_counter: 0,  // total number of unread msgs in hidden chat windows
    nb_slots: 0,
    space_left: 0,
    windows_dropdown_is_open: false,  // used to keep dropdown open when closing chat windows
};

function open_chat (session) {
    var chat_session = _.findWhere(chat_sessions, {id: session.id});
    if (!chat_session) {
        chat_session = {
            id: session.id,
            uuid: session.uuid,
            name: session.name,
            window: new ChatWindow(web_client, session.id, session.name, session.is_folded, session.unread_counter),
        };
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
            chat_manager.mark_channel_as_seen(session);
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

        // insert chat_session such that it will be the right-most visible window
        compute_available_slots(chat_sessions.length+1);
        chat_sessions.splice(display_state.nb_slots-1, 0, chat_session);

        chat_session.window.appendTo($('body'))
            .then(reposition_windows)
            .then(function () {
                return chat_manager.get_messages({channel_id: chat_session.id});
            }).then(function (messages) {
                chat_session.window.render(messages);
                chat_session.window.scrollBottom();
                if (!session.is_folded) {
                    chat_manager.mark_channel_as_seen(session);
                }
            });
    } else {
        if (chat_session.window.is_hidden) {
            make_session_visible(chat_session);
        } else if (session.is_folded !== chat_session.window.folded) {
            chat_session.window.toggle_fold(session.is_folded);
        }
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

function compute_available_slots (nb_windows) {
    var width = window.innerWidth;
    var nb_slots = Math.floor(width/CHAT_WINDOW_WIDTH);
    var space_left = width - (Math.min(nb_slots, nb_windows)*CHAT_WINDOW_WIDTH);
    if (nb_slots < nb_windows && space_left < 50) {
        nb_slots--;  // leave at least 50px for the hidden windows dropdown button
        space_left += CHAT_WINDOW_WIDTH;
    }
    display_state.nb_slots = nb_slots;
    display_state.space_left = space_left;
}

var reposition_windows = _.debounce(function () {
    compute_available_slots(chat_sessions.length);
    var hidden_sessions = [];
    var hidden_unread_counter = 0;
    var nb_slots = display_state.nb_slots;
    _.each(chat_sessions, function (session, index) {
        if (index < nb_slots) {
            session.window.$el.css({right: CHAT_WINDOW_WIDTH*index, bottom: 0});
            session.window.do_show();
        } else {
            hidden_sessions.push(session);
            hidden_unread_counter += session.window.unread_msgs;
            session.window.do_hide();
        }
    });
    display_state.hidden_sessions = hidden_sessions;
    display_state.hidden_unread_counter = hidden_unread_counter;

    if (display_state.$hidden_windows_dropdown) {
        display_state.$hidden_windows_dropdown.remove();
    }
    if (hidden_sessions.length) {
        display_state.$hidden_windows_dropdown = render_hidden_sessions_dropdown();
        var $hidden_windows_dropdown = display_state.$hidden_windows_dropdown;
        $hidden_windows_dropdown.css({right: CHAT_WINDOW_WIDTH * nb_slots, bottom: 0})
                                .appendTo($('body'));
        reposition_hidden_sessions_dropdown();
        display_state.windows_dropdown_is_open = false;

        $hidden_windows_dropdown.on('click', '.o_chat_header', function (event) {
            var session_id = $(event.currentTarget).data('session-id');
            var session = _.findWhere(hidden_sessions, {id: session_id});
            if (session) {
                make_session_visible(session);
            }
        });
        $hidden_windows_dropdown.on('click', '.o_chat_window_close', function (event) {
            var session_id = $(event.currentTarget).closest('.o_chat_header').data('session-id');
            var session = _.findWhere(hidden_sessions, {id: session_id});
            if (session) {
                session.window.on_click_close(event);
                display_state.windows_dropdown_is_open = true;  // keep the dropdown open
            }
        });
    }
}, 100);

function make_session_visible (session) {
    utils.swap(chat_sessions, session, chat_sessions[display_state.nb_slots-1]);
    session.window.toggle_fold(false);
    reposition_windows();
}

function render_hidden_sessions_dropdown () {
    var $dropdown = $(QWeb.render("mail.ChatWindowsDropdown", {
        sessions: display_state.hidden_sessions,
        open: display_state.windows_dropdown_is_open,
        unread_counter: display_state.hidden_unread_counter,
    }));
    return $dropdown;
}

function reposition_hidden_sessions_dropdown () {
    // Unfold dropdown to the left if there is enough place
    var $dropdown_ul = display_state.$hidden_windows_dropdown.children('ul');
    if (display_state.space_left > $dropdown_ul.width() + 10) {
        $dropdown_ul.addClass('dropdown-menu-right');
    }
}

function update_sessions (message, scrollBottom) {
    _.each(chat_sessions, function (session) {
        if (_.contains(message.channel_ids, session.id)) {
            if (!session.window.folded && !session.window.is_hidden) {
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
        display_state.hidden_unread_counter = 0;
        _.each(chat_sessions, function (session) {
            if (channel.id === session.id) {
                session.window.update_unread(channel.unread_counter);
            }
            if (session.window.is_hidden) {
                display_state.hidden_unread_counter += session.window.unread_msgs;
            }
        });
        if (display_state.$hidden_windows_dropdown) {
            display_state.$hidden_windows_dropdown.html(render_hidden_sessions_dropdown().html());
            reposition_hidden_sessions_dropdown();
        }
    });

    chat_manager.is_ready.then(function() {
        _.each(chat_manager.get_channels(), function (channel) {
            if (channel.is_detached) {
                open_chat(channel);
            }
        });
    });

    chat_manager.bus.on('detach_channel', null, function (channel) {
        var chat_session = _.findWhere(chat_sessions, {id: channel.id});
        if (!chat_session || chat_session.window.folded) {
            chat_manager.detach_channel(channel);
        } else if (chat_session && chat_session.window.is_hidden) {
            make_session_visible(chat_session);
        }
    });

    core.bus.on('resize', null, reposition_windows);
});

});
