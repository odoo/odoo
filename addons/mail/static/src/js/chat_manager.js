odoo.define('mail.chat_manager', function (require) {
"use strict";

var bus = require('bus.bus').bus;
var utils = require('mail.utils');
var config = require('web.config');
var Bus = require('web.Bus');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var web_client = require('web.web_client');
var Class = require('web.Class');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');

var _t = core._t;
var _lt = core._lt;
var LIMIT = 25;
var preview_msg_max_size = 350;  // optimal for native english speakers
var ODOOBOT_ID = "ODOOBOT";

// Private model
//----------------------------------------------------------------------------------
var messages = [];
var channels = [];
var channels_preview_def;
var channel_defs = {};
var chat_unread_counter = 0;
var unread_conversation_counter = 0;
var emojis = [];
var emoji_substitutions = {};
var needaction_counter = 0;
var starred_counter = 0;
var mention_partner_suggestions = [];
var canned_responses = [];
var commands = [];
var discuss_menu_id;
var global_unread_counter = 0;
var pinned_dm_partners = [];  // partner_ids we have a pinned DM with
var client_action_open = false;

// Global unread counter and notifications
//----------------------------------------------------------------------------------
bus.on("window_focus", null, function() {
    global_unread_counter = 0;
    web_client.set_title_part("_chat");
});

function notify_incoming_message (msg, options) {
    if (bus.is_odoo_focused() && options.is_displayed) {
        // no need to notify
        return;
    }
    var title = _t('New message');
    if (msg.author_id[1]) {
        title = _.escape(msg.author_id[1]);
    }
    var content = utils.parse_and_transform(msg.body, utils.strip_html).substr(0, preview_msg_max_size);

    if (!bus.is_odoo_focused()) {
        global_unread_counter++;
        var tab_title = _.str.sprintf(_t("%d Messages"), global_unread_counter);
        web_client.set_title_part("_chat", tab_title);
    }

    utils.send_notification(web_client, title, content);
}

// Message and channel manipulation helpers
//----------------------------------------------------------------------------------

// options: channel_id, silent
function add_message (data, options) {
    options = options || {};
    var msg = _.findWhere(messages, { id: data.id });

    if (!msg) {
        msg = chat_manager.make_message(data);
        // Keep the array ordered by id when inserting the new message
        messages.splice(_.sortedIndex(messages, msg, 'id'), 0, msg);
        _.each(msg.channel_ids, function (channel_id) {
            var channel = chat_manager.get_channel(channel_id);
            if (channel) {
                add_to_cache(msg, []);
                if (options.domain && options.domain !== []) {
                    add_to_cache(msg, options.domain);
                }
                if (channel.hidden) {
                    channel.hidden = false;
                    chat_manager.bus.trigger('new_channel', channel);
                }
                if (channel.type !== 'static' && !msg.is_author && !msg.is_system_notification) {
                    if (options.increment_unread) {
                        update_channel_unread_counter(channel, channel.unread_counter+1);
                    }
                    if (channel.is_chat && options.show_notification) {
                        if (!client_action_open && config.device.size_class !== config.device.SIZES.XS) {
                            // automatically open chat window
                            chat_manager.bus.trigger('open_chat', channel, { passively: true });
                        }
                        var query = {is_displayed: false};
                        chat_manager.bus.trigger('anyone_listening', channel, query);
                        notify_incoming_message(msg, query);
                    }
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
        body: data.body || "",
        date: moment(time.str_to_datetime(data.date)),
        message_type: data.message_type,
        subtype_description: data.subtype_description,
        is_author: data.author_id && data.author_id[0] === session.partner_id,
        is_note: data.is_note,
        is_system_notification: (data.message_type === 'notification' && data.model === 'mail.channel')
            || data.info === 'transient_message',
        attachment_ids: data.attachment_ids || [],
        subject: data.subject,
        email_from: data.email_from,
        customer_email_status: data.customer_email_status,
        customer_email_data: data.customer_email_data,
        record_name: data.record_name,
        tracking_value_ids: data.tracking_value_ids,
        channel_ids: data.channel_ids,
        model: data.model,
        res_id: data.res_id,
        url: session.url("/mail/view?message_id=" + data.id),
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
        msg.displayed_author = (msg.author_id === ODOOBOT_ID) && "OdooBot" ||
                               msg.author_id && msg.author_id[1] ||
                               msg.email_from || _t('Anonymous');
    }

    // Don't redirect on author clicked of self-posted or OdooBot messages
    msg.author_redirect = !msg.is_author && msg.author_id !== ODOOBOT_ID;

    // Compute the avatar_url
    if (msg.author_id === ODOOBOT_ID) {
        msg.avatar_src = "/mail/static/src/img/odoo_o.png";
    } else if (msg.author_id && msg.author_id[0]) {
        msg.avatar_src = "/web/image/res.partner/" + msg.author_id[0] + "/image_small";
    } else if (msg.message_type === 'email') {
        msg.avatar_src = "/mail/static/src/img/email_icon.png";
    } else {
        msg.avatar_src = "/mail/static/src/img/smiley/avatar.jpg";
    }

    // add anchor tags to urls
    msg.body = utils.parse_and_transform(msg.body, utils.add_link);

    // Compute url of attachments
    _.each(msg.attachment_ids, function(a) {
        a.url = '/web/content/' + a.id + '?download=true';
    });

    // format date to the local only once by message
    // can not be done in preprocess, since it alter the original value
    if (msg.tracking_value_ids && msg.tracking_value_ids.length) {
        _.each(msg.tracking_value_ids, function(f) {
            if (_.contains(['date', 'datetime'], f.field_type)) {
                var format = (f.field_type === 'date') ? 'LL' : 'LLL';
                if (f.old_value) {
                    f.old_value = moment.utc(f.old_value).local().format(format);
                }
                if (f.new_value) {
                    f.new_value = moment.utc(f.new_value).local().format(format);
                }
            }
        });
    }

    return msg;
}

function add_channel_to_message (message, channel_id) {
    message.channel_ids.push(channel_id);
    message.channel_ids = _.uniq(message.channel_ids);
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
        channel = chat_manager.make_channel(data, options);
        channels.push(channel);
        // In case of a static channel (Inbox, Starred), the name is translated thanks to _lt
        // (lazy translate). In this case, channel.name is an object, not a string.
        channels = _.sortBy(channels, function (channel) { return _.isString(channel.name) ? channel.name.toLowerCase() : '' });
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
        server_type: data.channel_type,
        type: data.type || data.channel_type,
        all_history_loaded: false,
        uuid: data.uuid,
        is_detached: data.is_minimized,
        is_folded: data.state === "folded",
        autoswitch: 'autoswitch' in options ? options.autoswitch : true,
        hidden: options.hidden,
        display_needactions: options.display_needactions,
        mass_mailing: data.mass_mailing,
        group_based_subscription: data.group_based_subscription,
        needaction_counter: data.message_needaction_counter || 0,
        unread_counter: 0,
        last_seen_message_id: data.seen_message_id,
        cache: {'[]': {
            all_history_loaded: false,
            loaded: false,
            messages: [],
        }},
    };
    if (channel.type === "channel") {
        channel.type = data.public !== "private" ? "public" : "private";
    }
    if (_.size(data.direct_partner) > 0) {
        channel.type = "dm";
        channel.name = data.direct_partner[0].name;
        channel.direct_partner_id = data.direct_partner[0].id;
        channel.status = data.direct_partner[0].im_status;
        pinned_dm_partners.push(channel.direct_partner_id);
        bus.update_option('bus_presence_partner_ids', pinned_dm_partners);
    } else if ('anonymous_name' in data) {
        channel.name = data.anonymous_name;
    }
    if (data.last_message_date) {
        channel.last_message_date = moment(time.str_to_datetime(data.last_message_date));
    }
    channel.is_chat = !channel.type.match(/^(public|private|static)$/);
    if (data.message_unread_counter) {
        update_channel_unread_counter(channel, data.message_unread_counter);
    }
    return channel;
}

function remove_channel (channel) {
    if (!channel) { return; }
    if (channel.type === 'dm') {
        var index = pinned_dm_partners.indexOf(channel.direct_partner_id);
        if (index > -1) {
            pinned_dm_partners.splice(index, 1);
            bus.update_option('bus_presence_partner_ids', pinned_dm_partners);
        }
    }
    channels = _.without(channels, channel);
    delete channel_defs[channel.id];
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

function update_channel_unread_counter (channel, counter) {
    if (channel.unread_counter > 0 && counter === 0) {
        unread_conversation_counter = Math.max(0, unread_conversation_counter-1);
    } else if (channel.unread_counter === 0 && counter > 0) {
        unread_conversation_counter++;
    }
    if (channel.is_chat) {
        chat_unread_counter = Math.max(0, chat_unread_counter - channel.unread_counter + counter);
    }
    channel.unread_counter = counter;
    chat_manager.bus.trigger("update_channel_unread_counter", channel);
}

// Notification handlers
// ---------------------------------------------------------------------------------
function on_notification (notifications) {
    // sometimes, the web client receives unsubscribe notification and an extra
    // notification on that channel.  This is then followed by an attempt to
    // rejoin the channel that we just left.  The next few lines remove the
    // extra notification to prevent that situation to occur.
    var unsubscribed_notif = _.find(notifications, function (notif) {
        return notif[1].info === "unsubscribe";
    });
    if (unsubscribed_notif) {
        notifications = _.reject(notifications, function (notif) {
            return notif[0][1] === "mail.channel" && notif[0][2] === unsubscribed_notif[1].id;
        });
    }
    _.each(notifications, function (notification) {
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
        } else if (model === 'bus.presence') {
            // update presence of users
            on_presence_notification(notification[1]);
        }
    });
}

function on_needaction_notification (message) {
    message = add_message(message, {
        channel_id: 'channel_inbox',
        show_notification: true,
        increment_unread: true,
    });
    invalidate_caches(message.channel_ids);
    if (message.channel_ids.length !== 0) {
        needaction_counter++;
    }
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
    var channel_already_in_cache = true;
    if (message.channel_ids.length === 1) {
        channel_already_in_cache = !!chat_manager.get_channel(message.channel_ids[0]);
        def = chat_manager.join_channel(message.channel_ids[0], {autoswitch: false});
    } else {
        def = $.when();
    }
    def.then(function () {
        // don't increment unread if channel wasn't in cache yet as its unread counter has just been fetched
        add_message(message, { show_notification: true, increment_unread: channel_already_in_cache });
        invalidate_caches(message.channel_ids);
    });
}

function on_partner_notification (data) {
    if (data.info === "unsubscribe") {
        var channel = chat_manager.get_channel(data.id);
        if (channel) {
            var msg;
            if (_.contains(['public', 'private'], channel.type)) {
                msg = _.str.sprintf(_t('You unsubscribed from <b>%s</b>.'), channel.name);
            } else {
                msg = _.str.sprintf(_t('You unpinned your conversation with <b>%s</b>.'), channel.name);
            }
            remove_channel(channel);
            chat_manager.bus.trigger("unsubscribe_from_channel", data.id);
            web_client.do_notify(_("Unsubscribed"), msg);
        }
    } else if (data.type === 'toggle_star') {
        on_toggle_star_notification(data);
    } else if (data.type === 'mark_as_read') {
        on_mark_as_read_notification(data);
    } else if (data.type === 'mark_as_unread') {
        on_mark_as_unread_notification(data);
    } else if (data.info === 'channel_seen') {
        on_channel_seen_notification(data);
    } else if (data.info === 'transient_message') {
        on_transient_message_notification(data);
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
                starred_counter--;
            } else {
                add_to_cache(message, []);
                var channel_starred = chat_manager.get_channel('channel_starred');
                channel_starred.cache = _.pick(channel_starred.cache, "[]");
                starred_counter++;
            }
            chat_manager.bus.trigger('update_message', message);
        }
    });
    chat_manager.bus.trigger('update_starred', starred_counter);
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
                channel.needaction_counter = Math.max(channel.needaction_counter - data.message_ids.length, 0);
            }
        });
    } else { // if no channel_ids specified, this is a 'mark all read' in the inbox
        _.each(channels, function (channel) {
            channel.needaction_counter = 0;
        });
    }
    needaction_counter = Math.max(needaction_counter - data.message_ids.length, 0);
    chat_manager.bus.trigger('update_needaction', needaction_counter);
}

function on_mark_as_unread_notification (data) {
    _.each(data.message_ids, function (message_id) {
        var message = _.findWhere(messages, { id: message_id });
        if (message) {
            invalidate_caches(message.channel_ids);
            add_channel_to_message(message, 'channel_inbox');
            add_to_cache(message, []);
        }
    });
    var channel_inbox = chat_manager.get_channel('channel_inbox');
    channel_inbox.cache = _.pick(channel_inbox.cache, "[]");

    _.each(data.channel_ids, function (channel_id) {
        var channel = chat_manager.get_channel(channel_id);
        if (channel) {
            channel.needaction_counter += data.message_ids.length;
        }
    });
    needaction_counter += data.message_ids.length;
    chat_manager.bus.trigger('update_needaction', needaction_counter);
}

function on_channel_seen_notification (data) {
    var channel = chat_manager.get_channel(data.id);
    if (channel) {
        channel.last_seen_message_id = data.last_message_id;
        if (channel.unread_counter) {
            update_channel_unread_counter(channel, 0);
        }
    }
}

function on_chat_session_notification (chat_session) {
    var channel;
    if ((chat_session.channel_type === "channel") && (chat_session.state === "open")) {
        add_channel(chat_session, {autoswitch: false});
        if (!chat_session.is_minimized && chat_session.info !== 'creation') {
            web_client.do_notify(_t("Invitation"), _t("You have been invited to: ") + chat_session.name);
        }
    }
    // partner specific change (open a detached window for example)
    if ((chat_session.state === "open") || (chat_session.state === "folded")) {
        channel = chat_session.is_minimized && chat_manager.get_channel(chat_session.id);
        if (channel) {
            channel.is_detached = true;
            channel.is_folded = (chat_session.state === "folded");
            chat_manager.bus.trigger("open_chat", channel);
        }
    } else if (chat_session.state === "closed") {
        channel = chat_manager.get_channel(chat_session.id);
        if (channel) {
            channel.is_detached = false;
            chat_manager.bus.trigger("close_chat", channel, {keep_open_if_unread: true});
        }
    }
}

function on_presence_notification (data) {
    var dm = chat_manager.get_dm_from_partner_id(data.id);
    if (dm) {
        dm.status = data.im_status;
        chat_manager.bus.trigger('update_dm_presence', dm);
    }
}

function on_transient_message_notification (data) {
    var last_message = _.last(messages);
    data.id = (last_message ? last_message.id : 0) + 0.01;
    data.author_id = data.author_id || ODOOBOT_ID;
    add_message(data);
}

// Public interface
//----------------------------------------------------------------------------------
var ChatManager =  Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    // these two functions are exposed for extensibility purposes and shouldn't be called by other modules
    make_message: make_message,
    make_channel: make_channel,

    init: function (parent) {
        var self = this;
        Mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);

        this.bus = new Bus();
        this.bus.on('client_action_open', null, function (open) {
            client_action_open = open;
        });

        bus.on('notification', null, on_notification);

        this.channel_seen = _.throttle(function (channel) {
            return self.rpc('mail.channel', 'channel_seen')
                .args([[channel.id]])
                .exec({shadow: true});
        }, 3000);
    },

    start: function () {
        this.is_ready = session.is_bound.then(function(){
                return session.rpc('/mail/client_action');
            }).then(this._onMailClientAction.bind(this));

        add_channel({
            id: "channel_inbox",
            name: _lt("Inbox"),
            type: "static",
        }, { display_needactions: true });

        add_channel({
            id: "channel_starred",
            name: _lt("Starred"),
            type: "static"
        });
    },

    _onMailClientAction: function (result) {
        _.each(result.channel_slots, function (channels) {
            _.each(channels, add_channel);
        });
        needaction_counter = result.needaction_inbox_counter;
        starred_counter = result.starred_counter;
        commands = _.map(result.commands, function (command) {
            return _.extend({ id: command.name }, command);
        });
        mention_partner_suggestions = result.mention_partner_suggestions;
        discuss_menu_id = result.menu_id;

        // Shortcodes: canned responses and emojis
        _.each(result.shortcodes, function (s) {
            if (s.shortcode_type === 'text') {
                canned_responses.push(_.pick(s, ['id', 'source', 'substitution']));
            } else {
                emojis.push(_.pick(s, ['id', 'source', 'substitution', 'description']));
                emoji_substitutions[_.escape(s.source)] = s.substitution;
            }
        });
        bus.start_polling();
    },

    // options: domain, load_more
    _fetchFromChannel: function (channel, options) {
        options = options || {};
        var domain =
            (channel.id === "channel_inbox") ? [['needaction', '=', true]] :
            (channel.id === "channel_starred") ? [['starred', '=', true]] :
                                                [['channel_ids', 'in', channel.id]];
        var cache = get_channel_cache(channel, options.domain);

        if (options.domain) {
            domain = domain.concat(options.domain || []);
        }
        if (options.load_more) {
            var min_message_id = cache.messages[0].id;
            domain = [['id', '<', min_message_id]].concat(domain);
        }

        return this.rpc('mail.message', 'message_fetch')
            .args([domain])
            .kwargs({limit: LIMIT, context: session.user_context})
            .exec()
            .then(function (msgs) {
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
    },
    // options: force_fetch
    _fetchDocumentMessages : function (ids, options) {
        var loaded_msgs = _.filter(messages, function (message) {
            return _.contains(ids, message.id);
        });
        var loaded_msg_ids = _.pluck(loaded_msgs, 'id');

        options = options || {};
        if (options.force_fetch || _.difference(ids.slice(0, LIMIT), loaded_msg_ids).length) {
            var ids_to_load = _.difference(ids, loaded_msg_ids).slice(0, LIMIT);

            return this.rpc('mail.message', 'message_format')
                .args([ids_to_load])
                .kwargs({context: session.user_context})
                .exec()
                .then(function (msgs) {
                    var processed_msgs = [];
                    _.each(msgs, function (msg) {
                        processed_msgs.push(add_message(msg, {silent: true}));
                    });
                    return _.sortBy(loaded_msgs.concat(processed_msgs), function (msg) {
                        return msg.id;
                    });
                });
        } else {
            return $.when(loaded_msgs);
        }
    },

    post_message: function (data, options) {
        var self = this;
        options = options || {};

        // This message will be received from the mail composer as html content subtype
        // but the urls will not be linkified. If the mail composer takes the responsibility
        // to linkify the urls we end up with double linkification a bit everywhere.
        // Ideally we want to keep the content as text internally and only make html
        // enrichment at display time but the current design makes this quite hard to do.
        var body = utils.parse_and_transform(_.str.trim(data.content), utils.add_link);

        var msg = {
            partner_ids: data.partner_ids,
            body: body,
            attachment_ids: data.attachment_ids,
        };
        if ('subject' in data) {
            msg.subject = data.subject;
        }
        if ('channel_id' in options) {
            // post a message in a channel or execute a command
            return this.rpc('mail.channel', data.command ? 'execute_command' : 'message_post')
                .args([options.channel_id])
                .kwargs(_.extend(msg, {
                    message_type: 'comment',
                    content_subtype: 'html',
                    subtype: 'mail.mt_comment',
                    command: data.command,
                }))
                .exec();
        }
        if ('model' in options && 'res_id' in options) {
            // post a message in a chatter
            _.extend(msg, {
                content_subtype: data.content_subtype,
                context: data.context,
                message_type: data.message_type,
                subtype: data.subtype,
                subtype_id: data.subtype_id,
            });

            return this.rpc(options.model, 'message_post')
                .args([options.res_id])
                .kwargs(msg)
                .exec()
                .then(function (msg_id) {
                    return self.rpc('mail.message', 'message_format')
                        .args([msg_id])
                        .exec()
                        .then(function (msgs) {
                            msgs[0].model = options.model;
                            msgs[0].res_id = options.res_id;
                            add_message(msgs[0]);
                        });
                });
        }
    },

    get_message: function (id) {
        return _.findWhere(messages, {id: id});
    },
    get_messages: function (options) {
        var channel;

        if ('channel_id' in options && options.load_more) {
            // get channel messages, force load_more
            channel = this.get_channel(options.channel_id);
            return this._fetchFromChannel(channel, {domain: options.domain || {}, load_more: true});
        }
        if ('channel_id' in options) {
            // channel message, check in cache first
            channel = this.get_channel(options.channel_id);
            var channel_cache = get_channel_cache(channel, options.domain);
            if (channel_cache.loaded) {
                return $.when(channel_cache.messages);
            } else {
                return this._fetchFromChannel(channel, {domain: options.domain});
            }
        }
        if ('ids' in options) {
            // get messages from their ids (chatter is the main use case)
            return this._fetchDocumentMessages(options.ids, options).then(function(result) {
                chat_manager.mark_as_read(options.ids);
                return result;
            });
        }
        if ('model' in options && 'res_id' in options) {
            // get messages for a chatter, when it doesn't know the ids (use
            // case is when using the full composer)
            var domain = [['model', '=', options.model], ['res_id', '=', options.res_id]];
            this.rpc('mail.message', 'message_fetch')
                .args([domain])
                .kwargs({limit: 30})
                .exec()
                .then(function (msgs) {
                    return _.map(msgs, add_message);
                });
        }
    },
    toggle_star_status: function (message_id) {
        return this.rpc('mail.message', 'toggle_message_starred')
            .args([[message_id]])
            .exec();
    },
    unstar_all: function () {
        return this.rpc('mail.message', 'unstar_all')
            .args([[]])
            .exec();
    },
    mark_as_read: function (message_ids) {
        var ids = _.filter(message_ids, function (id) {
            var message = _.findWhere(messages, {id: id});
            // If too many messages, not all are fetched, and some might not be found
            return !message || message.is_needaction;
        });
        if (ids.length) {
            return this.rpc('mail.message', 'set_message_done')
                .args([ids])
                .exec();
        } else {
            return $.when();
        }
    },
    mark_all_as_read: function (channel, domain) {
        if ((channel.id === "channel_inbox" && needaction_counter) || (channel && channel.needaction_counter)) {
            return this.rpc('mail.message', 'mark_all_as_read')
                .kwargs({channel_ids: channel.id !== "channel_inbox" ? [channel.id] : [], domain: domain})
                .exec();
        }
        return $.when();
    },
    undo_mark_as_read: function (message_ids, channel) {
        return this.rpc('mail.message', 'mark_as_unread')
            .args([message_ids, [channel.id]])
            .exec();
    },
    mark_channel_as_seen: function (channel) {
        if (channel.unread_counter > 0 && channel.type !== 'static') {
            update_channel_unread_counter(channel, 0);
            this.channel_seen(channel);
        }
    },

    get_channels: function () {
        return _.clone(channels);
    },

    get_channel: function (id) {
        return _.findWhere(channels, {id: id});
    },

    get_dm_from_partner_id: function (partner_id) {
        return _.findWhere(channels, {direct_partner_id: partner_id});
    },

    all_history_loaded: function (channel, domain) {
        return get_channel_cache(channel, domain).all_history_loaded;
    },

    get_mention_partner_suggestions: function (channel) {
        if (!channel) {
            return mention_partner_suggestions;
        }
        if (!channel.members_deferred) {
            channel.members_deferred = this.rpc('mail.channel', "channel_fetch_listeners")
                .args([channel.uuid])
                .exec({shadow: true})
                .then(function (members) {
                    var suggestions = [];
                    _.each(mention_partner_suggestions, function (partners) {
                        suggestions.push(_.filter(partners, function (partner) {
                            return !_.findWhere(members, { id: partner.id });
                        }));
                    });

                    return [members];
                });
        }
        return channel.members_deferred;
    },

    get_commands: function (channel) {
        return _.filter(commands, function (command) {
            return !command.channel_types || _.contains(command.channel_types, channel.server_type);
        });
    },
    get_canned_responses: function () {
        return canned_responses;
    },

    get_emojis: function() {
        return emojis;
    },

    get_needaction_counter: function () {
        return needaction_counter;
    },
    get_starred_counter: function () {
        return starred_counter;
    },
    get_chat_unread_counter: function () {
        return chat_unread_counter;
    },
    get_unread_conversation_counter: function () {
        return unread_conversation_counter;
    },

    get_last_seen_message: function (channel) {
        if (channel.last_seen_message_id) {
            var messages = channel.cache['[]'].messages;
            var msg = _.findWhere(messages, {id: channel.last_seen_message_id});
            if (msg) {
                var i = _.sortedIndex(messages, msg, 'id') + 1;
                while (i < messages.length && (messages[i].is_author || messages[i].is_system_notification)) {
                    msg = messages[i];
                    i++;
                }
                return msg;
            }
        }
    },

    get_discuss_menu_id: function () {
        return discuss_menu_id;
    },

    detach_channel: function (channel) {
        return this.rpc('mail.channel', "channel_minimize")
            .args([channel.uuid, true])
            .exec({shadow: true});
    },
    remove_chatter_messages: function (model) {
        messages = _.reject(messages, function (message) {
            return message.channel_ids.length === 0 && message.model === model;
        });
    },

    create_channel: function (name, type) {
        var method = type === "dm" ? "channel_get" : "channel_create";
        var args = type === "dm" ? [[name]] : [name, type];

        return this.rpc('mail.channel', method)
            .args(args)
            .exec()
            .then(add_channel);
    },
    join_channel: function (channel_id, options) {
        if (channel_id in channel_defs) {
            // prevents concurrent calls to channel_join_and_get_info
            return channel_defs[channel_id];
        }
        var channel = this.get_channel(channel_id);
        if (channel) {
            // channel already joined
            channel_defs[channel_id] = $.when(channel);
        } else {
            channel_defs[channel_id] = this.rpc('mail.channel', 'channel_join_and_get_info')
                .args([[channel_id]])
                .exec()
                .then(function (result) {
                    return add_channel(result, options);
                });
        }
        return channel_defs[channel_id];
    },
    open_and_detach_dm: function (partner_id) {
        return this.rpc('mail.channel', 'channel_get_and_minimize')
            .args([[partner_id]])
            .exec()
            .then(add_channel);
    },
    open_channel: function (channel) {
        chat_manager.bus.trigger(client_action_open ? 'open_channel' : 'detach_channel', channel);
    },

    unsubscribe: function (channel) {
        if (_.contains(['public', 'private'], channel.type)) {
            return this.rpc('mail.channel', 'action_unfollow')
                .args([[channel.id]])
                .exec();
        } else {
            return this.rpc('mail.channel', 'channel_pin')
                .args([channel.uuid, false])
                .exec();
        }
    },
    close_chat_session: function (channel_id) {
        var channel = this.get_channel(channel_id);
        this.rpc('mail.channel', "channel_fold")
            .kwargs({uuid : channel.uuid, state : "closed"})
            .exec({shadow: true});
    },
    fold_channel: function (channel_id, folded) {
        var args = {
            uuid: this.get_channel(channel_id).uuid,
        };
        if (_.isBoolean(folded)) {
            args.state = folded ? 'folded' : 'open';
        }
        return this.rpc('mail.channel', "channel_fold")
            .kwargs(args)
            .exec({shadow: true});
    },
    /**
     * Special redirection handling for given model and id
     *
     * If the model is res.partner, and there is a user associated with this
     * partner which isn't the current user, open the DM with this user.
     * Otherwhise, open the record's form view, if this is not the current user's.
     */
    redirect: function (res_model, res_id, dm_redirection_callback) {
        var self = this;
        var redirect_to_document = function (res_model, res_id, view_id) {
            web_client.do_action({
                type:'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: res_model,
                views: [[view_id || false, 'form']],
                res_id: res_id,
            });
        };
        if (res_model === "res.partner") {
            var domain = [["partner_id", "=", res_id]];
            this.rpc('res.users', "search")
                .args([domain])
                .exec()
                .then(function (user_ids) {
                    if (user_ids.length && user_ids[0] !== session.uid && dm_redirection_callback) {
                        self.create_channel(res_id, 'dm').then(dm_redirection_callback);
                    } else {
                        redirect_to_document(res_model, res_id);
                    }
                });
        } else {
            this.rpc(res_model, 'get_formview_id')
                .args([[res_id], session.user_context])
                .exec()
                .then(function (view_id) {
                    redirect_to_document(res_model, res_id, view_id);
                });
        }
    },

    get_channels_preview: function (channels) {
        var channels_preview = _.map(channels, function (channel) {
            var info = _.pick(channel, 'id', 'is_chat', 'name', 'status', 'unread_counter');
            info.last_message = _.last(channel.cache['[]'].messages);
            if (!info.is_chat) {
                info.image_src = '/web/image/mail.channel/'+channel.id+'/image_small';
            } else if (channel.direct_partner_id) {
                info.image_src = '/web/image/res.partner/'+channel.direct_partner_id+'/image_small';
            } else {
                info.image_src = '/mail/static/src/img/smiley/avatar.jpg';
            }
            return info;
        });
        var missing_channels = _.where(channels_preview, {last_message: undefined});
        if (!channels_preview_def) {
            if (missing_channels.length) {
                var missing_channel_ids = _.pluck(missing_channels, 'id');
                channels_preview_def = this.rpc('mail.channel', 'channel_fetch_preview')
                    .args([missing_channel_ids])
                    .exec({shadow: true});
            } else {
                channels_preview_def = $.when();
            }
        }
        return channels_preview_def.then(function (channels) {
            _.each(missing_channels, function (channel_preview) {
                var channel = _.findWhere(channels, {id: channel_preview.id});
                if (channel) {
                    channel_preview.last_message = add_message(channel.last_message);
                }
            });
            return _.filter(channels_preview, function (channel) {
                return channel.last_message;  // remove empty channels
            });
        });
    },
    get_message_body_preview: function (message_body) {
        return utils.parse_and_transform(message_body, utils.inline);
    },

    search_partner: function (search_val, limit) {
        var def = $.Deferred();
        var values = [];
        // search among prefetched partners
        var search_regexp = new RegExp(_.str.escapeRegExp(utils.unaccent(search_val)), 'i');
        _.each(mention_partner_suggestions, function (partners) {
            if (values.length < limit) {
                values = values.concat(_.filter(partners, function (partner) {
                    return session.partner_id !== partner.id && search_regexp.test(partner.name);
                })).splice(0, limit);
            }
        });
        if (!values.length) {
            // extend the research to all users
            def = this.rpc('res.partner', 'im_search')
                .args([search_val, limit || 20])
                .exec({shadow: true});
        } else {
            def = $.when(values);
        }
        return def.then(function (values) {
            var autocomplete_data = _.map(values, function (value) {
                return { id: value.id, value: value.name, label: value.name };
            });
            return _.sortBy(autocomplete_data, 'label');
        });
    },
});

var CallService = Class.extend(Mixins.EventDispatcherMixin, Mixins.ServiceProvider, {
    init: function () {
        Mixins.ServiceProvider.init.call(this);
        Mixins.EventDispatcherMixin.init.call(this);
    },
});
var chat_manager = new ChatManager(new CallService());
chat_manager.start();

return chat_manager;

});
