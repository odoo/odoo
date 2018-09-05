odoo.define('mail.ChatManager', function (require) {
"use strict";

var utils = require('mail.utils');

var AbstractService = require('web.AbstractService');
var Bus = require('web.Bus');
var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var web_client = require('web.web_client');

var _t = core._t;
var _lt = core._lt;

var LIMIT = 30; // max number of fetched messages from the server
var PREVIEW_MSG_MAX_SIZE = 350;  // optimal for native english speakers
var ODOOBOT_ID = "ODOOBOT"; // default author_id for messages

var emojiUnicodes={
    ":)":"😊", ":-)":"😊","=)":"😊", ":]":"😊",
    ":D":"😃",":-D":"😃","=D":"😃",
    "xD":"😆","XD":"😆",
    "x'D":"😂",
    ";)":"😉",";-)":"😉",
    "B)":"😎","8)":"😎","B-)":"😎","8-)":"😎",
    ";p":"😜",";P":"😜",
    ":p":"😋",":P":"😋",":-p":"😋",":-P":"😋","=P":"😋",
    "xp":"😝","xP":"😝",
    "o_o":"😳",
    ":|":"😐",":-|":"😐",
    ":/":"😕",":-/":"😕",
    ":(":"😞",
    ":@":"😱",
    ":O":"😲",":-O":"😲",":o":"😲",":-o":"😲",
    ":'o":"😨",  
    "3:(":"😠",">:(":"😠","3:":"😠",
    "3:)":"😈",">:)":"😈",
    ":*":"😘",":-*":"😘",
    "o:)":"😇",
    ":'(":"😢",
    ":'-(":"😭",":\"(":"😭",
    "&lt;3":"❤️",":heart":"❤️",
    ":heart_eyes":"😍",
    ":turban":"👳",
    ":+1":"👍",
    ":-1":"👎",
    ":ok":"👌",
    ":poop":"💩",
    ":no_see":"🙈",
    ":no_hear":"🙉",
    ":no_speak":"🙊",
    ":bug":"🐞",
    ":kitten":"😺",
    ":bear":"🐻",
    ":snail":"🐌",
    ":boar":"🐗",
    ":clover":"🍀",
    ":sunflower":"🌹",
    ":fire":"🔥",
    ":sun":"☀️",
    ":partly_sunny:":"⛅️",
    ":rainbow":"🌈",
    ":cloud":"☁️",
    ":zap":"⚡️",
    ":star":"⭐️",
    ":cookie":"🍪",
    ":pizza":"🍕",  
    ":hamburger":"🍔", 
    ":fries":"🍟",
    ":cake":"🎂",
    ":cake_part":"🍰",
    ":coffee":"☕️",
    ":banana":"🍌",
    ":sushi":"🍣",
    ":rice_ball":"🍙",
    ":beer":"🍺",
    ":wine":"🍷",
    ":cocktail":"🍸",
    ":tropical":"🍹",
    ":beers":"🍻",
    ":ghost":"👻",
    ":skull":"💀",
    ":et":"👽",":alien":"👽",
    ":party":"🎉",
    ":trophy":"🏆",
    ":key":"🔑",
    ":pin":"📌",
    ":postal_horn":"📯",
    ":music":"🎵",
    ":trumpet":"🎺",
    ":guitar":"🎸",
    ":soccer":"⚽️",
    ":football":"🏈",
    ":8ball":"🎱",
    ":clapper":"🎬",
    ":microphone":"🎤",
    ":cheese": "🧀",
    };

/**
 * This service handles everything about chat channels and messages.
 *
 * There are basically two points of entry:
 *
 *      1. Calling a public method by means of 'this.call'
 *      2. Receiving events on busBus (e.g. 'notification')
 */
var ChatManager =  AbstractService.extend({
    name: 'chat_manager',
    dependencies: ['ajax', 'bus_service'],
    CHANNEL_SEEN_THROTTLE: 3000,
    /**
     * @override
     */
    init: function () {
        var self = this;
        this._super.apply(this, arguments);

        this.messages = [];
        this.channels = [];
        this.messageFailures = [];
        this.channelsPreviewDef;
        this.channelDefs = {};
        this.unreadConversationCounter = 0;
        this.emojis = [];
        this.needactionCounter = 0;
        this.starredCounter = 0;
        this.moderationCounter = 0;
        this.moderatedChannelIDs = [];
        this.mentionPartnerSuggestions = [];
        this.cannedResponses = [];
        this.commands = [];
        this.discussMenuID;
        this.globalUnreadCounter = 0;
        this.pinnedDmPartners = [];  // partner_ids we have a pinned DM with
        this.discussOpen = false;

        this.chatBus = new Bus(this);
        this.busBus = this.call('bus_service', 'getBus');

        this.chatBus.on('discuss_open', null, function (open) {
            self.discussOpen = open;
        });

        this.busBus.on('notification', this, this._onNotification);
        this.busBus.on('window_focus', this, this._onWindowFocus);

        // TODO create private fonction on prototype
        this.channelSeen = _.throttle(function (channel) {
            return self._rpc({
                    model: 'mail.channel',
                    method: 'channel_seen',
                    args: [[channel.id]],
                }, {
                    shadow: true
                });
        }, self.CHANNEL_SEEN_THROTTLE);

        this._isReady = this._initMessaging();

        // Add static channels
        this._addChannel({
            id: "channel_inbox",
            name: _lt("Inbox"),
            type: "static",
        }, { displayNeedactions: true });
        this._addChannel({
            id: "channel_starred",
            name: _lt("Starred"),
            type: "static"
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Closes the chat window of a corresponding channel.
     * This operation is executed server-side and the chat window will be
     * folded in all potential tabs from all browsers.
     *
     * @param  {integer|string} channelID
     * @return {$.Promise}
     */
    closeChatSession: function (channelID) {
        var channel = this.getChannel(channelID);
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_fold',
                kwargs: {uuid : channel.uuid, state : 'closed'},
            }, {shadow: true});
    },
    /**
     * Creates a channel
     *
     * @param  {integer|string} name id of partner (in case of dm) or name
     * @param  {string} type ['dm', 'public', 'private']
     * @return {$.Promise}
     */
    createChannel: function (name, type) {
        var method = type === "dm" ? "channel_get" : "channel_create";
        var args = type === "dm" ? [[name]] : [name, type];
        var context = _.extend({isMobile: config.device.isMobile}, session.user_context);
        return this._rpc({
                model: 'mail.channel',
                method: method,
                args: args,
                kwargs: {context: context},
            })
            .then(this._addChannel.bind(this));
    },
    /**
     * Open the chat window for a given channel
     * (in all potential tabs from all browsers)
     *
     * @param  {integer} channelID
     * @return {$.Promise}
     */
    detachChannel: function (channelID) {
        var channel = this.getChannel(channelID);
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_minimize',
                args: [channel.uuid, true],
            }, {
                shadow: true,
            });
    },
    /**
     * Folds/Minimize the chat window
     * (in all potential tabs from all browsers)
     *
     * @param  {integer} channelID
     * @param  {boolean} folded
     * @return {$.Promise}
     */
    foldChannel: function (channelID, folded) {
        var args = {
            uuid: this.getChannel(channelID).uuid,
        };
        if (_.isBoolean(folded)) {
            args.state = folded ? 'folded' : 'open';
        }
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_fold',
                kwargs: args,
            }, {shadow: true});
    },
    /**
     * Returns the list of canned responses
     * A canned response is a pre-formatted text that is triggered with
     * some keystrokes, such as with ':'.
     *
     * @return {Array} array of Objects (mail.shortcode)
     */
    getCannedResponses: function () {
        return this.cannedResponses;
    },
    /**
     * Returns a channel corresponding to the given id.
     *
     * @param  {string|integer} id e.g. 'channel_inbox', 'channel_starred'
     * @return {Object|undefined} the channel, if it exists
     */
    getChannel: function (id) {
        return _.findWhere(this.channels, {id: id});
    },
    /**
     * Returns a list of channels
     *
     * @return {Object[]} list of channels
     */
    getChannels: function () {
        return _.clone(this.channels);
    },
    /**
     * Returns the content that will be shown in the mail navbar dropdown
     *
     * @param  {Object[]} channels
     * @return {$.Promise<Array>} resolved with array of preview msgs
     */
    getChannelsPreview: function (channels) {
        var self = this;
        var channelsPreview = _.map(channels, function (channel) {
            var info;
            if ((channel.channel_ids && _.contains(channel.channel_ids, "channel_inbox")) || channel.id === "mail_failure") {
                // this is a hack to preview messages and mail failure
                // map inbox(mail_message) data with existing channel/chat template
                info = _.pick(channel,
                    'id', 'body', 'avatar_src', 'res_id', 'model', 'module_icon',
                    'subject','date', 'record_name', 'status', 'displayed_author',
                    'email_from', 'unread_counter');
                info.last_message = {
                    body: info.body,
                    date: info.date,
                    displayed_author: info.displayed_author || info.email_from,
                };
                info.name = info.record_name || info.subject || info.displayed_author;
                info.image_src = info.module_icon || info.avatar_src;
                info.message_id = info.id;
                if (channel.id !== "mail_failure") {
                    info.id = 'channel_inbox';
                }
                return info;
            }
            info = _.pick(channel, 'id', 'is_chat', 'name', 'status', 'unread_counter');
            info.last_message = channel.last_message || _.last(channel.cache['[]'].messages);
            if (!info.is_chat) {
                info.image_src = '/web/image/mail.channel/'+channel.id+'/image_small';
            } else if (channel.direct_partner_id) {
                info.image_src = '/web/image/res.partner/'+channel.direct_partner_id+'/image_small';
            } else {
                info.image_src = '/mail/static/src/img/smiley/avatar.jpg';
            }
            return info;
        });
        var missingChannels = _.where(channelsPreview, {last_message: undefined});
        if (!this.channelsPreviewDef) {
            if (missingChannels.length) {
                var missingChannelIDs = _.pluck(missingChannels, 'id');
                this.channelsPreviewDef = this._rpc({
                        model: 'mail.channel',
                        method: 'channel_fetch_preview',
                        args: [missingChannelIDs],
                    }, {
                        shadow: true,
                    });
            } else {
                this.channelsPreviewDef = $.when();
            }
        }
        return this.channelsPreviewDef.then(function (channels) {
            _.each(missingChannels, function (channelPreview) {
                var channel = _.findWhere(channels, {id: channelPreview.id});
                if (channel) {
                    channelPreview.last_message = self._addMessage(channel.last_message);
                }
            });
            // sort channels: 1. unread, 2. chat, 3. date of last msg
            channelsPreview.sort(function (c1, c2) {
                return Math.min(1, c2.unread_counter) - Math.min(1, c1.unread_counter) ||
                       c2.is_chat - c1.is_chat ||
                       !!c2.last_message - !!c1.last_message ||
                       (c2.last_message && c2.last_message.date.diff(c1.last_message.date));
            });

            // generate last message preview (inline message body and compute date to display)
            _.each(channelsPreview, function (channel) {
                if (channel.last_message) {
                    channel.last_message_preview = utils.parse_and_transform(channel.last_message.body, utils.inline);
                    channel.last_message_date = channel.last_message.date.fromNow();
                }
            });
            return channelsPreview;
        });
    },
    /**
     * @return {web.Bus} the chat bus
     */
    getChatBus: function () {
        return this.chatBus;
    },
    /**
     * Show the list of available commands next to a message (e.g. star)
     *
     * @param  {Object} channel
     * @return {Array} list of commands
     */
    getCommands: function (channel) {
        var commands = _.filter(this.commands, function (command) {
            return !command.channel_types || _.contains(command.channel_types, channel.server_type);
        });
        return commands;
    },
    /**
     * Returns the record id of ir.ui.menu for Discuss
     *
     * @return {integer} record id
     */
    getDiscussMenuID: function () {
        return this.discussMenuID;
    },
    /**
     * Gets direct message channel
     *
     * @param  {integer} partnerID
     * @return {Object|undefined} channel
     */
    getDmFromPartnerID: function (partnerID) {
        return _.findWhere(this.channels, {direct_partner_id: partnerID});
    },
    /**
     * Returns list of emojis Objects
     *
     * @return {Object[]} list of emojis
     * ['id', 'source', 'unicode_source', 'substitution', 'description']
     */
    getEmojis: function () {
        return this.emojis;
    },
    /**
     * Get the last seen message for a given channel
     *
     * @param  {Object} channel
     * @return {Object|undefined} last seen Message Object (if any)
     */
    getLastSeenMessage: function (channel) {
        var result;
        if (channel.last_seen_message_id) {
            var messages = channel.cache['[]'].messages;
            var msg = _.findWhere(messages, {id: channel.last_seen_message_id});
            if (msg) {
                var i = _.sortedIndex(messages, msg, 'id') + 1;
                while (i < messages.length &&
                    (messages[i].is_author || messages[i].is_system_notification)) {
                        msg = messages[i];
                        i++;
                }
                result = msg;
            }
        }
        return result;
    },
    /**
     * Returns a list of mail failures
     *
     * @return {Object[]} list of channels
     */
    getMessageFailures: function () {
        return this.messageFailures;
    },
    /**
     * Get all listeners of a channel.
     *
     * @param  {Object} channel
     * @return {$.Promise<Array<Object[]>>|Array<Object[]>} Two cases:
     *
     *      1. 'Channel' provided
     *              => Promise resolved with a list containing a list of members
     *                 (list is cached in channel.membersDeferred)
     *      2. No 'channel' provided
     *              => list containing a list of members (cached by chat_manager)
     */
    getMentionPartnerSuggestions: function (channel) {
        if (!channel) {
            return this.mentionPartnerSuggestions;
        }
        if (!channel.membersDeferred) {
            channel.membersDeferred = this._rpc({
                    model: 'mail.channel',
                    method: 'channel_fetch_listeners',
                    args: [channel.uuid],
                }, {
                    shadow: true
                })
                .then(function (members) {
                    return [members];
                });
        }
        return channel.membersDeferred;
    },
    /**
     * Gets message from its id
     *
     * @param  {integer} msgID
     * @return {Object|undefined} Message Object (if any)
     */
    getMessage: function (msgID) {
        return _.findWhere(this.messages, {id: msgID});
    },
    /**
     * Gets messages from channel or ids or record (model and res_id):
     *
     *      1. From channel if we have 'channelID' in options
     *      2. From ids if we have 'ids' in options
     *      3. From model if we have 'model' and 'res_id' in options
     *
     * Rule of precedence:
     *
     *      'channelID' < 'ids' < 'model' and 'res_id'
     *
     * If we have none of the cases above, we return an empty list.
     *
     * @param  {Object} [options]
     * @param  {integer|string} [options.channelID]
     * @param  {Array} [options.domain]
     * @param  {integer[]} [options.ids]
     * @param  {boolean} [options.loadMore]
     * @param  {string} [options.model]
     * @param  {integer} [options.res_id]
     * @return {$.Promise<Object[]>} list of messages
     */
    getMessages: function (options) {
        var channel;
        var self = this;

        if ('channelID' in options && options.loadMore) {
            // get channel messages, force load more
            channel = this.getChannel(options.channelID);
            return this._fetchFromChannel(channel, {domain: options.domain || {}, loadMore: true});
        }
        if ('channelID' in options) {
            // channel message, check in cache first
            channel = this.getChannel(options.channelID);
            var channelCache = this._getChannelCache(channel, options.domain);
            if (channelCache.loaded) {
                return $.when(channelCache.messages);
            } else {
                return this._fetchFromChannel(channel, {domain: options.domain});
            }
        }
        if ('ids' in options) {
            // get messages from their ids (chatter is the main use case)
            return this._fetchDocumentMessages(options.ids, options).then(function (result) {
                self.markAsRead(options.ids);
                return result;
            });
        }
        if ('model' in options && 'res_id' in options) {
            // get messages for a chatter, when it doesn't know the ids (use
            // case is when using the full composer)
            var domain = [['model', '=', options.model], ['res_id', '=', options.res_id]];
            return this._rpc({
                    model: 'mail.message',
                    method: 'message_fetch',
                    args: [domain],
                    kwargs: {limit: LIMIT},
                })
                .then(function (msgs) {
                    return _.map(msgs, self._addMessage.bind(self));
                });
        }
        return $.when([]);
    },
    /**
     * Returns the number of messages that the user needs to moderate
     *
     * @return {integer}
     */
    getModerationCounter: function () {
        return this.moderationCounter;
    },
    /**
     * Returns the number of messages received from followed channels
     * + all messages where the current user is notified.
     *
     * @return {integer} needaction counter
     */
    getNeedactionCounter: function () {
        return this.needactionCounter;
    },
    /**
     * Gets the number of starred message
     *
     * @return {integer} starred counter
     */
    getStarredCounter: function () {
        return this.starredCounter;
    },
    /**
     * Gets the number of conversation which contains unread messages
     *
     * @return {integer} unread conversation counter
     */
    getUnreadConversationCounter: function () {
        return this.unreadConversationCounter;
    },
    /**
     * States whether all messages have been loaded or not
     *
     * @param  {Object} channel
     * @param  {Array} domain
     * @return {boolean}
     */
    isAllHistoryLoaded: function (channel, domain) {
        return this._getChannelCache(channel, domain).all_history_loaded;
    },
    /**
     * @return {boolean}
     */
    isModerator: function () {
        return this._isModerator;
    },
    /**
     * @return {$.Promise}
     */
    isReady: function () {
        return this._isReady;
    },
    /**
     * join an existing channel
     * See @createChannel to join a new channel
     *
     * @param  {integer} channelID
     * @param  {Object} [options]
     * @return {$.Promise<Object>} resolved with channel object
     */
    joinChannel: function (channelID, options) {
        var self = this;
        if (channelID in this.channelDefs) {
            // prevents concurrent calls to channel_join_and_get_info
            return this.channelDefs[channelID];
        }
        var channel = this.getChannel(channelID);
        if (channel) {
            // channel already joined
            this.channelDefs[channelID] = $.when(channel);
        } else {
            this.channelDefs[channelID] = this._rpc({
                    model: 'mail.channel',
                    method: 'channel_join_and_get_info',
                    args: [[channelID]],
                })
                .then(function (result) {
                    return self._addChannel(result, options);
                });
        }
        return this.channelDefs[channelID];
    },
    /**
     * Marks all messages from a channel as read
     *
     * @param  {Object} channel
     * @param  {Array} domain
     * @return {$.Promise}
     */
    markAllAsRead: function (channel, domain) {
        if ((channel.id === "channel_inbox" && this.needactionCounter) ||
            (channel && channel.needaction_counter)) {
            return this._rpc({
                    model: 'mail.message',
                    method: 'mark_all_as_read',
                    kwargs: {
                        channel_ids: channel.id !== "channel_inbox" ? [channel.id] : [],
                        domain: domain,
                    },
                });
        }
        return $.when();
    },
    /**
     * Mark messages as read
     *
     * @param  {Array} msgIDs list of messages ids
     * @return {$.Promise}
     */
    markAsRead: function (msgIDs) {
        var self = this;
        var ids = _.filter(msgIDs, function (id) {
            var message = _.findWhere(self.messages, {id: id});
            // If too many messages, not all are fetched, and some might not be found
            return !message || message.is_needaction;
        });
        if (ids.length) {
            return this._rpc({
                    model: 'mail.message',
                    method: 'set_message_done',
                    args: [ids],
                });
        } else {
            return $.when();
        }
    },
    /**
     * Marks a channel as seen.
     * The seen message will be the last message.
     * Resolved with the last seen message, only for non-static channels
     *
     * @param  {Object} channel
     * @return {$.Promise<integer|undefined>} last message id seen in the channel
     */
    markChannelAsSeen: function (channel) {
        if (channel.unread_counter > 0 && channel.type !== 'static') {
            this._updateChannelUnreadCounter(channel, 0);
            return this.channelSeen(channel);
        }
        return $.when();
    },
    /**
     * Opens the chat window in discuss.
     *
     * @param  {integer} partnerID
     * @return {$.Promise<Object>} resolved with the dm channel
     */
    openAndDetachDm: function (partnerID) {
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_get_and_minimize',
                args: [[partnerID]],
            })
            .then(this._addChannel.bind(this));
    },
    /**
     * Open the channel:
     *
     *      1. If discuss is opened, asks discuss to open the channel
     *      2. Otherwise, asks the chat_window_manager to detach the channel
     *
     * @param  {Object} channel
     */
    openChannel: function (channel) {
        this.chatBus.trigger(this.discussOpen ? 'open_channel' : 'detach_channel', channel);
    },
    /**
     * Prepares and sends a message to the server:
     *
     *      1. Either the message is posted on a channel
     *      2. Or the message is posted in a model's record (chatter)
     *
     * Rule of precedence:
     *
     *      'channelID' < 'model' & 'res_id'
     *
     * If options as none of these parameters, do nothing and return
     * a promise no resolved item.
     *
     * @param  {Object} data data related to the new message
     * @param  {Object} options
     * @param  {string|integer} [options.channelID]
     * @param  {string} [options.model]
     * @param  {integer} [options.res_id]
     * @return {$.Promise}
     */
    postMessage: function (data, options) {
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

        // Replace emojis by their unicode character
        _.each(emojiUnicodes, function (unicode, key) {
            var escapedKey = String(key).replace(/([.*+?=^!:${}()|[\]/\\])/g, '\\$1');
            var regexp = new RegExp("(\\s|^)(" + escapedKey + ")(?=\\s|$)", "g");
            msg.body = msg.body.replace(regexp, "$1" + unicode);
        });
        if ('subject' in data) {
            msg.subject = data.subject;
        }
        if ('channelID' in options) {
            // post a message in a channel or execute a command
            return this._rpc({
                    model: 'mail.channel',
                    method: data.command ? 'execute_command' : 'message_post',
                    args: [options.channelID],
                    kwargs: _.extend(msg, {
                        message_type: 'comment',
                        subtype: 'mail.mt_comment',
                        command: data.command,
                    }),
                 });
        }
        if ('model' in options && 'res_id' in options) {
            // post a message in a chatter
            _.extend(msg, {
                context: data.context,
                message_type: data.message_type,
                subtype: data.subtype,
                subtype_id: data.subtype_id,
            });

            return this._rpc({
                    model: options.model,
                    method: 'message_post',
                    args: [options.res_id],
                    kwargs: msg,
                })
                .then(function (msgID) {
                    return self._rpc({
                            model: 'mail.message',
                            method: 'message_format',
                            args: [[msgID]],
                        })
                        .then(function (msgs) {
                            msgs[0].model = options.model;
                            msgs[0].res_id = options.res_id;
                            self._addMessage(msgs[0]);
                        });
                });
        }
        return $.when();
    },
    /**
     * Special redirection handling for given model and id
     *
     * If the model is res.partner, and there is a user associated with this
     * partner which isn't the current user, open the DM with this user.
     * Otherwhise, open the record's form view, if this is not the current user's.
     *
     * @param  {string} resModel model to open
     * @param  {integer} resID record to open
     * @param  {function} [dmRedirectionCallback] only used if 'res.partner'
     */
    redirect: function (resModel, resID, dmRedirectionCallback) {
        var self = this;
        var redirectToDocument = function (resModel, resID, viewID) {
            web_client.do_action({
                type:'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: resModel,
                views: [[viewID || false, 'form']],
                res_id: resID,
            });
        };
        if (resModel === 'res.partner') {
            var domain = [['partner_id', '=', resID]];
            this._rpc({
                    model: 'res.users',
                    method: 'search',
                    args: [domain],
                })
                .then(function (userIDs) {
                    if (userIDs.length && userIDs[0] !== session.uid && dmRedirectionCallback) {
                        self.createChannel(resID, 'dm').then(dmRedirectionCallback);
                    } else {
                        redirectToDocument(resModel, resID);
                    }
                });
        } else {
            this._rpc({
                    model: resModel,
                    method: 'get_formview_id',
                    args: [[resID], session.user_context],
                })
                .then(function (viewID) {
                    redirectToDocument(resModel, resID, viewID);
                });
        }
    },
    /**
     * Removes all messages from the current model except 'needaction'.
     * We want to keep it in inbox.
     *
     * @param  {string} model
     */
    removeChatterMessages: function (model) {
        this.messages = _.reject(this.messages, function (message) {
            return (!message.channel_ids || message.channel_ids.length === 0) && message.model === model;
        });
    },
    /**
     * Search among prefetched partners, using the string 'searchVal'
     *
     * @param  {string} searchVal
     * @param  {integer} limit max number of found partners in the response
     * @return {$.Promise<Object[]>} list of found partners (matching 'searchVal')
     */
    searchPartner: function (searchVal, limit) {
        var def = $.Deferred();
        var values = [];
        // search among prefetched partners
        var searchRegexp = new RegExp(_.str.escapeRegExp(utils.unaccent(searchVal)), 'i');
        _.each(this.mentionPartnerSuggestions, function (partners) {
            if (values.length < limit) {
                values = values.concat(_.filter(partners, function (partner) {
                    return session.partner_id !== partner.id && searchRegexp.test(partner.name);
                })).splice(0, limit);
            }
        });
        if (!values.length) {
            // extend the research to all users
            def = this._rpc({
                    model: 'res.partner',
                    method: 'im_search',
                    args: [searchVal, limit || 20],
                }, {
                    shadow: true,
                });
        } else {
            def = $.when(values);
        }
        return def.then(function (values) {
            var autocompleteData = _.map(values, function (value) {
                return { id: value.id, value: value.name, label: value.name };
            });
            return _.sortBy(autocompleteData, 'label');
        });
    },
    /**
     * Stars or unstars message
     *
     * @param  {integer} msgID
     * @return {$.Promise}
     */
    toggleStarStatus: function (msgID) {
        return this._rpc({
                model: 'mail.message',
                method: 'toggle_message_starred',
                args: [[msgID]],
            });
    },
    /**
     * Unstars all messages from all channels
     *
     * @return {$.Promise}
     */
    unstarAll: function () {
        return this._rpc({
                model: 'mail.message',
                method: 'unstar_all',
                args: [[]]
            });
    },
    /**
     * Unsubscribes from channel
     *
     * @param  {Object} channel
     * @param  {integer|string} [channel.id] mandatory if channel is of type 'public' or 'private'
     * @param  {string} [channel.type]
     * @param  {string} [channel.uuid] mandatory if channel is not of type 'public' or 'private'
     * @return {$.Promise}
     */
    unsubscribe: function (channel) {
        if (_.contains(['public', 'private'], channel.type)) {
            return this._rpc({
                    model: 'mail.channel',
                    method: 'action_unfollow',
                    args: [[channel.id]],
                });
        } else {
            return this._rpc({
                    model: 'mail.channel',
                    method: 'channel_pin',
                    args: [channel.uuid, false],
                });
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a channel and returns it.
     * Simply returns the channel if already exists.
     *
     * @private
     * @param  {Object} data
     * @param  {string|integer} data.id id of channel or 'channel_inbox', 'channel_starred', ...
     * @param  {string|Object} data.name name of channel, e.g. 'general'
     * @param  {string} data.type type of channel, e.g. 'static'
     * @param  {string} [data.state] e.g. 'open', 'folded'
     * @param  {Object|integer} [options=undefined]
     * @param  {boolean} [options.silent]
     * @return {Object} the newly or already existing channel
     */
    _addChannel: function (data, options) {
        options = typeof options === "object" ? options : {};
        var channel = this.getChannel(data.id);
        if (channel) {
            if (channel.is_folded !== (data.state === "folded")) {
                channel.is_folded = (data.state === "folded");
                this.call('chat_window_manager', 'toggleFoldChat', channel);
            }
        } else {
            channel = this._makeChannel(data, options);
            this.channels.push(channel);
            if (data.last_message) {
                channel.last_message = this._addMessage(data.last_message);
            }
            // In case of a static channel (Inbox, Starred), the name is translated thanks to _lt
            // (lazy translate). In this case, channel.name is an object, not a string.
            this.channels = _.sortBy(this.channels, function (channel) {
                return _.isString(channel.name) ? channel.name.toLowerCase() : '';
            });
            if (!options.silent) {
                this.chatBus.trigger("new_channel", channel);
            }
            if (channel.is_detached) {
                this.call('chat_window_manager', 'openChat', channel);
            }
        }
        return channel;
    },
    /**
     * Adds a channel to a message
     * Usefull when you mark a message as 'to do'.
     * The message will be available in 'Starred' channel.
     *
     * @private
     * @param  {Object} message
     * @param  {string} channelID
     */
    _addChannelToMessage: function (message, channelID) {
        if (!message.channel_ids) {
            message.channel_ids = [];
        }
        message.channel_ids.push(channelID);
        message.channel_ids = _.uniq(message.channel_ids);
    },
    /**
     * Creates a new message
     *
     * @private
     * @param  {Object} data message data
     * @param  {integer} data.id
     * @param  {Object} [options]
     * @param  {Array} [options.domain]
     * @param  {boolean} [options.increment_unread] whether we should increment
     *      the unread_counter of channel.
     * @param  {boolean} [options.silent] whether it should inform in the chatBus
     *      of the newly created message.
     * @return {Object} message object
     */
    _addMessage: function (data, options) {
        var self = this;
        options = options || {};
        var msg = _.findWhere(this.messages, { id: data.id });

        if (!msg) {
            msg = this._makeMessage(data);
            // Keep the array ordered by id when inserting the new message
            this.messages.splice(_.sortedIndex(this.messages, msg, 'id'), 0, msg);
            _.each(msg.channel_ids, function (channelID) {
                var channel = self.getChannel(channelID);
                if (channel) {
                    // update the channel's last message (displayed in the channel
                    // preview, in mobile)
                    if (!channel.last_message || msg.id > channel.last_message.id) {
                        channel.last_message = msg;
                    }
                    self._addToCache(msg, []);
                    if (options.domain && options.domain !== []) {
                        self._addToCache(msg, options.domain);
                    }
                    if (channel.hidden) {
                        channel.hidden = false;
                        self.chatBus.trigger('new_channel', channel);
                    }
                    if (channel.type !== 'static' && !msg.is_author && !msg.is_system_notification) {
                        if (options.increment_unread) {
                            self._updateChannelUnreadCounter(channel, channel.unread_counter+1);
                        }
                        if (channel.is_chat && options.show_notification) {
                            if (!self.discussOpen && !config.device.isMobile) {
                                // automatically open chat window
                                self.call('chat_window_manager', 'openChat', channel, { passively: true });
                            }
                            var query = {is_displayed: false};
                            self.chatBus.trigger('anyone_listening', channel, query);
                            self._notifyIncomingMessage(msg, query);
                        }
                    }
                }
            });
            if (!options.silent) {
                this.chatBus.trigger('new_message', msg);
            }
        } else if (options.domain && options.domain !== []) {
            this._addToCache(msg, options.domain);
        } else if (data.moderation_status === 'accepted') {
            msg.channel_ids = _.uniq(data.channel_ids.concat(msg.channel_ids));
            msg.needsModeration = false;
            if (msg.isModerator) {
                this.moderationCounter--;
                this._removeMessageFromChannel("channel_moderation", msg);
                this.chatBus.trigger('update_moderation_counter');
            }
            this.chatBus.trigger('update_message', msg);
        }
        return msg;
    },
    /**
     * Stores message to channelCache.
     *
     * @private
     * @param  {Object} message
     * @param  {Array} domain
     */
    _addToCache: function (message, domain) {
        var self = this;
        _.each(message.channel_ids, function (channelID) {
            var channel = self.getChannel(channelID);
            if (channel) {
                var channelCache = self._getChannelCache(channel, domain);
                var index = _.sortedIndex(channelCache.messages, message, 'id');
                if (channelCache.messages[index] !== message) {
                    channelCache.messages.splice(index, 0, message);
                }
            }
        });
    },
    /**
     * Gets messages from their ids
     * This method is used when the chatter linked to a record need to be loaded.
     *
     * @private
     * @param  {Array} msgIDs message ids to load
     * @param  {Object} options
     * @return {$.Promise<Object[]>} resolved with fetched messages
     */
    _fetchDocumentMessages : function (msgIDs, options) {
        var self = this;
        var loadedMsgs = _.filter(this.messages, function (message) {
            return _.contains(msgIDs, message.id);
        });
        var loadedMsgIDs = _.pluck(loadedMsgs, 'id');

        options = options || {};
        if (options.forceFetch || _.difference(msgIDs.slice(0, LIMIT), loadedMsgIDs).length) {
            var idsToLoad = _.difference(msgIDs, loadedMsgIDs).slice(0, LIMIT);
            return this._rpc({
                    model: 'mail.message',
                    method: 'message_format',
                    args: [idsToLoad],
                    context: session.user_context,
                })
                .then(function (msgs) {
                    var processedMsgs = [];
                    _.each(msgs, function (msg) {
                        processedMsgs.push(self._addMessage(msg, {silent: true}));
                    });
                    return _.sortBy(loadedMsgs.concat(processedMsgs), function (msg) {
                        return msg.id;
                    });
                });
        } else {
            return $.when(loadedMsgs);
        }
    },
    /**
     * Gets messages from channel
     *
     * @private
     * @param  {Object} channel
     * @param  {integer|string} channel.id string for static channels, e.g. 'channel_inbox'
     * @param  {Object} [option={}]
     * @param  {Array} [options.domain] filter on the messages of the channel
     * @param  {boolean} [options.loadMore] Whether it should load more message
     * @return {$.Promise<Object[]>} resolved with list of messages
     */
    _fetchFromChannel: function (channel, options) {
        var self = this;
        options = options || {};
        var domain =
            (channel.id === 'channel_inbox') ? [['needaction', '=', true]] :
            (channel.id === 'channel_starred') ? [['starred', '=', true]] :
            (channel.id === 'channel_moderation') ? [['need_moderation', '=', true]] :
                                                    ['|',
                                                     '&', '&',
                                                     ['model', '=', 'mail.channel'],
                                                     ['res_id', 'in', [channel.id]],
                                                     ['need_moderation', '=', true],
                                                     ['channel_ids', 'in', [channel.id]]
                                                    ];
        var cache = this._getChannelCache(channel, options.domain);

        if (options.domain) {
            domain = domain.concat(options.domain || []);
        }
        if (options.loadMore) {
            var minMessageID = cache.messages[0].id;
            domain = [['id', '<', minMessageID]].concat(domain);
        }

        return this._rpc({
                model: 'mail.message',
                method: 'message_fetch',
                args: [domain],
                kwargs: {limit: LIMIT, context: session.user_context},
            })
            .then(function (msgs) {
                if (!cache.all_history_loaded) {
                    cache.all_history_loaded =  msgs.length < LIMIT;
                }
                cache.loaded = true;

                _.each(msgs, function (msg) {
                    self._addMessage(msg, {
                        channel_id: channel.id,
                        silent: true,
                        domain: options.domain,
                    });
                });
                var channelCache = self._getChannelCache(channel, options.domain || []);
                return channelCache.messages;
            });
    },
    /**
     * Gets channel content from the cache.
     * Usefull to get cached messages from a channel.
     *
     * @private
     * @param  {Object} channel
     * @param  {Object[]} channel.cache
     * @param  {Array} domain
     * @return {Object|undefined}
     */
    _getChannelCache: function (channel, domain) {
        var stringifiedDomain = JSON.stringify(domain || []);
        if (!channel.cache[stringifiedDomain]) {
            channel.cache[stringifiedDomain] = {
                all_history_loaded: false,
                loaded: false,
                messages: [],
            };
        }
        return channel.cache[stringifiedDomain];
    },
    /**
     * @private
     * @returns {$.Promise}
     */
    _initMessaging: function () {
        var self = this;
        return session.is_bound.then(function (){
            var context = _.extend({isMobile: config.device.isMobile}, session.user_context);
            return self._rpc({
                route: '/mail/init_messaging',
                params: {context: context},
            });
        }).then(function (result) {
            _.each(result.channel_slots, function (channels) {
                _.each(channels, self._addChannel.bind(self));
            });
            self.messageFailures = result.mail_failures;
            self.needactionCounter = result.needaction_inbox_counter || 0;
            self.starredCounter = result.starred_counter || 0;
            self.moderationCounter = result.moderation_counter;
            self.moderatedChannelIDs = result.moderation_channel_ids;
            self._isModerator = result.is_moderator;

            //if user is moderator then add moderation channel
            if (self._isModerator) {
                self._addChannel({
                    id: "channel_moderation",
                    name: _lt("Moderate Messages"),
                    type: "static"
                });
            }
            self.commands = _.map(result.commands, function (command) {
                return _.extend({ id: command.name }, command);
            });
            self.mentionPartnerSuggestions = result.mention_partner_suggestions;
            self.discussMenuID = result.menu_id;

            // Shortcodes: canned responses
            _.each(result.shortcodes, function (s) {
                self.cannedResponses.push(_.pick(s, ['id', 'source', 'substitution']));
            });
            // emojis

            var lastAdded = null;
            _.each(emojiUnicodes, function (unicode, key) {
                if (lastAdded != unicode){
                    lastAdded = unicode;
                    self.emojis.push({source:key, unicode_source:unicode, description:key});
                }
            });

            self.busBus.start_polling();
        });
    },
    /**
     * Clear cache of a channel
     *
     * @private
     * @param  {Array} channelIDs must be int or string
     */
    _invalidateCaches: function (channelIDs) {
        var self = this;
        _.each(channelIDs, function (channelID) {
            var channel = self.getChannel(channelID);
            if (channel) {
                channel.cache = { '[]': channel.cache['[]']};
            }
        });
    },
    /**
     * Creates channel object
     *
     * @private
     * @param  {Object} data
     * @param  {string} [data.anonymous_name]
     * @param  {string} data.channel_type
     * @param  {Object[]} [data.direct_partner]
     * @param  {boolean} [data.group_based_subscription]
     * @param  {integer|string} data.id
     * @param  {boolean} data.is_moderator
     * @param  {boolean} data.is_minimized
     * @param  {string} [data.last_message_date]
     * @param  {boolean} data.mass_mailing
     * @param  {integer} [data.message_needaction_counter]
     * @param  {integer} [data.message_unread_counter]
     * @param  {boolean} data.moderation whether this channel is moderated or not
     * @param  {string} data.name
     * @param  {string} [data.public]
     * @param  {integer} data.seen_message_id
     * @param  {string} [data.state]
     * @param  {string} [data.type]
     * @param  {string} data.uuid
     * @param  {Object} options
     * @param  {boolean} [options.autoswitch]
     * @param  {boolean} options.displayNeedactions
     * @param  {boolean} [options.hidden]
     * @return {Object} channel
     */
    _makeChannel: function (data, options) {
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
            display_needactions: options.displayNeedactions,
            mass_mailing: data.mass_mailing,
            isModerated: data.moderation,
            isModerator: data.is_moderator,
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
            this.pinnedDmPartners.push(channel.direct_partner_id);
            this.busBus.update_option('bus_presence_partner_ids', this.pinnedDmPartners);
        } else if ('anonymous_name' in data) {
            channel.name = data.anonymous_name;
        }
        if (data.last_message_date) {
            channel.last_message_date = moment(time.str_to_datetime(data.last_message_date));
        }
        channel.is_chat = !channel.type.match(/^(public|private|static)$/);
        if (data.message_unread_counter) {
            this._updateChannelUnreadCounter(channel, data.message_unread_counter);
        }
        return channel;
    },
    /**
     * Creates message object
     *
     * @private
     * @param  {Object} data
     * @param  {integer[]} [data.attachment_ids=[]]
     * @param  {integer[]} [data.author_id]
     * @param  {string} [data.body=""]
     * @param  {Array} data.channel_ids contains integers and strings
     * @param  {string} data.customer_email_status
     * @param  {string} data.date
     * @param  {string} data.email_from
     * @param  {integer} data.id
     * @param  {string} [data.info]
     * @param  {boolean} data.is_discussion
     * @param  {boolean} data.is_note
     * @param  {boolean} data.is_notification
     * @param  {string} data.message_type
     * @param  {string} [data.moderation_status]
     * @param  {string} [data.model]
     * @param  {boolean} data.module_icon src url of the module icon
     * @param  {string} data.record_name
     * @param  {integer} data.res_id
     * @param  {string} data.subject
     * @param  {string} data.subtype_description
     * @param  {integer[]} data.tracking_value_ids
     * @return {Object} message
     */
    _makeMessage: function (data) {
        var self = this;
        var msg = {
            id: data.id,
            author_id: data.author_id,
            body: data.body || "",
            date: moment(time.str_to_datetime(data.date)),
            message_type: data.message_type,
            subtype_description: data.subtype_description,
            is_author: data.author_id && data.author_id[0] === session.partner_id,
            isModerator: data.model === 'mail.channel' &&
                _.contains(this.moderatedChannelIDs, data.res_id) &&
                data.moderation_status === 'pending_moderation',
            is_note: data.is_note,
            is_discussion: data.is_discussion,
            is_notification: data.is_notification,
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
            module_icon:data.module_icon,
        };
        _.each(emojiUnicodes, function (value, key) {
            //add o_mail_emoji class on each unicode to manage size and font
            var unicode = String(value);
            var regexp = new RegExp("(?:^|\\s|<[a-z]*>)(" + unicode + ")(?=\\s|$|</[a-z]*>)", "g");
            var msg_bak = msg.body;
            msg.body = msg.body.replace(regexp, ' <span class="o_mail_emoji">'+unicode+'</span> ');
            // Idiot-proof limit. If the user had the amazing idea of copy-pasting thousands of emojis,
            // the image rendering can lead to memory overflow errors on some browsers (e.g. Chrome).
            // Set an arbitrary limit to 200 from which we simply don't replace them (anyway, they are
            // already replaced by the unicode counterpart).
            if (_.str.count(msg.body, 'o_mail_emoji') > 200) {
                msg.body = msg_bak;
            }
        });
        function propertyDescr(channel) {
            return {
                enumerable: true,
                get: function () {
                    return _.contains(msg.channel_ids, channel);
                },
                set: function (bool) {
                    if (bool) {
                        self._addChannelToMessage(msg, channel);
                    } else {
                        msg.channel_ids = _.without(msg.channel_ids, channel);
                    }
                }
            };
        }

        Object.defineProperties(msg, {
            is_starred: propertyDescr("channel_starred"),
            is_needaction: propertyDescr("channel_inbox"),
            needsModerationByUser: propertyDescr("channel_moderation"),
        });

        if (_.contains(data.needaction_partner_ids, session.partner_id)) {
            msg.is_needaction = true;
        }
        if (_.contains(data.starred_partner_ids, session.partner_id)) {
            msg.is_starred = true;
        }
        if (data.moderation_status === 'pending_moderation') {
            msg.needsModeration = true;
            msg.needsModerationByUser = msg.isModerator;
            // the message is not linked to the moderated channel on the
            // server, therefore this message has not this channel in
            // channel_ids. Here, just to show this message in the channel
            //visually, it links this message to the channel
            msg.channel_ids.push(msg.res_id);
        }
        if (msg.model === 'mail.channel') {
            var realChannels = _.without(msg.channel_ids, 'channel_inbox', 'channel_starred', 'channel_moderation');
            var origin = realChannels.length === 1 ? realChannels[0] : undefined;
            var channel = origin && this.getChannel(origin);
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
        _.each(msg.attachment_ids, function (a) {
            a.url = '/web/content/' + a.id + '?download=true';
        });

        // format date to the local only once by message
        // can not be done in preprocess, since it alter the original value
        if (msg.tracking_value_ids && msg.tracking_value_ids.length) {
            var format;
            _.each(msg.tracking_value_ids, function (f) {
                if (f.field_type === 'datetime') {
                    format = 'LLL';
                    if (f.old_value) {
                        f.old_value = moment.utc(f.old_value).local().format(format);
                    }
                    if (f.new_value) {
                        f.new_value = moment.utc(f.new_value).local().format(format);
                    }
                } else if (f.field_type === 'date') {
                    format = 'LL';
                    if (f.old_value) {
                        f.old_value = moment(f.old_value).local().format(format);
                    }
                    if (f.new_value) {
                        f.new_value = moment(f.new_value).local().format(format);
                    }
                }
            });
        }

        return msg;
    },
    /**
     * @private
     * @param  {Object} data key, value to decide activity created or deleted
     */
    _manageActivityUpdateNotification: function (data) {
        this.chatBus.trigger('activity_updated', data);
    },
    /**
     * @private
     * @param {Object} data
     */
    _manageAuthorNotification: function (data) {
        this._addMessage(data.message);
    },
    /**
     * @private
     * @param  {Object} message
     * @param  {Array} message.channel_ids list of integers and strings,
     *      where strings for static channels, e.g. 'channel_inbox'.
     */
    _manageChannelNotification: function (message) {
        var self = this;
        var def;
        var channelAlreadyInCache = true;
        if (message.channel_ids.length === 1) {
            channelAlreadyInCache = !!this.getChannel(message.channel_ids[0]);
            def = this.joinChannel(message.channel_ids[0], {autoswitch: false});
        } else {
            def = $.when();
        }
        def.then(function () {
            // don't increment unread if channel wasn't in cache yet as
            // its unread counter has just been fetched
            self._addMessage(message, {
                show_notification: true,
                increment_unread: channelAlreadyInCache
            });
            self._invalidateCaches(message.channel_ids);
        });
    },
    /**
     * @private
     * @param  {Object} data
     * @param  {integer|string} data.id string for static channels, e.g. 'channel_inbox'
     * @param  {integer} [data.last_message_id] mandatory if 'id' refers to an
     *      existing channel.
     */
    _manageChannelSeenNotification: function (data) {
        var channel = this.getChannel(data.id);
        if (channel) {
            channel.last_seen_message_id = data.last_message_id;
            if (channel.unread_counter) {
                this._updateChannelUnreadCounter(channel, 0);
            }
        }
    },
    /**
     * Controls the session of the chat window
     *
     * @private
     * @param  {Object} chatSession
     * @param  {string} chatSession.channel_type
     * @param  {string|integer} chatSession.id string for static channels, e.g. 'channel_inbox'
     * @param  {string} chatSession.info
     * @param  {boolean} chatSession.is_minimized
     * @param  {string} chatSession.name
     * @param  {string} chatSession.state
     */
    _manageChatSessionNotification: function (chatSession) {
        var channel;
        if ((chatSession.channel_type === "channel") && (chatSession.state === "open")) {
            this._addChannel(chatSession, {autoswitch: false});
            if (!chatSession.is_minimized && chatSession.info !== 'creation') {
                web_client.do_notify(_t("Invitation"), _t("You have been invited to: ") + chatSession.name);
            }
        }
        // partner specific change (open a detached window for example)
        if ((chatSession.state === "open") || (chatSession.state === "folded")) {
            channel = chatSession.is_minimized && this.getChannel(chatSession.id);
            if (channel) {
                channel.is_detached = true;
                channel.is_folded = (chatSession.state === "folded");
                this.call('chat_window_manager', 'openChat', channel);
            }
        } else if (chatSession.state === "closed") {
            channel = this.getChannel(chatSession.id);
            if (channel) {
                channel.is_detached = false;
                this.call('chat_window_manager', 'closeChat', channel, {keep_open_if_unread: true});
            }
        }
    },
    /**
     * @private
     * @param {Object} data
     * @param {Object[]} [data.message_ids]
     */
    _manageDeletionNotification: function (data) {
        var self = this;
        _.each(data.message_ids, function (msgID) {
            var message = _.findWhere(self.messages, { id: msgID });
            if (message) {
                if (message.isModerator) {
                    self._removeMessageFromChannel("channel_moderation", message);
                    self.moderationCounter--;
                }
                message.needsModeration = false;
                self._removeMessageFromChannel(message.res_id, message);
                self.chatBus.trigger('update_message', message);
                }
            });
        this.chatBus.trigger('update_moderation_counter');
    },
    /**
     * Add or remove failure when receiving a failure update message
     * @private
     * @param  {Object} data
     */
    _manageMessageFailureNotification: function (data) {
        var self = this;
        _.each(data.elements, function (updateMessage) {

            var isAddFailure = _.some(updateMessage.notifications, function(notif) {
                return notif[0] === 'exception' || notif[0] === 'bounce';
            });
            var res = _.find(self.messageFailures, {'message_id': updateMessage.message_id});
            if (res) {
                var index = _.findIndex(self.messageFailures, res);
                if (isAddFailure) {
                    self.messageFailures[index] = updateMessage;
                } else {
                    self.messageFailures.splice(index, 1);
                }
            } else if (isAddFailure) {
                self.messageFailures.push(updateMessage);
            } 
            var message = _.findWhere(self.messages, { id: updateMessage.message_id });
            if (message) {
                if (isAddFailure) {
                    message.customer_email_status = "exception";
                } else{
                    message.customer_email_status = "sent";
                }
                self._updateMessageNotificationStatus(updateMessage, message);
                self.chatBus.trigger('update_message', message);
            }
        });
        this.chatBus.trigger('update_needaction', this.needactionCounter);
    },
    /**
     * Updates channel_inbox when a message has marked as read.
     *
     * @private
     * @param  {Object} data
     * @param  {integer[]} [data.channel_ids]
     * @param  {integer[]} [data.message_ids]
     * @param  {string} [data.type]
     */
    _manageMarkAsReadNotification: function (data) {
        var self = this;
        _.each(data.message_ids, function (msgID) {
            var message = _.findWhere(self.messages, { id: msgID });
            if (message) {
                self._invalidateCaches(message.channel_ids);
                self._removeMessageFromChannel("channel_inbox", message);
                self.chatBus.trigger('update_message', message, data.type);
            }
        });
        if (data.channel_ids) {
            _.each(data.channel_ids, function (channelID) {
                var channel = self.getChannel(channelID);
                if (channel) {
                    channel.needaction_counter = Math.max(channel.needaction_counter - data.message_ids.length, 0);
                }
            });
        } else { // if no channel_ids specified, this is a 'mark all read' in the inbox
            _.each(this.channels, function (channel) {
                channel.needaction_counter = 0;
            });
        }
        this.needactionCounter = Math.max(this.needactionCounter - data.message_ids.length, 0);
        this.chatBus.trigger('update_needaction', this.needactionCounter);
    },
    /**
     * @private
     * @param {Object} data notification data
     * @param {Object} data.message
     */
    _manageModeratorNotification: function (data) {
        this.moderationCounter++;
        this._addMessage(data.message);
        this.chatBus.trigger('update_moderation_counter');
    },
    /**
     * @private
     * @param  {Object} message
     * @param  {integer[]} message.channel_ids
     */
    _manageNeedactionNotification: function (message) {
        var self = this;
        message = this._addMessage(message, {
            channel_id: 'channel_inbox',
            increment_unread: true,
            show_notification: true,
        });
        this._invalidateCaches(message.channel_ids);
        if (message.channel_ids.length !== 0) {
            this.needactionCounter++;
        }
        _.each(message.channel_ids, function (channelID) {
            var channel = self.getChannel(channelID);
            if (channel) {
                channel.needaction_counter++;
            }
        });
        this.chatBus.trigger('update_needaction', this.needactionCounter);
    },
    /**
     * @private
     * @param  {Object} data structure depending on the type
     * @param  {integer} data.id
     */
    _managePartnerNotification: function (data) {
        if (data.info === "unsubscribe") {
            var channel = this.getChannel(data.id);
            if (channel) {
                var msg;
                if (_.contains(['public', 'private'], channel.type)) {
                    msg = _.str.sprintf(_t('You unsubscribed from <b>%s</b>.'), channel.name);
                } else {
                    msg = _.str.sprintf(_t('You unpinned your conversation with <b>%s</b>.'), channel.name);
                }
                this._removeChannel(channel);
                this.chatBus.trigger("unsubscribe_from_channel", data.id);
                web_client.do_notify(_t("Unsubscribed"), msg);
            }
        } else if (data.type === 'toggle_star') {
            this._manageToggleStarNotification(data);
        } else if (data.type === 'mark_as_read') {
            this._manageMarkAsReadNotification(data);
        } else if (data.type === 'moderator') {
            this._manageModeratorNotification(data);
        } else if (data.type === 'author') {
            this._manageAuthorNotification(data);
        } else if (data.type === 'deletion') {
            this._manageDeletionNotification(data);
        } else if (data.info === 'channel_seen') {
            this._manageChannelSeenNotification(data);
        } else if (data.info === 'transient_message') {
            this._manageTransientMessageNotification(data);
        } else if (data.type === 'activity_updated') {
            this._manageActivityUpdateNotification(data);
        } else if (data.type === 'mail_failure') {
            this._manageMessageFailureNotification(data);
        } else {
            this._manageChatSessionNotification(data);
        }
    },
    /**
     * @private
     * @param  {Object} data partner infos
     * @param  {integer} data.id
     * @param  {string} data.im_status
     */
    _managePresenceNotification: function (data) {
        var dm = this.getDmFromPartnerID(data.id);
        if (dm) {
            dm.status = data.im_status;
            this.chatBus.trigger('update_dm_presence', dm);
        }
    },
    /**
     * @private
     * @param  {Object} data
     * @param  {integer[]} data.message_ids
     * @param  {boolean} data.starred
     * @param  {string} data.type
     */
    _manageToggleStarNotification: function (data) {
        var self = this;
        _.each(data.message_ids, function (msgID) {
            var message = _.findWhere(self.messages, { id: msgID });
            if (message) {
                self._invalidateCaches(message.channel_ids);
                message.is_starred = data.starred;
                if (!message.is_starred) {
                    self._removeMessageFromChannel("channel_starred", message);
                } else {
                    self._addToCache(message, []);
                    var channelStarred = self.getChannel('channel_starred');
                    channelStarred.cache = _.pick(channelStarred.cache, "[]");
                }
                self.chatBus.trigger('update_message', message);
            }
        });

        if (data.starred) { // increase starred counter if message is marked as star
            this.starredCounter += data.message_ids.length;
        } else { // decrease starred counter if message is remove from star if unstar_all then it will set to 0.
            this.starredCounter -= data.message_ids.length;
        }

        this.chatBus.trigger('update_starred', this.starredCounter);
    },
    /**
     * @private
     * @param  {Object} data
     * @param  {string} data.author_id
     */
    _manageTransientMessageNotification: function (data) {
        var lastMessage = _.last(this.messages);
        data.id = (lastMessage ? lastMessage.id : 0) + 0.01;
        data.author_id = data.author_id || ODOOBOT_ID;
        this._addMessage(data);
    },
    /**
     * shows a popup to notify a new received message.
     * This will also rename the odoo tab browser if
     * the user is not in it.
     *
     * @private
     * @param  {Object} msg message received
     * @param  {Array} msg.author_id contains [integer, string]
     * @param  {string} msg.body
     * @param  {Object} options
     * @param  {boolean} options.is_displayed
     */
    _notifyIncomingMessage: function (msg, options) {
        if (this.busBus.is_odoo_focused() && options.is_displayed) {
            // no need to notify
            return;
        }
        var title = _t('New message');
        if (msg.author_id[1]) {
            title = _.escape(msg.author_id[1]);
        }
        var content = utils.parse_and_transform(msg.body, utils.strip_html)
            .substr(0, PREVIEW_MSG_MAX_SIZE);

        if (!this.busBus.is_odoo_focused()) {
            this.globalUnreadCounter++;
            var tabTitle = _.str.sprintf(_t("%d Messages"), this.globalUnreadCounter);
            web_client.set_title_part("_chat", tabTitle);
        }

        this.call('bus_service', 'sendNotification', web_client, title, content);
    },
    /**
     * Removes channel
     *
     * @private
     * @param  {Object} [channel]
     * @param  {integer} [channel.direct_partner_id] mandatory if type is 'dm'
     * @param  {integer|string} channel.id string for static channels, e.g. 'channel_inbox'
     * @param  {string} [channel.type]
     */
    _removeChannel: function (channel) {
        if (!channel) { return; }
        if (channel.type === 'dm') {
            var index = this.pinnedDmPartners.indexOf(channel.direct_partner_id);
            if (index > -1) {
                this.pinnedDmPartners.splice(index, 1);
                this.busBus.update_option('bus_presence_partner_ids', this.pinnedDmPartners);
            }
        }
        this.channels = _.without(this.channels, channel);
        delete this.channelDefs[channel.id];
    },
    /**
     * Removes a message from a channel.
     * it will also remove cached message from the channel
     *
     * @private
     * @param  {integer|string} channelID string for static channels, e.g. 'channel_inbox'
     * @param  {Object} message
     */
    _removeMessageFromChannel: function (channelID, message) {
        message.channel_ids = _.without(message.channel_ids, channelID);
        var channel = _.findWhere(this.channels, { id: channelID });
        _.each(channel.cache, function (cache) {
            cache.messages = _.without(cache.messages, message);
        });
    },
    /**
     * Increments or decrements unreadConversationCounter
     *
     * @private
     * @param  {Object} channel
     * @param  {integer} counter
     */
    _updateChannelUnreadCounter: function (channel, counter) {
        if (channel.unread_counter > 0 && counter === 0) {
            this.unreadConversationCounter = Math.max(0, this.unreadConversationCounter-1);
        } else if (channel.unread_counter === 0 && counter > 0) {
            this.unreadConversationCounter++;
        }
        channel.unread_counter = counter;
        this.chatBus.trigger("update_channel_unread_counter", channel);
    },
    /**
     * Update the message notification status of message based on update_message
     *
     * @private
     * @param {Object} updateMessage
     * @param {Object[]} updateMessage.notifications
     */
    _updateMessageNotificationStatus: function (updateMessage, message) {
        _.each(updateMessage.notifications, function (notif, id, list) {
            var partnerName = notif[1];
            var notifStatus = notif[0];
            var res = _.find(message.customer_email_data, function(entry){ 
                return entry[0] === parseInt(id);
            });
            if (res) {
                res[2] = notifStatus;
            } else {
                message.customer_email_data.push([parseInt(id), partnerName, notifStatus]);
            }
        });
    },
    
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Notification handlers
     * Sometimes, the web client receives unsubscribe notification and an extra
     * notification on that channel.  This is then followed by an attempt to
     * rejoin the channel that we just left.  The next few lines remove the
     * extra notification to prevent that situation to occur.
     *
     * @private
     * @param  {Array} notifications
     */
    _onNotification: function (notifications) {
        var self = this;
        var unsubscribedNotif = _.find(notifications, function (notif) {
            return notif[1].info === "unsubscribe";
        });
        if (unsubscribedNotif) {
            notifications = _.reject(notifications, function (notif) {
                return notif[0][1] === "mail.channel" && notif[0][2] === unsubscribedNotif[1].id;
            });
        }
        _.each(notifications, function (notification) {
            var model = notification[0][1];
            if (model === 'ir.needaction') {
                // new message in the inbox
                self._manageNeedactionNotification(notification[1]);
            } else if (model === 'mail.channel') {
                // new message in a channel
                self._manageChannelNotification(notification[1]);
            } else if (model === 'res.partner') {
                // channel joined/left, message marked as read/(un)starred, chat open/closed
                self._managePartnerNotification(notification[1]);
            } else if (model === 'bus.presence') {
                // update presence of users
                self._managePresenceNotification(notification[1]);
            }
        });
    },
    /**
     * Global unread counter and notifications
     *
     * @private
     */
    _onWindowFocus: function () {
        this.globalUnreadCounter = 0;
        web_client.set_title_part("_chat");
    },

});

core.serviceRegistry.add('chat_manager', ChatManager);

return ChatManager;

});
