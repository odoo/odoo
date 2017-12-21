odoo.define('mail.ChatWindowManager', function (require) {
"use strict";

var ExtendedChatWindow = require('mail.ExtendedChatWindow');

var AbstractService = require('web.AbstractService');
var config = require('web.config');
var core = require('web.core');
var utils = require('web.utils');
var web_client = require('web.web_client');

var _t = core._t;
var QWeb = core.qweb;

//----------------------------------------------------------------
var CHAT_WINDOW_WIDTH = 325 + 5;  // 5 pixels between windows

/**
 * This service handles chat channels that are displayed in "chat window" mode
 */
var ChatWindowManager =  AbstractService.extend({
    name: 'chat_window_manager',
    dependencies: ['chat_manager'],

    /**
     * @override
     */
    init: function () {
        var self = this;

        this._super.apply(this, arguments);

        this.chatSessions = [];
        this.newChatSession;
        this.displayState = {
            chatWindowsHidden: false,  // chat windows aren't displayed when the client action is open
            hiddenSessions: [],
            hiddenUnreadCounter: 0,  // total number of unread msgs in hidden chat windows
            nbSlots: 0,
            spaceLeft: 0,
            windowsDropdownIsOpen: false,  // used to keep dropdown open when closing chat windows
        };
        var chatReady = this.call('chat_manager', 'isReady');
        chatReady.then(function () {
            var channels = self.call('chat_manager', 'getChannels');
            _.each(channels, function (channel) {
                if (channel.is_detached) {
                    self.openChat(channel);
                }
            });
        });

        var chatBus = this.call('chat_manager', 'getChatBus');
        chatBus.on('update_message', this, this._onUpdateMessage);
        chatBus.on('new_message', this, this._onNewMessage);
        chatBus.on('anyone_listening', this, this._onAnyoneListening);
        chatBus.on('unsubscribe_from_channel', this, this._onUnsubscribeFromChannel);
        chatBus.on('update_channel_unread_counter', this, this._onUpdateChannelUnreadCounter);
        chatBus.on('update_dm_presence', this, this._onUpdateDmPresence);
        chatBus.on('detach_channel', this, this._onDetachChannel);
        chatBus.on('discuss_open', this, this._onDiscussOpen);

        core.bus.on('resize', this, _.debounce(this._repositionWindows.bind(this), 100));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object} chatSession
     * @param {integer} chatSession.id
     * @param {Object} options
     */
    closeChat: function (chatSession, options) {
        var session = _.find(this.chatSessions, {id: chatSession.id});
        if (session) {
            this._closeChat(session, options);
        }
    },
    /**
     * @param {Object} session
     * @param {integer} session.id
     * @param {boolean} [session.is_chat] true for dm? => server_type="chat" & type="dm"...
     * @param {boolean} [session.mass_mailing]
     * @param {string} [session.status] e.g. 'offline'
     * @param {Object} [options]
     * @param {boolean} [options.passively] if set to true, open the chat window
     * without focusing the input and marking messages as read if it is not
     * open yet, and do nothing otherwise
     */ 
    openChat: function (session, options) {
        var self = this;
        if (!session) {
            this._openChatWithoutSession();
            return;
        }
        options = options || {};
        var chatSession = _.findWhere(this.chatSessions, {id: session.id});
        if (!chatSession) {
            var prefix = !session.is_chat ? "#" : "";
            var windowOptions = {
                autofocus: !options.passively,
                input_less: session.mass_mailing,
                status: session.status,
            };
            chatSession = {
                id: session.id,
                uuid: session.uuid,
                name: session.name,
                keep_unread: options.passively, // don't automatically mark unread messages as seen
                window: new ExtendedChatWindow(web_client, session.id, prefix + session.name, session.is_folded, session.unread_counter, windowOptions),
            };
            chatSession.window.on("close_chat_session", null, function () {
                self._closeChat(chatSession);
                self.call('chat_manager', 'closeChatSession', chatSession.id);
            });
            chatSession.window.on("toggle_star_status", null, function (messageID) {
                self.call('chat_manager', 'toggleStarStatus', messageID);
            });

            chatSession.window.on("fold_channel", null, function (channelID, folded) {
                self.call('chat_manager', 'foldChannel', channelID, folded);
            });

            chatSession.window.on("post_message", null, function (message, channelID) {
                self.call('chat_manager', 'postMessage', message, {
                        channelID: channelID
                    }).then(function () {
                        chatSession.window.thread.scroll_to();
                    });
            });
            chatSession.window.on("redirect", null, function (resModel, resID) {
                self.call('chat_manager', 'redirect', resModel, resID, self.openChat.bind(self));
            });
            chatSession.window.on("redirect_to_channel", null, function (channelID) {
                var session = _.findWhere(self.chatSessions, {id: channelID});
                if (!session) {
                    self.call('chat_manager', 'joinChannel', channelID).then(function (channel) {
                        self.call('chat_manager', 'detachChannel', channelID);
                    });
                } else {
                    session.window.toggle_fold(false);
                }
            });

            var removeNewChat = false;
            if (options.passively) {
                this.chatSessions.push(chatSession); // simply insert the window to the left
            } else if (this.newChatSession && this.newChatSession.partner_id && this.newChatSession.partner_id === session.direct_partner_id) {
                // the window takes the place of the 'newChatSession' window
                this.chatSessions[_.indexOf(this.chatSessions, this.newChatSession)] = chatSession;
                removeNewChat = true;
            } else {
                this._addChatSession(chatSession); // add session such that window is visible
            }

            chatSession.window.appendTo($('body'))
                .then(function () {
                    self._repositionWindows({remove_new_chat: removeNewChat});
                    return self.call('chat_manager', 'getMessages', {channelID: chatSession.id});
                }).then(function (messages) {
                    chatSession.window.render(messages);
                    chatSession.window.thread.scroll_to();
                    setTimeout(function () {
                        chatSession.window.thread.$el.on("scroll", null, _.debounce(function () {
                            if (!chatSession.keep_unread && chatSession.window.thread.is_at_bottom()) {
                                self.call('chat_manager', 'markChannelAsSeen', session);
                            }
                        }, 100));
                    }, 0); // setTimeout to prevent to execute handler on first scroll_to, which is asynchronous
                    if (options.passively) {
                        // mark first unread messages as seen when focusing the window, then on scroll to bottom as usual
                        chatSession.window.$('.o_mail_thread, .o_chat_composer').one('click', function () {
                            self.call('chat_manager', 'markChannelAsSeen', session);
                        });
                    } else if (!self.displayState.chatWindowsHidden && !session.is_folded) {
                        self.call('chat_manager', 'markChannelAsSeen', session);
                    }
                });
        } else if (!options.passively) {
            if (chatSession.window.is_hidden) {
                this._makeSessionVisible(chatSession);
            } else if (session.is_folded !== chatSession.window.folded) {
                chatSession.window.toggle_fold(session.is_folded);
            }
        }
    },
    /**
     * Called when unfolding the chat window
     * 
     * @param {Object} channel
     * @param {integer} channel.id
     * @param {boolean} [channel.is_folded]
     */
    toggleFoldChat: function (channel) {
        var session = _.find(this.chatSessions, {id: channel.id});
        if (session) {
            session.window.toggle_fold(channel.is_folded);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add chatSession such that it will be the left-most visible window
     *
     * @private
     * @param {Object} chatSession
     */
    _addChatSession: function (chatSession) {
        this._computeAvailableSlots(this.chatSessions.length+1);
        this.chatSessions.splice(this.displayState.nbSlots-1, 0, chatSession);
    },
    /**
     * @private
     * @param {Object} chatSession
     * @param {boolean} [chatSession.keep_unread]
     * @param {Object} chatSession.window
     * @param {Object} [options]
     * @param {boolean} [options.keep_open_if_unread]
     */
    _closeChat: function (chatSession, options) {
        if (options && options.keep_open_if_unread && chatSession.keep_unread) {
            return;
        }
        this.chatSessions = _.without(this.chatSessions, chatSession);
        chatSession.window.destroy();
        this._repositionWindows();
    },
    /**
     * @private
     */
    _closeNewChat: function () {
        this.chatSessions = _.without(this.chatSessions, this.newChatSession);
        this._repositionWindows({remove_new_chat: true});
    },
    /**
     * @private
     * @param {integer} nbWindows
     */
    _computeAvailableSlots: function (nbWindows) {
        if (config.device.isMobile) {
            this.displayState.nbSlots = 1; // one chat window full screen in mobile
            return;
        }
        var width = window.innerWidth;
        var nbSlots = Math.floor(width/CHAT_WINDOW_WIDTH);
        var spaceLeft = width - (Math.min(nbSlots, nbWindows)*CHAT_WINDOW_WIDTH);
        if (nbSlots < nbWindows && spaceLeft < 50) {
            nbSlots--;  // leave at least 50px for the hidden windows dropdown button
            spaceLeft += CHAT_WINDOW_WIDTH;
        }
        this.displayState.nbSlots = nbSlots;
        this.displayState.spaceLeft = spaceLeft;
    },
    /**
     * @private
     */
    _destroyNewChat: function () {
        this.newChatSession.window.destroy();
        this.newChatSession = undefined;
    },
    /**
     * @private
     * @param {Object} session
     * @param {Widget} session.window
     */
    _makeSessionVisible: function (session) {
        utils.swap(this.chatSessions, session, this.chatSessions[this.displayState.nbSlots-1]);
        this._repositionWindows();
        session.window.toggle_fold(false);
    },
    /**
     * @private
     */
    _openChatWithoutSession: function () {
        var self = this;
        if (!this.newChatSession) {
            this.newChatSession = {
                id: '_open',
                window: new ExtendedChatWindow(web_client, undefined, _t('New message'), false, 0, {thread_less: true}),
            };
            this.newChatSession.window.on("close_chat_session", null, this._closeNewChat.bind(this));
            this.newChatSession.window.on('open_dm_session', null, function (partner_id) {
                self.newChatSession.partner_id = partner_id;
                var dm = self.call('chat_manager', 'getDmFromPartnerID', partner_id);
                if (!dm) {
                    self.call('chat_manager', 'openAndDetachDm', partner_id);
                } else {
                    var dmSession = _.findWhere(self.chatSessions, {id: dm.id});
                    if (!dmSession) {
                        self.call('chat_manager', 'detachChannel', dm.id);
                    } else {
                        self._closeChat(dmSession);
                        dm.is_folded = false;
                        self.openChat(dm);
                    }
                }
            });
            this._addChatSession(this.newChatSession);
            this.newChatSession.window.appendTo($('body')).then(this._repositionWindows.bind(this));
        } else {
            if (this.newChatSession.window.is_hidden) {
                this._makeSessionVisible(this.newChatSession);
            } else if (this.newChatSession.window.folded) {
                this.newChatSession.window.toggle_fold(false);
            }
        }
    },
    /**
     * @private
     * @param {Object} message
     * @param {integer[]} message.channel_ids
     * @param {boolean} scrollBottom
     */
    _updateSessions: function (message, scrollBottom) {
        var self = this;
        _.each(this.chatSessions, function (session) {
            if (_.contains(message.channel_ids, session.id)) {
                var messageVisible = !self.displayState.chatWindowsHidden && !session.window.folded &&
                                      !session.window.is_hidden && session.window.thread.is_at_bottom();
                if (messageVisible && !session.keep_unread) {
                    var channel = self.call('chat_manager', 'getChannel', session.id);
                    self.call('chat_manager', 'markChannelAsSeen', channel);
                }
                self.call('chat_manager', 'getMessages', {channelID: session.id}).then(function (messages) {
                    session.window.render(messages);
                    if (scrollBottom && messageVisible) {
                        session.window.thread.scroll_to();
                    }
                });
            }
        });
    },
    /**
     * @private
     */
    _renderHiddenSessionsDropdown: function () {
        var $dropdown = $(QWeb.render("mail.ChatWindowsDropdown", {
            sessions: this.displayState.hiddenSessions,
            open: this.displayState.windowsDropdownIsOpen,
            unread_counter: this.displayState.hiddenUnreadCounter,
            widget: {isMobile: config.device.isMobile},
        }));
        return $dropdown;
    },
    /**
     * @private
     */
    _repositionHiddenSessionsDropdown: function () {
        // Unfold dropdown to the left if there is enough place
        var $dropdownUL = this.displayState.$hiddenWindowsDropdown.children('ul');
        if (this.displayState.spaceLeft > $dropdownUL.width() + 10) {
            $dropdownUL.addClass('dropdown-menu-right');
        }
    },
    /**
     * @private
     * @param {Object} [options]
     * @param {boolean} [options.remove_new_chat]
     */
    _repositionWindows: function (options) {
        var self = this;
        if (options && options.remove_new_chat) {
            this._destroyNewChat();
        }
        if (this.displayState.chatWindowsHidden) {
            return;
        }
        this._computeAvailableSlots(this.chatSessions.length);
        var hiddenSessions = [];
        var hiddenUnreadCounter = 0;
        var nbSlots = this.displayState.nbSlots;
        _.each(this.chatSessions, function (session, index) {
            if (index < nbSlots) {
                session.window.$el.css({right: CHAT_WINDOW_WIDTH*index, bottom: 0});
                session.window.do_show();
            } else {
                hiddenSessions.push(session);
                hiddenUnreadCounter += session.window.unread_msgs;
                session.window.do_hide();
            }
        });
        this.displayState.hiddenSessions = hiddenSessions;
        this.displayState.hiddenUnreadCounter = hiddenUnreadCounter;
    
        if (this.displayState.$hidden_windows_dropdown) {
            this.displayState.$hidden_windows_dropdown.remove();
        }
        if (hiddenSessions.length) {
            this.displayState.$hiddenWindowsDropdown = this._renderHiddenSessionsDropdown();
            var $hiddenWindowsDropdown = this.displayState.$hiddenWindowsDropdown;
            $hiddenWindowsDropdown.css({right: CHAT_WINDOW_WIDTH * nbSlots, bottom: 0})
                                    .appendTo($('body'));
            this._repositionHiddenSessionsDropdown();
            this.displayState.windowsDropdownIsOpen = false;
    
            $hiddenWindowsDropdown.on('click', '.o_chat_header', function (event) {
                var sessionID = $(event.currentTarget).data('session-id');
                var session = _.findWhere(hiddenSessions, {id: sessionID});
                if (session) {
                    self._makeSessionVisible(session);
                }
            });
            $hiddenWindowsDropdown.on('click', '.o_chat_window_close', function (event) {
                var sessionID = $(event.currentTarget).closest('.o_chat_header').data('session-id');
                var session = _.findWhere(hiddenSessions, {id: sessionID});
                if (session) {
                    session.window.on_click_close(event);
                    self.displayState.windowsDropdownIsOpen = true;  // keep the dropdown open
                }
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} channel
     * @param {integer|string} channel.id
     * @param {Object} query
     */
    _onAnyoneListening: function (channel, query) {
        _.each(this.chatSessions, function (session) {
            if (channel.id === session.id && session.window.thread.is_at_bottom() && !session.window.is_hidden) {
                query.is_displayed = true;
            }
        });
    },
    /**
     * @private
     * @param {Object} channel
     * @param {integer} channel.id
     */
    _onDetachChannel: function (channel) {
        var chatSession = _.findWhere(this.chatSessions, {id: channel.id});
        if (!chatSession || chatSession.window.folded) {
            this.call('chat_manager', 'detachChannel', channel.id);
        } else if (chatSession.window.is_hidden) {
            this._makeSessionVisible(chatSession);
        } else {
            chatSession.window.focus_input();
        }
    },
    /**
     * @private
     * @param {boolean} open
     */
    _onDiscussOpen: function (open) {
        this.displayState.chatWindowsHidden = open;
        if (open) {
            $('body').addClass('o_no_chat_window');
        } else {
            $('body').removeClass('o_no_chat_window');
            this._repositionWindows();
        }
    },
    /**
     * @private
     * @param {Object} message
     */
    _onNewMessage: function (message) {
        this._updateSessions(message, true);
    },
    /**
     * @private
     * @param {Object} channel
     * @param {integer} channel.unread_counter
     */
    _onUpdateChannelUnreadCounter: function (channel) {
        var self = this;
        this.displayState.hiddenUnreadCounter = 0;
        _.each(self.chatSessions, function (session) {
            if (channel.id === session.id) {
                session.window.update_unread(channel.unread_counter);
                if (channel.unread_counter === 0) {
                    session.keep_unread = false;
                }
            }
            if (session.window.is_hidden) {
                self.displayState.hiddenUnreadCounter += session.window.unread_msgs;
            }
        });
        if (self.displayState.$hidden_windows_dropdown) {
            self.displayState.$hidden_windows_dropdown.html(self.renderHiddenSessionsDropdown().html());
            self._repositionHiddenSessionsDropdown();
        }
    },
    /**
     * @private
     * @param {Object} channel
     * @param {string|integer} channel.id
     * @param {string} channel.status e.g. 'offline'
     */
    _onUpdateDmPresence: function (channel) {
        _.each(this.chatSessions, function (session) {
            if (channel.id === session.id) {
                session.window.update_status(channel.status);
            }
        });
    },
    /**
     * @private
     * @param {Object} message
     */
    _onUpdateMessage: function (message) {
        this._updateSessions(message, false);
    },
    /**
     * @private
     * @param {string|integer} channelID
     */
    _onUnsubscribeFromChannel: function (channelID) {
        var self = this;
        _.each(self.chatSessions, function (session) {
            if (channelID === session.id) {
                self._closeChat(session);
            }
        });
    },

});

return ChatWindowManager;

});
