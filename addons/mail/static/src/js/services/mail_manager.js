odoo.define('mail.Manager', function (require) {
"use strict";

/**
 * This service is responsible for anything related to mail in JS.
 * In particular, it stores all threads and messages that have been fetched
 * from the server.
 *
 * As this service does quite a lot of stuffs, it is split into many different
 * files. For instance, the handling of notification in the longpoll is in
 * mail_notification_manager.js. This file contains the core functionnality
 * of the mail service.
 *
 * The main point of entry of this service is to call public methods by mean
 * of a service call.
 *
 * @example
 *
 * To get all threads that have been fetched from the server:
 *
 *      this.call('mail_service', 'getThreads');
 *
 * To get a particular thread with server ID 1:
 *
 *      this.call('mail_service', 'getThread', 1);
 */
var AbstractService = require('web.AbstractService');

var DMChat = require('mail.model.DMChat');
var Livechat = require('mail.model.Livechat');
var Mailbox = require('mail.model.Mailbox');
var MailFailure = require('mail.model.MailFailure');
var Message = require('mail.model.Message');
var MultiUserChannel = require('mail.model.MultiUserChannel');
var mailUtils = require('mail.utils');
var utils = require('web.utils');

var Bus = require('web.Bus');
var config = require('web.config');
var core = require('web.core');
var session = require('web.session');

var _t = core._t;

var PREVIEW_MSG_MAX_SIZE = 350;  // optimal for native english speakers

var MailManager =  AbstractService.extend({
    dependencies: ['ajax', 'bus_service', 'local_storage'],
    _isReady: false,
    _ODOOBOT_ID: ["ODOOBOT", "ODOOBOT"], // authorID for transient messages

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);

        this._throttleNotifyChannelFetched = _.throttle(this._notifyChannelFetched.bind(this), 3000);
        // List of channel that have requested the service to notify when
        // it has been fetched, so that throttled RPCs batch the ids.
        this._toNotifyChannelFetchedIDs = [];

        this._initializeInternalState();
        this._listenOnBuses();
        this._fetchMailStateFromServer();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a message
     *
     * @param {Object} data message data
     * @param {integer} data.id
     * @param {string} [data.moderation_status]
     * @param {Object} [options]
     * @param {Array} [options.domain]
     * @param {boolean} [options.incrementUnread] whether we should increment
     *   the unread_counter of channel.
     * @param {boolean} [options.silent] whether it should inform in the mailBus
     *   of the newly created message.
     * @returns {Promise<mail.model.Message>}
     */
    addMessage: function (data, options) {
        options = options || {};
        var message = this.getMessage(data.id);
        var prom;
        if (!message) {
            prom = this._addNewMessage(data, options);
        } else {
            if (data.moderation_status === 'accepted') {
                message.setModerationStatus('accepted', {
                    additionalThreadIDs: data.channel_ids
                });
            }
            this._addMessageToThreads(message, options);
            prom = Promise.resolve(message);
        }
        return prom;
    },
    /**
     * Creates a channel, can be either a true channel or a DM chat based on
     * `type`
     *
     * @param {integer|string} name id of partner (in case of dm) or name
     * @param {string} type ['dm_chat', 'public', 'private']
     * @returns {Promise<integer>} resolved with ID of the newly created
     *   channel
     */
    createChannel: function (name, type) {
        if (type === 'dm_chat') {
            return this._createDMChat(name);
        } else {
            return this._createChannel(name, type);
        }
    },
    /**
     * Returns the list of canned responses
     * A canned response is a pre-formatted text that is triggered with
     * some keystrokes, such as with ':'.
     *
     * @returns {Array} array of Objects (mail.shortcode)
     */
    getCannedResponses: function () {
        return this._cannedResponses;
    },
    /**
     * Returns a channel corresponding to the given id.
     *
     * @param  {integer} threadID
     * @returns {mail.model.Channel|undefined} the channel, if it exists
     */
    getChannel: function (threadID) {
        return _.find(this._threads, function (thread) {
            return thread.isChannel() && (thread.getID() === threadID);
        });
    },
    /**
     * Returns a list of channels
     *
     * @returns {mail.model.Channel[]} list of channels
     */
    getChannels: function () {
        return _.filter(this._threads, function (thread) {
            return thread.isChannel();
        });
    },
    /**
     * Returns the content that will be shown in the mail navbar dropdown
     *
     * @param {mail.model.Channel[]} channels
     * @returns {Promise<Object[]>} resolved with list of channel previews
     */
    getChannelPreviews: function (channels) {
        var self = this;
        return this._getChannelPreviews(channels).then(function (previews) {
            var sortedPreviews = self._sortPreviews(previews);
            return sortedPreviews;
        });
    },
    /**
     * @returns {web.Bus} the mail bus
     */
    getMailBus: function () {
        return this._mailBus;
    },
    /**
     * Returns the record id of ir.ui.menu for Discuss
     *
     * @returns {integer} record id
     */
    getDiscussMenuID: function () {
        return this._discussMenuID;
    },
    /**
     * Gets direct message channel
     *
     * @param {integer} partnerID
     * @returns {Object|undefined} channel
     */
    getDMChatFromPartnerID: function (partnerID) {
        return _.find(this._threads, function (thread) {
            return thread.getType() === 'dm_chat' &&
                    thread.getDirectPartnerID() === partnerID;
        });
    },
    /**
     * @param {string} mailboxID
     * @returns {mail.model.Mailbox} the mailbox, if any
     */
    getMailbox: function (mailboxID) {
        return _.find(this._threads, function (thread) {
            return thread.getID() === 'mailbox_' + mailboxID;
        });
    },
    /**
     * Returns a list of mail failures
     *
     * @returns {mail.model.MailFailure[]} list of mail failures
     */
    getMailFailures: function () {
        return this._mailFailures;
    },
    /**
     * Get partners as mentions from a chatter
     * Typically all employees as partner suggestions.
     *
     * @returns {Array<Array<Object[]>>}
     */
    getMentionPartnerSuggestions: function () {
        return this._mentionPartnerSuggestions;
    },
    /**
     * Gets message from its ID
     *
     * @param {integer} messageID
     * @returns {mail.model.Message|undefined} the matched message (if any)
     */
    getMessage: function (messageID) {
        return _.find(this._messages, function (message) {
            return message.getID() === messageID;
        });
    },
    /**
     * Returns the previews to display in the systray's messaging menu.
     *
     * @param {string} [filter=undefined] specify 'chat' or 'channels' to only
     *   get previews for that type of threads
     * @returns {Promise<Object[]>} resolved with list of objects that have a
     *   valid format for rendering a messaging menu preview items.
     */
    getSystrayPreviews: function (filter) {
        var self = this;

        var channelDef = this._getSystrayChannelPreviews(filter);
        var inboxDef = this._getSystrayInboxPreviews(filter);
        var failureDef = this._getSystrayMailFailurePreviews(filter);

        return Promise.all([channelDef, inboxDef, failureDef])
            .then(function (result) { //previewsChannel, previewsInbox, previewsFailure
                // order: failures > inbox > channel, each group must be sorted
                var previewsChannel = self._sortPreviews(result[0]);
                var previewsInbox = self._sortPreviews(result[1]);
                var previewsFailure = self._sortPreviews(result[2]);
                return _.union(previewsFailure, previewsInbox, previewsChannel);
            });
    },
    /**
     * Get the list of channel IDs where the current user is a moderator
     *
     * @returns {integer[]}
     */
    getModeratedChannelIDs: function () {
        return this._moderatedChannelIDs || [];
    },
    /**
     * Get the OdooBot ID, which is the default authorID for transient messages
     *
     * @returns {Array<string>}
     */
    getOdoobotID: function () {
        return this._ODOOBOT_ID;
    },
    /**
     * Returns thread matching provided ID, if any
     *
     * @param {string|integer} threadID
     * @returns {mail.model.Thread|undefined} the thread, if it exists
     */
    getThread: function (threadID) {
        return _.find(this._threads, function (thread) {
            return thread.getID() === threadID;
        });
    },
    /**
     * Returns a list of threads
     *
     * @returns {mail.model.Thread[]} list of threads
     */
    getThreads: function () {
        return this._threads;
    },
    /**
     * States whether the current user is a moderator or not
     *
     * @returns {boolean}
     */
    isMyselfModerator: function () {
        return this._isMyselfModerator;
    },
    /**
     * States whether the mail manager is ready or not
     * This is the case when it has fetched the initial state from the server,
     * by means of the route 'mail/init_messaging'
     *
     * @returns {boolean}
     */
    isReady: function () {
        return this._isReady;
    },
    /**
     * Join an existing channel
     * See @createChannel to join a new channel
     *
     * @param {integer} channelID
     * @param {Object} [options] options to be passed on channel add
     * @returns {Promise<integer>} resolved with channelID joined
     */
    joinChannel: function (channelID, options) {
        var prom;
        var channel = this.getChannel(channelID);
        if (channel) {
            // channel already joined
            prom = Promise.resolve(channelID);
        } else {
            prom = this._joinAndAddChannel(channelID, options);
        }
        return prom;
    },
    /**
     * Mark messages as read
     *
     * @param  {Array} messageIDs list of messages IDs
     * @returns {Promise} resolved when messages have been marked as read on
     *   the server.
     */
    markMessagesAsRead: function (messageIDs) {
        var self = this;
        var ids = _.filter(messageIDs, function (id) {
            var message = self.getMessage(id);
            // If too many messages, not all are fetched,
            // and some might not be found
            return !message || message.isNeedaction();
        });
        if (ids.length) {
            return this._rpc({
                model: 'mail.message',
                method: 'set_message_done',
                args: [ids],
            });
        } else {
            return Promise.resolve();
        }
    },
    /**
     * @param {Object} data
     * @param {integer} data.channelID
     */
    notifyChannelFetched: function (data) {
        this._toNotifyChannelFetchedIDs = _.uniq(this._toNotifyChannelFetchedIDs.concat(data.channelID));
        this._throttleNotifyChannelFetched();
    },
    /**
     * @param {integer|string} threadID
     */
    openThread: function (threadID) {
        this._openThreadInDiscuss(threadID);
    },
    /**
     * Special redirection handling for given model and id
     *
     * If the model is res.partner, and there is a user associated with this
     * partner which isn't the current user, open the DM chat with this user.
     * Otherwhise, open the record's form view (if not current user's).
     *
     * @param {string} resModel model to open
     * @param {integer} resID record to open
     * @param {function} [dmRedirectionCallback] only used if 'res.partner',
     *   a function that has a threadID as input
     */
    redirect: function (resModel, resID, dmRedirectionCallback) {
        if (resModel === 'res.partner') {
            this._redirectPartner(resModel, resID, dmRedirectionCallback);
        } else {
            this._redirectDefault(resModel, resID);
        }
    },
    /**
     * Remove the message from all of its threads
     *
     * @param {mail.model.Message} message
     */
    removeMessageFromThreads: function (message) {
        var self = this;
        _.each(message.getThreadIDs(), function (threadID) {
            var thread = self.getThread(threadID);
            if (thread) {
                thread.removeMessage(message.getID());
            }
        });
    },
    /**
     * Search among prefetched partners, using the string 'searchVal'
     *
     * @param {string} searchVal
     * @param {integer} limit max number of found partners in the response
     * @returns {Promise<Object[]>} list of found partners (matching
     *   'searchVal')
     */
    searchPartner: function (searchVal, limit) {
        var self = this;
        var partners = this._searchPartnerPrefetch(searchVal, limit);
        return new Promise(function (resolve, reject) {
            if (!partners.length) {
                resolve(self._searchPartnerFetch(searchVal, limit));
            } else {
                resolve(partners);
            }
        }).then(function (partners) {
            var suggestions = _.map(partners, function (partner) {
                return {
                    id: partner.id,
                    value: partner.name,
                    label: partner.name
                };
            });
            return _.sortBy(suggestions, 'label');
        });
    },
    /**
     * Unstars all messages from all channels
     *
     * @returns {Promise}
     */
    unstarAll: function () {
        return this._rpc({
            model: 'mail.message',
            method: 'unstar_all',
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a channel and returns it.
     * Simply returns the channel if already exists.
     *
     * @private
     * @param {Object} data
     * @param {integer} data.id id of channel
     * @param {string|Object} data.name name of channel, e.g. 'general'
     * @param {string} data.type type of channel, e.g. 'public'
     * @param {string} [data.state] e.g. 'open', 'folded'
     * @param {Object|integer} [options=undefined]
     * @param {boolean} [options.silent=false]
     * @returns {Promise<integer>} resolves with the ID of the newly or already
     *   existing channel
     */
    _addChannel: function (data, options) {
        options = typeof options === 'object' ? options : {};
        var channel = this.getChannel(data.id);
        var proms = [];
        if (!channel) {
            channel = this._makeChannel(data, options);
            if (channel.getType() === 'dm_chat') {
                this._pinnedDmPartners.push(channel.getDirectPartnerID());
            }
            this._threads.push(channel);
            if (data.last_message) {
                // channel_info in mobile, necessary for showing channel
                // preview in mobile
                proms.push(this.addMessage(data.last_message));
            }
            this._sortThreads();
            if (!options.silent) {
                this._mailBus.trigger('new_channel', channel, proms);
            }
        }
        return Promise.all(proms).then(function () {
            return channel.getID();
        });
    },
    /**
     * Add a new mailbox
     *
     * @private
     * @param {Object} data
     * @param {Object} options
     * @returns {mail.model.Mailbox}
     */
    _addMailbox: function (data, options) {
        options = typeof options === 'object' ? options : {};
        var mailbox = new Mailbox({
            parent: this,
            data: data,
            options: options,
            commands: this._commands
        });
        this._threads.push(mailbox);
        this._sortThreads();
        return mailbox;
    },
    /**
     * Stores a message to the cache `domain` of all of its threads
     *
     * @private
     * @param {mail.model.Message} message
     * @param {Object} [options={}]
     * @param {Array} [options.domain=[]]
     * @param {boolean} [options.incrementUnread=false]
     */
    _addMessageToThreads: function (message, options) {
        var self = this;
        options = options || {};
        _.each(message.getThreadIDs(), function (threadID) {
            var thread = self.getThread(threadID);
            if (thread) {
                thread.addMessage(message, options);
            }
        });
    },
    /**
     * Add a new message
     *
     * @private
     * @param {Object} data
     * @param {Object} options
     * @return {Promise<mail.model.Message>}
     */
    _addNewMessage: function (data, options) {
        var self = this;
        var message = this._makeMessage(data);
        // Keep the array ordered by ID when inserting the new message
        var index = _.sortedIndex(this._messages, message, function (msg) {
            return msg.getID();
        });
        this._messages.splice(index, 0, message);
        return this._addNewMessagePostprocessThread(message, options).then(function () {
            self._addMessageToThreads(message, options);
            if (!options.silent) {
                self._mailBus.trigger('new_message', message);
            }
            return message;
        });
    },
    /**
     * For newly added message, postprocess threads linked to this message
     *
     * @private
     * @param {mail.model.Message} message
     * @param {Object} options
     * @param {Array} [options.domain]
     * @param {boolean} [options.incrementUnread]
     * @param {boolean} [options.showNotification]
     * @returns {Promise}
     */
    _addNewMessagePostprocessThread: function (message, options) {
        var self = this;
        var proms = [];
        _.each(message.getThreadIDs(), function (threadID) {
            var thread = self.getThread(threadID);
            if (thread) {
                if (
                    thread.getType() !== 'mailbox' &&
                    !message.isMyselfAuthor() &&
                    !message.isSystemNotification()
                ) {
                    if (thread.isTwoUserThread() && options.showNotification) {
                        var prom = Promise.resolve();
                        if (
                            !self._isDiscussOpen() &&
                            !config.device.isMobile &&
                            !thread.isDetached()
                        ) {
                            // automatically open thread window
                            // while keeping it unread
                            prom = thread.detach({ passively: true });
                        }
                        proms.push(prom);
                        prom.then(function () {
                            var query = { isVisible: false };
                            self._mailBus.trigger('is_thread_bottom_visible', thread, query);
                            if (!self.call('bus_service', 'isOdooFocused') || !query.isVisible) {
                                self._notifyIncomingMessage(message);
                            }
                        });
                    }
                }
            }
        });
        return Promise.all(proms);
    },
    /**
     * Create a Channel (other than a DM)
     *
     * @private
     * @param {string} name
     * @param {string} type
     * @returns {Promise<integer>} ID of the created channel
     */
    _createChannel: function (name, type) {
        var context = _.extend({ isMobile: config.device.isMobile }, session.user_context);
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_create',
                args: [name, type],
                kwargs: { context: context },
            })
            .then(this._addChannel.bind(this));
    },
    /**
     * Create a Direct Messages Chat
     *
     * @private
     * @param {string} name
     * @returns {Promise<integer>} ID of the created channel
     */
    _createDMChat: function (name) {
        var context = _.extend({ isMobile: config.device.isMobile }, session.user_context);
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_get',
                args: [[name]],
                kwargs: { context: context },
            })
            .then(this._addChannel.bind(this));
    },
    /**
     * @private
     * @param {integer[]} channelIDs
     * @returns {Promise<Object[]>} resolved with list of channel preview
     */
    _fetchChannelPreviews: function (channelIDs) {
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_fetch_preview',
                args: [channelIDs],
            }, { shadow: true });
    },
    /**
     * @private
     */
    _fetchMailStateFromServer: function () {
        var self = this;
        session.is_bound.then(function () {
            var context = _.extend(
                { isMobile: config.device.isMobile },
                session.user_context
            );
            return self._rpc({
                route: '/mail/init_messaging',
                params: { context: context },
            });
        }).then(function (result) {
            self._updateInternalStateFromServer(result);
            self.call('bus_service', 'startPolling');
            self._isReady = true;
            self._mailBus.trigger('messaging_ready');
        });
    },
    /**
     * Get previews of the channels
     *
     * The preview of a channel is built from the channel information and its
     * lastest message. A channel without a last message is incomplete, so it
     * must fetch this message.
     *
     * Note that a channel could have no message at all, so it fetches for the
     * last message only once per channel. This is correct to not fetch more
     * than once in this case, because any later received message updates
     * automatically the last message of a channel.
     *
     * @private
     * @param {mail.model.Channel[]} channels
     * @returns {Promise<Object[]>} resolved with list of channel previews
     */
    _getChannelPreviews: function (channels) {
        var self = this;

        var unpreviewedChannels = _.reject(channels, function (channel) {
            return channel.hasBeenPreviewed();
        });
        var fetchDef;
        if (unpreviewedChannels.length) {
            var ids = _.map(unpreviewedChannels, function (channel) {
                return channel.getID();
            });
            fetchDef = this._fetchChannelPreviews(ids);
        } else {
            fetchDef = Promise.resolve();
        }
        return fetchDef.then(function (fetchedPreviews) {
            // add fetched messages
            var proms = [];
            _.each(fetchedPreviews, function (fetchedPreview) {
                if (fetchedPreview.last_message) {
                    proms.push(self.addMessage(fetchedPreview.last_message));
                }
                // mark the channel as previewed, so that we do not need to
                // fetch preview again
                var channel = self.getChannel(fetchedPreview.id);
                channel.markAsPreviewed();
            });
            return Promise.all(proms);
        }).then(function () {
            return _.map(channels, function (channel) {
                return channel.getPreview();
            });
        });
    },
    /**
     * Get the previews of the mail failures
     * Mail failures of a same model with the same type are grouped together, so
     * that there are few preview items on the messaging menu in the systray.
     *
     * To determine whether this is a model preview or a document preview review
     * the documentID is omitted for a model preview, whereas it is set for a
     * preview of a failure related to a document.
     *
     * @returns {Promise<Object[]>} resolved with previews of mail failures
     */
    _getMailFailurePreviews: function () {
        // items = list of objects:
        //  item = {
        //      unreadCounter: {integer},
        //      failure: {mail.model.MailFailure},
        //      isSameDocument: {boolean}
        //  }
        var items = [];
        _.each(this._mailFailures, function (failure) {
            var unreadCounter = 1;
            var isSameDocument = true;
            var sameModelAndTypeItem = _.find(items, function (item) {
                if (
                    item.failure.isLinkedToDocument() &&
                    (item.failure.getDocumentModel() === failure.getDocumentModel()) &&
                    (item.failure.getFailureType() === failure.getFailureType())
                ) {
                    isSameDocument = item.failure.getDocumentID() === failure.getDocumentID();
                    return true;
                }
                return false;
            });

            if (failure.isLinkedToDocument() && sameModelAndTypeItem) {
                unreadCounter = sameModelAndTypeItem.unreadCounter + 1;
                isSameDocument = sameModelAndTypeItem.isSameDocument && isSameDocument;
                var index = _.findIndex(items, sameModelAndTypeItem);
                items[index] = {
                    unreadCounter: unreadCounter,
                    failure: failure,
                    isSameDocument: isSameDocument,
                };
            } else {
                items.push({
                    unreadCounter: unreadCounter,
                    failure: failure,
                    isSameDocument: true,
                });
            }
        });
        return _.map(items, function (item) {
            // return preview with correct unread counter
            // also unset documentID if the grouped mail failures are from
            // same model but different document
            var preview = {};
            _.extend(preview, item.failure.getPreview(), {
                unreadCounter: item.unreadCounter,
            });
            if (!item.isSameDocument) {
                preview.documentID = undefined;
            }
            return preview;
        });
    },
    /**
     * @private
     * @param {string|undefined} [filter] the filter to apply on channel
     *   previews in systray messaging menu
     * @returns {Promise<Object[]>} resolved with object valid for template
     *   mail.Preview on channel previews, based on selected filter
     */
    _getSystrayChannelPreviews: function (filter) {
        var filteredThreads = _.filter(this._threads, function (thread) {
            if (!thread.isChannel()) {
                return false;
            }
            if (filter === 'chat') {
                return thread.isTwoUserThread();
            } else if (filter === 'channels') {
                return !thread.isTwoUserThread();
            }
            return true;
        });
        return this.getChannelPreviews(filteredThreads);
    },
    /**
     * Get the previews of needaction messages, i.e. messages in Inbox mailbox,
     * based on selected filter.
     *
     * FIXME: it will use the current fetched messages in inbox + perform
     * another message fetch on inbox. In other words, it means that some thread
     * previews may be missing in the systray messaging menu. For example:
     *
     *   - Each message fetch on Inbox fetches at most 30 messages.
     *   - There are 31 messages on Inbox.
     *   - No message on Inbox has been fetched at the moment
     *   - the 1st message on Inbox is linked to a document, and no other
     *     message in Inbox is linked to this document
     *
     * When clicking on the messaging menu, it will fetch all messages of Inbox,
     * except the 1st message, in order to show the previews. The preview of
     * the document thread of the 1st message will not be shown in the message
     * menu
     *
     * This is a limitation, which should be solved by making changes on the
     * server logic (e.g. provide list of all document threads in inbox on
     * the rpc mail/init_messaging).
     *
     * @private
     * @param {string|undefined} [filter]
     * @returns {Promise<Object[]>} resolved with valid objects for template
     *   mail.Preview on inbox message previews
     */
    _getSystrayInboxPreviews: function (filter) {
        // 'All' filter, show messages preview from inbox and mail failures
        // inbox previews
        if (filter === 'mailbox_inbox' || !filter) {
            var inbox = this.getMailbox('inbox');
            return inbox.getMessagePreviews();
        } else {
            return Promise.resolve([]);
        }
    },
    /**
     * Get the previews of mail failure, based on selected filter.
     *
     * @private
     * @param {string|undefined} [filter]
     */
    _getSystrayMailFailurePreviews: function (filter) {
        // mail failure previews
        if (filter === 'mailbox_inbox' || !filter) {
            return this._getMailFailurePreviews();
        } else {
            return Promise.resolve([]);
        }
    },
    /**
     * Initialize the internal state of the mail service. Ensure that all
     * attributes are set before doing any operation on them.
     *
     * @private
     */
    _initializeInternalState: function () {
        this._cannedResponses = [];
        this._mailBus = new Bus(this);
        this._commands = [];
        this._discussMenuID = undefined;
        this._discussOpen = false;
        this._isMyselfModerator = false;
        this._mailFailures = [];
        // list of employees for chatter mentions
        this._mentionPartnerSuggestions = [];
        this._messages = [];
        this._moderatedChannelIDs = [];
        // # of message received when odoo is out of focus
        this._outOfFocusUnreadMessageCounter = 0;
        // partner_ids we have a pinned DM chat with
        this._pinnedDmPartners = [];
        // all threads, including channels, DM, mailboxes, document threads, ...
        this._threads = [];

        this._addMailbox({
            id: 'inbox',
            name: _t("Inbox"),
        });
        this._addMailbox({
            id: 'starred',
            name: _t("Starred"),
        });
        this._addMailbox({
            id: 'history',
            name: _t("History"),
        });
    },
    /**
     * State whether discuss app is open or not
     *
     * @private
     * @returns {boolean}
     */
    _isDiscussOpen: function () {
        return this._discussOpen;
    },
    /**
     * Join the channel, and add it locally afterwards
     *
     * @private
     * @param {integer|string} channelID
     * @param {Object} options options passed on channel add
     * @returns {Promise<integer>} channelID of joined and added channel
     */
    _joinAndAddChannel: function (channelID, options) {
        var self = this;
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_join_and_get_info',
                args: [[channelID]],
            })
            .then(function (result) {
                return self._addChannel(result, options);
            });
    },
    /**
     * Listen on several buses, before doing any action that trigger something
     * on those buses.
     *
     * @private
     */
    _listenOnBuses: function () {
        this._mailBus.on('discuss_open', this, this._onDiscussOpen);
        this.call('bus_service', 'on', 'window_focus', this, this._onWindowFocus);
    },
    /**
     * Creates a new instance of Channel with the given data and options.
     *
     * @private
     * @param {Object} data
     * @param {Array} [data.channel_type] if set and is 'livechat', the channel
     *   is a Livechat.
     * @param {Array} [data.direct_partner] if set and is an non-empty array,
     *   the channel is a DM chat
     * @param {Object} [options]
     * @returns {mail.model.Channel}
     */
    _makeChannel: function (data, options) {
        if (_.size(data.direct_partner) > 0) {
            return new DMChat({
                parent: this,
                data: data,
                options: options,
                commands: this._commands
            });
        }
        if (data.channel_type === 'livechat') {
            return new Livechat({
                parent: this,
                data: data,
                options: options,
                commands: this._commands,
            });
        }
        return new MultiUserChannel({
            parent: this,
            data: data,
            options: options,
            commands: this._commands,
        });
    },
    /**
     * Creates a new instance of Message with the given data.
     *
     * @private
     * @param {Object} data
     * @returns {mail.model.Message}
     */
    _makeMessage: function (data) {
        return new Message(this, data);
    },
    /**
     * @private
     * @returns {$.Promise}
     */
    _notifyChannelFetched: function () {
        var channelIDs = this._toNotifyChannelFetchedIDs;
        this._toNotifyChannelFetchedIDs = [];
        if (_.isEmpty(channelIDs)) {
            // no channel to notify fetched
            return Promise.resolve();
        }
        return this._rpc({
            model: 'mail.channel',
            method: 'channel_fetched',
            args: [channelIDs],
        }, { shadow: true });
    },
    /**
     * shows a popup to notify a new received message.
     * This will also rename the browser tab if this is not the active tab.
     *
     * @private
     * @param {mail.model.Message} message message received
     */
    _notifyIncomingMessage: function (message) {
        if (this.call('bus_service', 'isOdooFocused')) {
            // no need to notify
            return;
        }
        var title = _t("New message");
        if (message.hasAuthor()) {
            title = _.escape(message.getAuthorName());
        }
        var content = mailUtils.parseAndTransform(message.getBody(), mailUtils.stripHTML)
            .substr(0, PREVIEW_MSG_MAX_SIZE);

        if (!this.call('bus_service', 'isOdooFocused')) {
            this._outOfFocusUnreadMessageCounter++;
            var tabTitle = _.str.sprintf(
                _t("%d Messages"),
                this._outOfFocusUnreadMessageCounter
            );
            this.trigger_up('set_title_part', {
                part: '_chat',
                title: tabTitle
            });
        }

        this.call('bus_service', 'sendNotification', title, content);
    },
    /**
     * Open the thread in the Discuss app
     *
     * @private
     * @param {integer|string} threadID a valid threadID
     */
    _openThreadInDiscuss: function (threadID) {
        var thread = this.getThread(threadID);
        this._mailBus.trigger('open_thread_in_discuss', thread);
    },
    /**
     * @private
     * @param {string} resModel
     * @param {integer} resID
     */
    _redirectDefault: function (resModel, resID) {
        var self = this;
        this._rpc({
                model: resModel,
                method: 'get_formview_id',
                args: [[resID], session.user_context.uid],
            })
            .then(function (viewID) {
                self._redirectToDocument(resModel, resID, viewID);
            });
    },
    /**
     * @private
     * @param  {Object} message
     * @param  {Array} message.channel_ids list of integers and strings,
     *      where strings for static channels, e.g. 'mailbox_inbox'.
     * @param {string} resModel
     * @param {integer} resID
     * @param {string} viewID
     */
    _redirectToDocument: function (resModel, resID, viewID) {
        this.do_action({
            type: 'ir.actions.act_window',
            view_mode: 'form',
            res_model: resModel,
            views: [[viewID || false, 'form']],
            res_id: resID,
        });
    },
    /**
     * @private
     * @param {string} resModel 'res.partner'
     * @param {integer} resID
     * @param {function} dmRedirection a function callback that has
     *   threadID as input
     */
    _redirectPartner: function (resModel, resID, dmRedirection) {
        var self = this;
        var domain = [['partner_id', '=', resID], ['share', '=', false]];
        this._rpc({
                model: 'res.users',
                method: 'search',
                args: [domain],
            })
            .then(function (userIDs) {
                if (
                    userIDs.length &&
                    userIDs[0] !== session.uid &&
                    dmRedirection
                ) {
                    self.createChannel(resID, 'dm_chat').then(dmRedirection);
                } else {
                    self._redirectToDocument(resModel, resID);
                }
            });
    },
    /**
     * Remove channel
     *
     * This is only called by the mail_notification_manager
     *
     * @private
     * @param {mail.model.Channel} [channel]
     */
    _removeChannel: function (channel) {
        if (!channel) { return; }
        if (channel.getType() === 'dm_chat') {
            var index = this._pinnedDmPartners.indexOf(channel.getDirectPartnerID());
            if (index > -1) {
                this._pinnedDmPartners.splice(index, 1);
            }
        }
        this._threads = _.without(this._threads, channel);
    },
    /**
     * Removes a message from a thread.
     *
     * @private
     * @param {string} threadID
     * @param {mail.model.Message} message
     */
    _removeMessageFromThread: function (threadID, message) {
        message.removeThread(threadID);
        var thread = _.find(this._threads, function (thread) {
            return thread.getID() === threadID;
        });
        thread.removeMessage(message.getID());
    },
    /**
     * @private
     */
    _resetOutOfFocusUnreadMessageCounter: function () {
        this._outOfFocusUnreadMessageCounter = 0;
    },
    /**
     * Extend the research to all users
     *
     * @private
     * @param {string} searchVal
     * @param {integer} limit
     * @returns {Promise<Object[]>} fetched partners matching 'searchVal'
     */
    _searchPartnerFetch: function (searchVal, limit) {
        return this._rpc({
                model: 'res.partner',
                method: 'im_search',
                args: [searchVal, limit || 20],
            }, { shadow: true });
    },
    /**
     * Search among prefetched partners
     *
     * @private
     * @param {string} searchVal
     * @param {integer} limit
     * @returns {string[]} partner suggestions that match searchVal
     *   (max limit, exclude session partner)
     */
    _searchPartnerPrefetch: function (searchVal, limit) {
        var values = [];
        var searchRegexp = new RegExp(_.str.escapeRegExp(utils.unaccent(searchVal)), 'i');
        _.each(this._mentionPartnerSuggestions, function (partners) {
            if (values.length < limit) {
                values = values.concat(_.filter(partners, function (partner) {
                    return (session.partner_id !== partner.id) &&
                            searchRegexp.test(partner.name);
                })).splice(0, limit);
            }
        });
        return values;
    },
    /**
     * Sort previews
     *
     *      1. unread,
     *      2. dated previews
     *      3. two-user thread,
     *      4. date,
     *
     * @private
     * @param {Object[]} previews
     * @returns {Object[]} sorted list of previews
     */
    _sortPreviews: function (previews) {
        var res = previews.sort(function (p1, p2) {
            var unreadDiff = Math.min(1, p2.unreadCounter) - Math.min(1, p1.unreadCounter);
            var datedDiff = !!p2.date - !!p1.date;
            var isTwoUserThreadDiff = p2.isTwoUserThread - p1.isTwoUserThread;
            var dateDiff = p2.date && p2.date.diff(p1.date);
            return  unreadDiff || datedDiff || isTwoUserThreadDiff || dateDiff;
        });
        return res;
    },
    /**
     * Sort threads
     *
     * In case of mailboxes (Inbox, Starred), the name is translated
     * thanks to _lt (lazy translate). In this case, channel.getName() is an
     * object, not a string.
     *
     * @private
     */
    _sortThreads: function () {
        this._threads = _.sortBy(this._threads, function (thread) {
            var name = thread.getName();
            return _.isString(name) ? name.toLowerCase() : '';
        });
    },
    /**
     * Update the canned responses with mail data fetched from the server
     *
     * @private
     * @param {Object} data
     * @param {Object[]} [data.shortcodes]
     * @param {integer} data.shortcodes[i].id
     * @param {string} data.shortcodes[i].source
     * @param {string} data.shortcodes[i].substitution
     */
    _updateCannedResponsesFromServer: function (data) {
        var self = this;
        _.each(data.shortcodes, function (s) {
            var cannedResponse = _.pick(s, ['id', 'source', 'substitution']);
            self._cannedResponses.push(cannedResponse);
        });
    },
    /**
     * Update the channels with the mail data fetched from server, including
     * public, private, DM, livechat, etc.
     *
     * @private
     * @param {Object} data
     * @param {Object} [data.channel_slots] contains the data of channels to
     *   update, which are grouped by channel type by key of the object
     *   (e.g. list of public channel data are stored in 'channel_channel')
     * @param {Object[]} [data.channel_slots[i] list of data of channel of type
     *   `i`
     * @returns {Promise}
     */
    _updateChannelsFromServer: function (data) {
        var self = this;
        var proms = [];
        const options = {};

        _.each(data.channel_slots, function (channels) {
            _.each(channels, function (channel) {
                proms.push(self._addChannel(channel, options));
            });
        });
        return Promise.all(proms);
    },
    /**
     * Update commands from mail data fetched from the server
     *
     * @private
     * @param {Object} data
     * @param {Object[]} data.commands list of command data from the server
     */
    _updateCommandsFromServer: function (data) {
        this._commands = _.map(data.commands, function (command) {
            return _.extend({ id: command.name }, command);
        });
    },
    /**
     * Update internal state from server data (mail/init_messaging rpc result)
     *
     * @private
     * @param {Object} result data from server on mail/init_messaging rpc
     * @param {Array<Object[]>} result.mention_partner_suggestions list of
     *   suggestions.
     * @param {integer} result.menu_id the menu ID of discuss app
     * @returns {Promise}
     */
    _updateInternalStateFromServer: function (result) {
        // commands are needed for channel instantiation
        this._updateCommandsFromServer(result);
        var prom = this._updateChannelsFromServer(result);
        this._updateModerationSettingsFromServer(result);
        this._updateMailboxesFromServer(result);
        this._updateMailFailuresFromServer(result);
        this._updateCannedResponsesFromServer(result);

        this._mentionPartnerSuggestions = result.mention_partner_suggestions;
        this._discussMenuID = result.menu_id;

        return prom;
    },
    /**
     * Update the mailboxes with mail data fetched from server, namely 'Inbox',
     * 'Starred', 'History', and 'Moderation Queue' if the user is a moderator of a channel
     *
     * @private
     * @param {Object} data
     * @param {boolean} [data.is_moderator=false] states whether the user is
     *   moderator of a channel
     * @param {integer} [data.moderation_counter=0] states the mailbox counter
     *   to set to 'Moderation Queue'
     * @param {integer} [data.needaction_inbox_counter=0] states the mailbox
     *   counter to set to 'Inbox'
     * @param {integer} [data.starred_counter=0] states the mailbox counter to
     *   set to 'Starred'
     */
    _updateMailboxesFromServer: function (data) {
        this.getMailbox('inbox').setMailboxCounter(data.needaction_inbox_counter || 0);
        this.getMailbox('starred').setMailboxCounter(data.starred_counter || 0);

        if (data.is_moderator) {
            this._addMailbox({
                id: 'moderation',
                name: _t("Moderate Messages"),
                mailboxCounter: data.moderation_counter || 0,
            });
        }
    },
    /**
     * Update mail failures with mail data fetched from the server
     *
     * @private
     * @param {Object} data
     * @param {Object[]} data.mail_failures data to update mail failures
     *   locally
     */
    _updateMailFailuresFromServer: function (data) {
        var self = this;
        this._mailFailures = _.map(data.mail_failures, function (mailFailureData) {
            return new MailFailure(self, mailFailureData);
        });
    },
    /**
     * Update moderation settings with mail data fetched from server
     *
     * @private
     * @param {Object} data
     * @param {boolean} [data.is_moderator=false]
     * @param {integer[]} [data.moderation_channel_ids]
     */
    _updateModerationSettingsFromServer: function (data) {
        this._isMyselfModerator = data.is_moderator;
        this._moderatedChannelIDs = data.moderation_channel_ids;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {boolean} open
     */
    _onDiscussOpen: function (open) {
        this._discussOpen = open;
    },
    /**
     * Reset out of focus unread message counter + tab title
     *
     * @private
     */
    _onWindowFocus: function () {
        this._resetOutOfFocusUnreadMessageCounter();
        this.trigger_up('set_title_part', { part: '_chat' });
    },
});

return MailManager;

});
