odoo.define('mail.chat_manager', function (require) {
"use strict";

var bus = require('bus.bus').bus;
var core = require('web.core');
var data = require('web.data');
var Model = require('web.Model');
var session = require('web.session');
var time = require('web.time');
var web_client = require('web.web_client');

var _t = core._t;
var LIMIT = 100;
var preview_msg_max_size = 50;

var MessageModel = new Model('mail.message', session.context);
var ChannelModel = new Model('mail.channel', session.context);

// Private model
//----------------------------------------------------------------------------------
var messages = [];
var channels = [];
var channel_defs = {};
var emojis = [];
var emoji_substitutions = {};
var needaction_counter = 0;
var mention_partner_suggestions = [];
var discuss_ids = {};

// Message and channel manipulation helpers
//----------------------------------------------------------------------------------

// options: channel_id, silent
function add_message (data, options) {
    options = options || {};
    var msg = _.findWhere(messages, { id: data.id });

    if (!msg) {
        msg = make_message(data);
        // Keep the array ordered by date when inserting the new message
        messages.splice(_.sortedIndex(messages, msg, 'id'), 0, msg);
        _.each(msg.channel_ids, function (channel_id) {
            var channel = chat_manager.get_channel(channel_id);

            if (channel) {
                add_to_cache(msg, []);
                if (options.domain && options.domain !== []) {
                    add_to_cache(msg, options.domain);
                }
            }
            if (channel && channel.hidden) {
                channel.hidden = false;
                chat_manager.bus.trigger('new_channel', channel);
            }
            if (channel && !_.contains(["public", "private"], channel.type) && (options.show_notification)) {
                var query = { is_displayed: false };
                chat_manager.bus.trigger('anyone_listening', channel, query);
                if (!query.is_displayed) {
                    var title = _t('New message');
                    if (msg.author_id[1]) {
                        title += _t(' from ') + msg.author_id[1];
                    }
                    var trunc_text = function (t, limit) {
                        return (t.length > limit) ? t.substr(0, limit-1)+'&hellip;' : t;
                    };
                    web_client.do_notify(title, trunc_text(msg.body, preview_msg_max_size));
                }
            }
        });
        if (!options.silent) {
            chat_manager.bus.trigger('new_message', msg);
        }
    } else if (options.domain && options.domain !== []) {
        add_to_cache(msg, options.domain);
    }
    return msg;
}

function make_message (data) {
    var msg = {
        id: data.id,
        author_id: data.author_id,
        body_short: data.body_short || "",
        body: data.body || "",
        date: moment(time.str_to_datetime(data.date)),
        message_type: data.message_type,
        subtype_description: data.subtype_description,
        is_note: data.is_note,
        attachment_ids: data.attachment_ids,
        subject: data.subject,
        email_from: data.email_from,
        record_name: data.record_name,
        tracking_value_ids: data.tracking_value_ids,
        channel_ids: data.channel_ids,
        model: data.model,
        res_id: data.res_id,
    };

    _.each(_.keys(emoji_substitutions), function (key) {
        var escaped_key = String(key).replace(/([.*+?=^!:${}()|[\]\/\\])/g, '\\$1');
        var regexp = new RegExp("(?:^|\\s|<[a-z]*>)(" + escaped_key + ")(?=\\s|$|</[a-z]*>)", "g");
        msg.body = msg.body.replace(regexp, ' <span class="o_mail_emoji">'+emoji_substitutions[key]+'</span> ');
    });

    function property_descr(channel) {
        return {
            enumerable: true,
            get: function () {
                return _.contains(msg.channel_ids, channel);
            },
            set: function (bool) {
                if (bool) {
                    add_channel_to_message(msg, channel);
                } else {
                    msg.channel_ids = _.without(msg.channel_ids, channel);
                }
            }
        };
    }

    Object.defineProperties(msg, {
        is_starred: property_descr("channel_starred"),
        is_needaction: property_descr("channel_inbox"),
    });

    if (_.contains(data.needaction_partner_ids, session.partner_id)) {
        msg.is_needaction = true;
    }
    if (_.contains(data.starred_partner_ids, session.partner_id)) {
        msg.is_starred = true;
    }
    if (msg.model === 'mail.channel') {
        var real_channels = _.without(msg.channel_ids, 'channel_inbox', 'channel_starred');
        var origin = real_channels.length === 1 ? real_channels[0] : undefined;
        var channel = origin && chat_manager.get_channel(origin);
        if (channel) {
            msg.origin_id = origin;
            msg.origin_name = channel.name;
        }
    }

    // Compute displayed author name or email
    if ((!msg.author_id || !msg.author_id[0]) && msg.email_from) {
        msg.mailto = msg.email_from;
    } else {
        msg.displayed_author = msg.author_id && msg.author_id[1] ||
                               msg.email_from || _t('Anonymous');
    }

    // Compute the avatar_url
    if (msg.author_id && msg.author_id[0]) {
        msg.avatar_src = "/web/image/res.partner/" + msg.author_id[0] + "/image_small";
    } else if (msg.message_type === 'email') {
        msg.avatar_src = "/mail/static/src/img/email_icon.png";
    } else {
        msg.avatar_src = "/mail/static/src/img/smiley/avatar.jpg";
    }

    // Compute url of attachments
    _.each(msg.attachment_ids, function(a) {
        a.url = '/web/content/' + a.id + '?download=true';
    });

    return msg;
}

function add_channel_to_message (message, channel_id) {
    message.channel_ids.push(channel_id);
    message.channel_ids = _.uniq(message.channel_ids);
}

function post_channel_message (data) {
    return ChannelModel.call('message_post', [data.channel_id], {
        message_type: 'comment',
        content_subtype: 'html',
        partner_ids: data.partner_ids,
        body: _.str.trim(data.content),
        subtype: 'mail.mt_comment',
        attachment_ids: data.attachment_ids,
    });
}

function post_document_message (model_name, res_id, data) {
    var values = {
        attachment_ids: data.attachment_ids,
        body: _.str.trim(data.content),
        content_subtype: data.content_subtype,
        context: data.context,
        message_type: data.message_type,
        partner_ids: data.partner_ids,
        subtype: data.subtype,
        subtype_id: data.subtype_id,
    };

    var model = new Model(model_name);
    return model.call('message_post', [res_id], values).then(function (msg_id) {
        return MessageModel.call('message_format', [msg_id]).then(function (msgs) {
            msgs[0].model = model_name;
            msgs[0].res_id = res_id;
            add_message(msgs[0]);
        });
    });
}

function add_channel (data, options) {
    options = typeof options === "object" ? options : {};
    var channel = chat_manager.get_channel(data.id);
    if (channel) {
        if (channel.is_folded !== (data.state === "folded")) {
            channel.is_folded = (data.state === "folded");
            chat_manager.bus.trigger("channel_toggle_fold", channel);
        }
    } else {
        channel = make_channel(data, options);
        channels.push(channel);
        channels = _.sortBy(channels, function (channel) { return channel.name.toLowerCase(); });
        if (!options.silent) {
            chat_manager.bus.trigger("new_channel", channel);
        }
        if (channel.is_detached) {
            chat_manager.bus.trigger("open_chat", channel);
        }
    }
    return channel;
}

function make_channel (data, options) {
    var channel = {
        id: data.id,
        name: data.name,
        type: data.type || data.channel_type,
        all_history_loaded: false,
        uuid: data.uuid,
        is_detached: data.is_minimized,
        is_folded: data.state === "folded",
        autoswitch: 'autoswitch' in options ? options.autoswitch : true,
        hidden: options.hidden,
        display_needactions: options.display_needactions,
        mass_mailing: data.mass_mailing,
        needaction_counter: data.message_needaction_counter || 0,
        unread_counter: data.message_unread_counter || 0,
        last_seen_message_id: data.seen_message_id,
        cache: {'[]': {
            all_history_loaded: false,
            loaded: false,
            messages: [],
        }},
    };
    if (channel.type === "channel" && data.public !== "private") {
        channel.type = "public";
    } else if (data.public === "private") {
        channel.type = "private";
    }
    if ('direct_partner' in data) {
        channel.type = "dm";
        channel.name = data.direct_partner[0].name;
        channel.status = data.direct_partner[0].im_status;
    }
    return channel;
}

function get_channel_cache (channel, domain) {
    var stringified_domain = JSON.stringify(domain || []);
    if (!channel.cache[stringified_domain]) {
        channel.cache[stringified_domain] = {
            all_history_loaded: false,
            loaded: false,
            messages: [],
        };
    }
    return channel.cache[stringified_domain];
}

function invalidate_caches(channel_ids) {
    _.each(channel_ids, function (channel_id) {
        var channel = chat_manager.get_channel(channel_id);
        if (channel) {
            channel.cache = { '[]': channel.cache['[]']};
        }
    });
}

function add_to_cache(message, domain) {
    _.each(message.channel_ids, function (channel_id) {
        var channel = chat_manager.get_channel(channel_id);
        if (channel) {
            var channel_cache = get_channel_cache(channel, domain);
            var index = _.sortedIndex(channel_cache.messages, message, 'id');
            if (channel_cache.messages[index] !== message) {
                channel_cache.messages.splice(index, 0, message);
            }
        }
    });
}

function remove_message_from_channel (channel_id, message) {
    message.channel_ids = _.without(message.channel_ids, channel_id);
    var channel = _.findWhere(channels, { id: channel_id });
    _.each(channel.cache, function (cache) {
        cache.messages = _.without(cache.messages, message);
    });
}

// options: domain, load_more
function fetch_from_channel (channel, options) {
    options = options || {};
    var domain =
        (channel.id === "channel_inbox") ? [['needaction', '=', true]] :
        (channel.id === "channel_starred") ? [['starred', '=', true]] :
                                            [['channel_ids', 'in', channel.id]];
    var cache = get_channel_cache(channel, options.domain);

    if (options.domain) {
        domain = new data.CompoundDomain(domain, options.domain || []);
    }
    if (options.load_more) {
        var min_message_id = cache.messages[0].id;
        domain = new data.CompoundDomain([['id', '<', min_message_id]], domain);
    }

    return MessageModel.call('message_fetch', [domain], {limit: LIMIT}).then(function (msgs) {
        if (!cache.all_history_loaded) {
            cache.all_history_loaded =  msgs.length < LIMIT;
        }
        cache.loaded = true;

        _.each(msgs, function (msg) {
            add_message(msg, {channel_id: channel.id, silent: true, domain: options.domain});
        });
        var channel_cache = get_channel_cache(channel, options.domain || []);
        return channel_cache.messages;
    });
}

// options: force_fetch
function fetch_document_messages (ids, options) {
    var loaded_msgs = _.filter(messages, function (message) {
        return _.contains(ids, message.id);
    });
    var loaded_msg_ids = _.pluck(loaded_msgs, 'id');

    options = options || {};
    if (options.force_fetch || _.difference(ids.slice(0, LIMIT), loaded_msg_ids).length) {
        var ids_to_load = _.difference(ids, loaded_msg_ids).slice(0, LIMIT);

        return MessageModel.call('message_format', [ids_to_load]).then(function (msgs) {
            var processed_msgs = [];
            _.each(msgs, function (msg) {
                processed_msgs.push(add_message(msg, {silent: true}));
            });
            return _.sortBy(loaded_msgs.concat(processed_msgs), function (msg) {
                return msg.date;
            });
        });
    } else {
        return $.when(loaded_msgs);
    }
}

function update_channel_unread_counter (channel, counter) {
    channel.unread_counter = counter;
    chat_manager.bus.trigger("update_channel_unread_counter", channel);
}

var channel_seen = _.throttle(function (channel) {
    return ChannelModel.call('channel_seen', [[channel.id]]).then(function (last_seen_message_id) {
        channel.last_seen_message_id = last_seen_message_id;
    });
}, 3000);

// Notification handlers
// ---------------------------------------------------------------------------------
function on_notification (notification) {
    var model = notification[0][1];
    if (model === 'ir.needaction') {
        // new message in the inbox
        on_needaction_notification(notification[1]);
    } else if (model === 'mail.channel') {
        // new message in a channel
        on_channel_notification(notification[1]);
    } else if (model === 'res.partner') {
        // channel joined/left, message marked as read/(un)starred, chat open/closed
        on_partner_notification(notification[1]);
    }
}

function on_needaction_notification (message) {
    message = add_message(message, { channel_id: 'channel_inbox', show_notification: true} );
    invalidate_caches(message.channel_ids);
    needaction_counter++;
    _.each(message.channel_ids, function (channel_id) {
        var channel = chat_manager.get_channel(channel_id);
        if (channel) {
            channel.needaction_counter++;
        }
    });
    chat_manager.bus.trigger('update_needaction', needaction_counter);
}

function on_channel_notification (message) {
    var def;
    if ((message.channel_ids.length === 1) && !chat_manager.get_channel(message.channel_ids[0])) {
        def = chat_manager.join_channel(message.channel_ids[0], {autoswitch: false});
    } else {
        def = $.when();
    }
    def.then(function () {
        _.each(message.channel_ids, function (channel_id) {
            var channel = chat_manager.get_channel(channel_id);
            if (channel) {
                update_channel_unread_counter(channel, channel.unread_counter+1);
            }
        });
        add_message(message, { show_notification: true });
        invalidate_caches(message.channel_ids);
    });
}

function on_partner_notification (data) {
    if (data.info === "unsubscribe") {
        channels = _.without(channels, chat_manager.get_channel(data.id));
        chat_manager.bus.trigger("unsubscribe_from_channel", data.id);
    } else if (data.type === 'toggle_star') {
        on_toggle_star_notification(data);
    } else if (data.type === 'mark_as_read') {
        on_mark_as_read_notification(data);
    } else if (data.type === 'mark_as_unread') {
        on_mark_as_unread_notification(data);
    } else {
        on_chat_session_notification(data);
    }
}

function on_toggle_star_notification (data) {
    _.each(data.message_ids, function (msg_id) {
        var message = _.findWhere(messages, { id: msg_id });
        if (message) {
            invalidate_caches(message.channel_ids);
            message.is_starred = data.starred;
            if (!message.is_starred) {
                remove_message_from_channel("channel_starred", message);
            }
            chat_manager.bus.trigger('update_message', message);
        }
    });
}

function on_mark_as_read_notification (data) {
    _.each(data.message_ids, function (msg_id) {
        var message = _.findWhere(messages, { id: msg_id });
        if (message) {
            invalidate_caches(message.channel_ids);
            remove_message_from_channel("channel_inbox", message);
            chat_manager.bus.trigger('update_message', message);
        }
    });
    if (data.channel_ids) {
        _.each(data.channel_ids, function (channel_id) {
            var channel = chat_manager.get_channel(channel_id);
            if (channel) {
                channel.needaction_counter -= data.message_ids.length;
            }
        });
    } else { // if no channel_ids specified, this is a 'mark all read' in the inbox
        _.each(channels, function (channel) {
            channel.needaction_counter = 0;
        });
    }
    needaction_counter -= data.message_ids.length;
    chat_manager.bus.trigger('update_needaction', needaction_counter);
}

function on_mark_as_unread_notification (data) {
    _.each(data.message_ids, function (message_id) {
        var message = _.findWhere(messages, { id: message_id });
        if (message) {
            invalidate_caches(message.channel_ids);
            add_channel_to_message(message, 'channel_inbox');
        }
    });
    _.each(data.channel_ids, function (channel_id) {
        var channel = chat_manager.get_channel(channel_id);
        if (channel) {
            channel.needaction_counter += data.message_ids.length;
        }
    });
    needaction_counter += data.message_ids.length;
    chat_manager.bus.trigger('update_needaction', needaction_counter);
}

function on_chat_session_notification (chat_session) {
    if ((chat_session.channel_type === "channel") && (chat_session.state === "open")) {
        add_channel(chat_session, {autoswitch: false});
        if (!chat_session.is_minimized && chat_session.info !== 'creation') {
            web_client.do_notify(_t("Invitation"), _t("You have been invited to: ") + chat_session.name);
        }
    }
    // partner specific change (open a detached window for example)
    if ((chat_session.state === "open") || (chat_session.state === "folded")) {
        if (chat_session.is_minimized && chat_manager.get_channel(chat_session.id)) {
            chat_manager.bus.trigger("open_chat", chat_session);
        }
    } else if (chat_session.state === "closed") {
        chat_manager.bus.trigger("close_chat", chat_session);
    }
}

// Public interface
//----------------------------------------------------------------------------------
var chat_manager = {
    post_message: post_channel_message,
    post_message_in_document: post_document_message,

    get_messages: function (options) {
        if ('channel_id' in options) { // channel message
            var channel = this.get_channel(options.channel_id);
            var channel_cache = get_channel_cache(channel, options.domain);
            if (channel_cache.loaded) {
                return $.when(channel_cache.messages);
            } else {
                return fetch_from_channel(channel, {domain: options.domain});
            }
        } else { // chatter message
        }
    },
    fetch: function (channel, domain) {
        return fetch_from_channel(channel, {domain: domain});
    },
    fetch_more: function (channel, domain) {
        return fetch_from_channel(channel, {domain: domain, load_more: true});
    },
    /**
     * Fetches chatter messages from their ids
     */
    fetch_messages: function (message_ids, options) {
        return fetch_document_messages(message_ids, options).then(function(result) {
            chat_manager.mark_as_read(message_ids);
            return result;
        });
    },
    toggle_star_status: function (message_id) {
        var msg = _.findWhere(messages, { id: message_id });

        return MessageModel.call('set_message_starred', [[message_id], !msg.is_starred]);
    },
    unstar_all: function () {
        return MessageModel.call('unstar_all', [[]], {});
    },
    mark_as_read: function (message_ids) {
        var ids = _.filter(message_ids, function (id) {
            var message = _.findWhere(messages, {id: id});
            return message.is_needaction;
        });
        if (ids.length) {
            return MessageModel.call('set_message_done', [ids]);
        } else {
            return $.when();
        }
    },
    mark_all_as_read: function (channel) {
        if ((!channel && needaction_counter) || (channel && channel.needaction_counter)) {
            return MessageModel.call('mark_all_as_read', channel ? [[channel.id]] : []);
        }
        return $.when();
    },
    undo_mark_as_read: function (message_ids, channel) {
        return MessageModel.call('mark_as_unread', [message_ids, [channel.id]]);
    },
    mark_channel_as_seen: function (channel) {
        if (channel.unread_counter > 0) {
            update_channel_unread_counter(channel, 0);
            channel_seen(channel);
        }
    },

    get_channels: function () {
        return _.clone(channels);
    },

    get_channel: function (id) {
        return _.findWhere(channels, {id: id});
    },

    all_history_loaded: function (channel, domain) {
        return get_channel_cache(channel, domain).all_history_loaded;
    },

    get_mention_partner_suggestions: function (channel) {
        if (!channel) {
            return mention_partner_suggestions;
        }
        if (!channel.members_deferred) {
            channel.members_deferred = ChannelModel
                .call("channel_fetch_listeners", [channel.uuid])
                .then(function (members) {
                    var suggestions = [];
                    _.each(mention_partner_suggestions, function (partners) {
                        suggestions.push(_.filter(partners, function (partner) {
                            return !_.findWhere(members, { id: partner.id });
                        }));
                    });

                    return [members].concat(suggestions);
                });
        }
        return channel.members_deferred;
    },

    get_emojis: function() {
        return emojis;
    },

    get_needaction_counter: function () {
        return needaction_counter;
    },

    get_discuss_ids: function () {
        return discuss_ids;
    },

    detach_channel: function (channel) {
        return ChannelModel.call("channel_minimize", [channel.uuid, true]);
    },
    remove_chatter_messages: function (model) {
        messages = _.reject(messages, function (message) {
            return message.channel_ids.length === 0 && message.model === model;
        });
    },
    bus: new core.Bus(),

    create_channel: function (name, type) {
        var method = type === "dm" ? "channel_get" : "channel_create";
        var args = type === "dm" ? [[name]] : [name, type];

        return ChannelModel
            .call(method, args)
            .then(add_channel);
    },
    join_channel: function (channel_id, options) {
        if (channel_id in channel_defs) {
            return channel_defs[channel_id];
        }
        var def = ChannelModel
            .call('channel_join_and_get_info', [[channel_id]])
            .then(function (result) {
                add_channel(result, options);
            });
        channel_defs[channel_id] = def;
        return def;
    },

    unsubscribe: function (channel) {
        var def;
        if (_.contains(['public', 'private'], channel.type)) {
            def = ChannelModel.call('action_unfollow', [[channel.id]]);
        } else {
            def = ChannelModel.call('channel_pin', [channel.uuid, false]);
        }
        return def.then(function () {
            channels = _.without(channels, channel);
            delete channel_defs[channel.id];
        });
    },
    close_chat_session: function (channel_id) {
        var channel = this.get_channel(channel_id);
        ChannelModel.call("channel_fold", [], {uuid : channel.uuid, state : "closed"});
    },
    fold_channel: function (channel_id) {
        var channel = this.get_channel(channel_id);
        return ChannelModel.call("channel_fold", [], {uuid : channel.uuid}).then(function () {
            channel.is_folded = !channel.is_folded;
        });
    },
};

// Initialization
// ---------------------------------------------------------------------------------
function init () {
    add_channel({
        id: "channel_inbox",
        name: _t("Inbox"),
        type: "static",
    }, { display_needactions: true });

    add_channel({
        id: "channel_starred",
        name: _t("Starred"),
        type: "static"
    });

    var load_channels = session.rpc('/mail/client_action').then(function (result) {
        _.each(result.channel_slots, function (channels) {
            _.each(channels, add_channel);
        });
        needaction_counter = result.needaction_inbox_counter;
        mention_partner_suggestions = result.mention_partner_suggestions;
    });

    var load_emojis = session.rpc("/mail/chat_init").then(function (result) {
        emojis = result.emoji;
        _.each(emojis, function(emoji) {
            emoji_substitutions[emoji.source] = emoji.substitution;
        });
    });

    var ir_model = new Model("ir.model.data");
    var load_menu_id = ir_model.call("xmlid_to_res_id", ["mail.mail_channel_menu_root_chat"]);
    var load_action_id = ir_model.call("xmlid_to_res_id", ["mail.mail_channel_action_client_chat"]);

    bus.on('notification', null, on_notification);

    return $.when(load_menu_id, load_action_id, load_channels, load_emojis).then(function (menu_id, action_id) {
        discuss_ids = {
            menu_id: menu_id,
            action_id: action_id,
        };
        bus.start_polling();
    });
}

chat_manager.is_ready = init();

return chat_manager;

});
