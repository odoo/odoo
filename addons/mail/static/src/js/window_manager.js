odoo.define('mail.window_manager', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var ExtendedChatWindow = require('mail.ExtendedChatWindow');

var config = require('web.config');
var core = require('web.core');
var utils = require('web.utils');
var web_client = require('web.web_client');

var _t = core._t;
var QWeb = core.qweb;

// chat window management
//----------------------------------------------------------------
var CHAT_WINDOW_WIDTH = 300 + 5;  // 5 pixels between windows
var chat_sessions = [];
var new_chat_session;
var display_state = {
    chat_windows_hidden: false,  // chat windows aren't displayed when the client action is open
    hidden_sessions: [],
    hidden_unread_counter: 0,  // total number of unread msgs in hidden chat windows
    nb_slots: 0,
    space_left: 0,
    windows_dropdown_is_open: false,  // used to keep dropdown open when closing chat windows
};

function add_chat_session (chat_session) {
    // adds chat_session such that it will be the left-most visible window
    compute_available_slots(chat_sessions.length+1);
    chat_sessions.splice(display_state.nb_slots-1, 0, chat_session);
}

// options.passively: if set to true, open the chat window without focusing the
// input and marking messages as read if it is not open yet, and do nothing
// otherwise
function open_chat (session, options) {
    if (!session) {
        open_chat_without_session();
        return;
    }
    options = options || {};
    var chat_session = _.findWhere(chat_sessions, {id: session.id});
    if (!chat_session) {
        var prefix = !session.is_chat ? "#" : "";
        var window_options = {
            autofocus: !options.passively,
            input_less: session.mass_mailing,
            status: session.status,
        };
        chat_session = {
            id: session.id,
            uuid: session.uuid,
            name: session.name,
            keep_unread: options.passively, // don't automatically mark unread messages as seen
            window: new ExtendedChatWindow(web_client, session.id, prefix + session.name, session.is_folded, session.unread_counter, window_options),
        };
        chat_session.window.on("close_chat_session", null, function () {
            close_chat(chat_session);
            chat_manager.close_chat_session(chat_session.id);
        });
        chat_session.window.on("toggle_star_status", null, function (message_id) {
            chat_manager.toggle_star_status(message_id);
        });

        chat_session.window.on("fold_channel", null, function (channel_id, folded) {
            chat_manager.fold_channel(channel_id, folded);
        });

        chat_session.window.on("post_message", null, function (message, channel_id) {
            message.content = _.escape(message.content);
            chat_manager
                .post_message(message, {channel_id: channel_id})
                .then(function () {
                    chat_session.window.thread.scroll_to();
                });
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

        var remove_new_chat = false;
        if (options.passively) {
            chat_sessions.push(chat_session); // simply insert the window to the left
        } else if (new_chat_session && new_chat_session.partner_id && new_chat_session.partner_id === session.direct_partner_id) {
            // the window takes the place of the 'new_chat_session' window
            chat_sessions[_.indexOf(chat_sessions, new_chat_session)] = chat_session;
            remove_new_chat = true;
        } else {
            add_chat_session(chat_session); // add session such that window is visible
        }

        chat_session.window.appendTo($('body'))
            .then(function () {
                reposition_windows({remove_new_chat: remove_new_chat});
                return chat_manager.get_messages({channel_id: chat_session.id});
            }).then(function (messages) {
                chat_session.window.render(messages);
                chat_session.window.thread.scroll_to();
                setTimeout(function () {
                    chat_session.window.thread.$el.on("scroll", null, _.debounce(function () {
                        if (!chat_session.keep_unread && chat_session.window.thread.is_at_bottom()) {
                            chat_manager.mark_channel_as_seen(session);
                        }
                    }, 100));
                }, 0); // setTimeout to prevent to execute handler on first scroll_to, which is asynchronous
                if (options.passively) {
                    // mark first unread messages as seen when focusing the window, then on scroll to bottom as usual
                    chat_session.window.$('.o_mail_thread, .o_chat_input').one('click', function () {
                        chat_manager.mark_channel_as_seen(session);
                    });
                } else if (!display_state.chat_windows_hidden && !session.is_folded) {
                    chat_manager.mark_channel_as_seen(session);
                }
            });
    } else if (!options.passively) {
        if (chat_session.window.is_hidden) {
            make_session_visible(chat_session);
        } else if (session.is_folded !== chat_session.window.folded) {
            chat_session.window.toggle_fold(session.is_folded);
        }
    }
}

function open_chat_without_session () {
    if (!new_chat_session) {
        new_chat_session = {
            id: '_open',
            window: new ExtendedChatWindow(web_client, undefined, _t('New message'), false, 0, {thread_less: true}),
        };
        new_chat_session.window.on("close_chat_session", null, close_new_chat);
        new_chat_session.window.on('open_dm_session', null, function (partner_id) {
            new_chat_session.partner_id = partner_id;
            var dm = chat_manager.get_dm_from_partner_id(partner_id);
            if (!dm) {
                chat_manager.open_and_detach_dm(partner_id);
            } else {
                var dm_session = _.findWhere(chat_sessions, {id: dm.id});
                if (!dm_session) {
                    chat_manager.detach_channel(dm);
                } else {
                    close_chat(dm_session);
                    dm.is_folded = false;
                    open_chat(dm);
                }
            }
        });
        add_chat_session(new_chat_session);
        new_chat_session.window.appendTo($('body')).then(reposition_windows);
    } else {
        if (new_chat_session.window.is_hidden) {
            make_session_visible(new_chat_session);
        } else if (new_chat_session.window.folded) {
            new_chat_session.window.toggle_fold(false);
        }
    }
}

function close_chat (chat_session, options) {
    if (options && options.keep_open_if_unread && chat_session.keep_unread) {
        return;
    }
    chat_sessions = _.without(chat_sessions, chat_session);
    chat_session.window.destroy();
    reposition_windows();
}

function close_new_chat () {
    chat_sessions = _.without(chat_sessions, new_chat_session);
    reposition_windows({remove_new_chat: true});
}

function destroy_new_chat () {
    new_chat_session.window.destroy();
    new_chat_session = undefined;
}

function toggle_fold_chat (channel) {
    var session = _.find(chat_sessions, {id: channel.id});
    if (session) {
        session.window.toggle_fold(channel.is_folded);
    }
}

function compute_available_slots (nb_windows) {
    if (config.device.size_class === config.device.SIZES.XS) {
        display_state.nb_slots = 1; // one chat window full screen in mobile
        return;
    }
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

var reposition_windows = function (options) {
    if (options && options.remove_new_chat) {
        destroy_new_chat();
    }
    if (display_state.chat_windows_hidden) {
        return;
    }
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
};

function make_session_visible (session) {
    utils.swap(chat_sessions, session, chat_sessions[display_state.nb_slots-1]);
    reposition_windows();
    session.window.toggle_fold(false);
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
            var message_visible = !display_state.chat_windows_hidden && !session.window.folded &&
                                  !session.window.is_hidden && session.window.thread.is_at_bottom();
            if (message_visible && !session.keep_unread) {
                chat_manager.mark_channel_as_seen(chat_manager.get_channel(session.id));
            }
            chat_manager.get_messages({channel_id: session.id}).then(function (messages) {
                session.window.render(messages);
                if (scrollBottom && message_visible) {
                    session.window.thread.scroll_to();
                }
            });
        }
    });
}


core.bus.on('web_client_ready', null, function () {
    chat_manager.bus.on('open_chat', null, open_chat);
    chat_manager.bus.on('close_chat', null, function (channel, options) {
        var session = _.find(chat_sessions, {id: channel.id});
        if (session) {
            close_chat(session, options);
        }
    });
    chat_manager.bus.on('channel_toggle_fold', null, toggle_fold_chat);

    chat_manager.bus.on('new_message', null, function (message) {
        update_sessions(message, true);
    });

    chat_manager.bus.on('update_message', null, function (message) {
        update_sessions(message, false);
    });

    chat_manager.bus.on('anyone_listening', null, function (channel, query) {
        _.each(chat_sessions, function (session) {
            if (channel.id === session.id && session.window.thread.is_at_bottom() && !session.window.is_hidden) {
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
                if (channel.unread_counter === 0) {
                    session.keep_unread = false;
                }
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

    chat_manager.bus.on('update_dm_presence', null, function (channel) {
        _.each(chat_sessions, function (session) {
            if (channel.id === session.id) {
                session.window.update_status(channel.status);
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

    chat_manager.bus.on('detach_channel', null, function (channel) {
        var chat_session = _.findWhere(chat_sessions, {id: channel.id});
        if (!chat_session || chat_session.window.folded) {
            chat_manager.detach_channel(channel);
        } else if (chat_session.window.is_hidden) {
            make_session_visible(chat_session);
        } else {
            chat_session.window.focus_input();
        }
    });

    chat_manager.bus.on('client_action_open', null, function (open) {
        display_state.chat_windows_hidden = open;
        if (open) {
            $('body').addClass('o_no_chat_window');
        } else {
            $('body').removeClass('o_no_chat_window');
            reposition_windows();
        }
    });

    core.bus.on('resize', null, _.debounce(reposition_windows, 100));
});

});

// FIXME: move this to its own file in master
odoo.define('mail.ExtendedChatWindow', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var ChatWindow = require('mail.ChatWindow');

return ChatWindow.extend({
    template: "mail.ExtendedChatWindow",
    start: function () {
        var self = this;
        return this._super().then(function () {
            if (self.options.thread_less) {
                self.$el.addClass('o_thread_less');
                self.$('.o_chat_search_input input')
                    .autocomplete({
                        source: function(request, response) {
                            chat_manager.search_partner(request.term, 10).done(response);
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
