odoo.define('mail.chat_manager', function (require) {
"use strict";

var bus = require('bus.bus').bus;
var core = require('web.core');
var data = require('web.data');
var Model = require('web.Model');
var session = require('web.session');
var web_client = require('web.web_client');

var _t = core._t;
var LIMIT = 20;
var preview_msg_max_size = 50;

var MessageModel = new Model('mail.message', session.context);
var ChannelModel = new Model('mail.channel', session.context);

// Private model
//----------------------------------------------------------------------------------
var messages = [];
var channels = [];
var emojis = [];
var emoji_substitutions = {};
var needaction_counter = 0;

// Message and channel manipulation helpers
//----------------------------------------------------------------------------------

// options: channel_id, silent
function add_message (data, options) {
    options = options || {};
    var msg = _.findWhere(messages, { id: data.id });

    if (!msg) {
        msg = make_message(data, options.channel_id);
        // Keep the array ordered by date when inserting the new message
        messages.splice(_.sortedIndex(messages, msg, 'date'), 0, msg);
        if (options.channel_id) {
            var channel = _.findWhere(channels, {id: options.channel_id});
            if (channel.hidden) {
                channel.hidden = false;
                chat_manager.bus.trigger('new_channel', channel);
            }
            if (!_.contains(["static", "public", "private"], channel.type) && (options.show_notification)) {
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
        }
        if (!options.silent) {
            chat_manager.bus.trigger('new_message', msg);
        }
    } else if (msg && options.channel_id !== undefined) {
        add_channel_to_message(msg, options.channel_id);
    }
    return msg;
}

function make_message (data, channel_id) {
    var msg = {
        id: data.id,
        author_id: data.author_id,
        body: data.body,
        date: data.date,
        message_type: data.message_type,
        is_note: data.is_note,
        attachment_ids: data.attachment_ids,
        subject: data.subject,
        email_from: data.email_from,
        record_name: data.record_name,
        tracking_value_ids: data.tracking_value_ids,
        channel_ids: (channel_id !== undefined ? [channel_id] : []),
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
    var channel = _.findWhere(channels, {id: data.id});
    if (channel) {
        if (channel.is_folded !== (data.state === "folded")) {
            channel.is_folded = (data.state === "folded");
            chat_manager.bus.trigger("channel_toggle_fold", channel);
        }
    } else {
        channel = make_channel(data, options);
        channels.push(channel);
        if (!options.silent) {
            chat_manager.bus.trigger("new_channel", channel);
        }
        if (channel.is_detached) {
            chat_manager.bus.trigger("open_chat", channel);
        }
    }
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
        cache: {'[]': {
            all_history_loaded: false,
            loaded: false,
            message_ids: [],
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
            message_ids: [],
        };
    }
    return channel.cache[stringified_domain];
}

function remove_message_from_channel (channel_id, message) {
    message.channel_ids = _.without(message.channel_ids, channel_id);
    var channel = _.findWhere(channels, { id: channel_id });
    _.each(channel.cache, function (cache) {
        cache.message_ids = _.without(cache.message_ids, message.id);
    });
}

// options: domain, load_more
function fetch_from_channel (channel, options) {
    var domain =
        (channel.id === "channel_inbox") ? [['needaction', '=', true]] :
        (channel.id === "channel_starred") ? [['starred', '=', true]] :
                                            [['channel_ids', 'in', channel.id]];

    options = options || {};
    if (options.domain) {
        domain = new data.CompoundDomain(domain, options.domain || []);
    }
    if (options.load_more) {
        var min_message_id = _.chain(messages)
            .filter(function (msg) { return _.contains(msg.channel_ids, channel.id); })
            .pluck("id")
            .min()
            .value();

        domain = new data.CompoundDomain([['id', '<', min_message_id]], domain);
    }

    return MessageModel.call('message_fetch', [domain], {limit: LIMIT}).then(function (msgs) {
        var cache = get_channel_cache(channel, options.domain);

        cache.message_ids = _.uniq(cache.message_ids.concat(_.pluck(msgs, 'id')));
        if (!cache.all_history_loaded) {
            cache.all_history_loaded =  msgs.length < LIMIT;
        }
        cache.loaded = true;

        _.each(msgs, function (msg) {
            add_message(msg, {channel_id: channel.id, silent: true});
        });
        return _.filter(messages, function (m) {
            return _.contains(cache.message_ids, m.id);
        });
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
                return $.when(_.filter(messages, function (message) {
                    return _.contains(message.channel_ids, options.channel_id);
                }));
            } else {
                return fetch_from_channel(channel);
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
        return fetch_document_messages(message_ids, options);
    },
    toggle_star_status: function (message_id) {
        var msg = _.findWhere(messages, { id: message_id });

        return MessageModel.call('set_message_starred', [[message_id], !msg.is_starred]).then(function () {
            msg.is_starred = !msg.is_starred;
            if (!msg.is_starred) {
                remove_message_from_channel("channel_starred", msg);
            }
            chat_manager.bus.trigger('update_message', msg);
        });
    },
    mark_as_read: function (message_id) {
        return MessageModel.call('set_message_done', [[message_id]]).then(function () {
            var message = _.findWhere(messages, { id: message_id });
            remove_message_from_channel("channel_inbox", message);
            chat_manager.bus.trigger('update_message', message);
            needaction_counter = needaction_counter - 1;
            chat_manager.bus.trigger('update_needaction', needaction_counter);
        });
    },

    get_channels: function () {
        return _.clone(channels);
    },

    get_channel: function (id) {
        return _.findWhere(channels, {id: id}) || channels[0];
    },

    all_history_loaded: function (channel, domain) {
        return get_channel_cache(channel, domain).all_history_loaded;
    },

    get_emojis: function() {
        return emojis;
    },

    get_needaction_counter: function () {
        return needaction_counter;
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
            .then(add_channel)
            .then(function () {
                bus.restart_poll();
            });
    },
    join_channel: function (channel_id, options) {
        return ChannelModel
            .call('channel_join_and_get_info', [[channel_id]])
            .then(function (result) {
                add_channel(result, options);
            });
    },

    unsubscribe: function (channel) {
        var def;
        if (channel.type === "dm") {
            def = ChannelModel.call('channel_pin', [channel.uuid, false]);
        } else {
            def = ChannelModel.call('action_unfollow', [[channel.id]]);
        }
        return def.then(function () {
            channels = _.without(channels, channel);
        });
    },
    close_chat_session: function (channel_id) {
        var channel = _.findWhere(channels, {id: channel_id});
        ChannelModel.call("channel_fold", [], {uuid : channel.uuid, state : "closed"});
    },
    fold_channel: function (channel_id) {
        var channel = _.findWhere(channels, {id: channel_id});
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
        _.each(result.channel_slots.channel_channel, add_channel);
        _.each(result.channel_slots.channel_private_group, add_channel);
        _.each(result.channel_slots.channel_direct_message, add_channel);
        needaction_counter = result.needaction_inbox_counter;
    });

    var load_emojis = session.rpc("/mail/chat_init").then(function (result) {
        emojis = result.emoji;
        _.each(emojis, function(emoji) {
            emoji_substitutions[emoji.source] = emoji.substitution;
        });
    });

    bus.on('notification', null, function (notification) {
        var model = notification[0][1];
        if (model === 'ir.needaction') {
            // new message in the inbox
            var message = notification[1];
            message = add_message(message, { channel_id: 'channel_inbox', show_notification: true} );
            needaction_counter = needaction_counter + 1;
            chat_manager.bus.trigger('update_needaction', needaction_counter);
        }
        if (model === 'mail.channel') {
            // new message in a channel
            var message = notification[1];
            var channel_id = message.channel_ids[0];
            // fetch the channel info if not done already
            var channel = _.findWhere(channels, {id: channel_id});
            var channel_ready;
            if (!channel) {
                channel_ready = chat_manager.join_channel(channel_id, { autoswitch: false });
            }
            $.when(channel_ready).then(function () {
                add_message(message, { channel_id: channel_id, show_notification: true });
            });
        }
        if (model === 'res.partner') {
            var chat_session = notification[1];
            if ((chat_session.channel_type === "channel") && (chat_session.public === "private") && (chat_session.state === "open")) {
                add_channel(chat_session, {autoswitch: false});
                if (!chat_session.is_minimized) {
                    web_client.do_notify(_t("Private Channel"), _t("You have been invited to: ") + chat_session.name);
                }
            }
            // partner specific change (open a detached window for example)
            if ((chat_session.state === "open") || (chat_session.state === "folded")) {
                add_channel(chat_session, {autoswitch: false, silent: true, hidden: true});
                if (chat_session.is_minimized) {
                    chat_manager.bus.trigger("open_chat", chat_session);
                }
            }
            if (chat_session.state === "closed") {
                chat_manager.bus.trigger("close_chat", chat_session);
            }
        }
    });

    return $.when(load_channels, load_emojis).then(function () {
        bus.start_polling();
        return chat_manager;
    });
}

return init();

});
