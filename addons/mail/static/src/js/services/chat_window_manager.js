odoo.define('mail.ChatWindowManager', function (require) {
"use strict";

var ChatSession = require('mail.model.ChatSession');
var utils = require('mail.utils');
var ConversationWindow = require('mail.widget.ConversationWindow');

var Class = require('web.Class');
var config = require('web.config');
var core = require('web.core');
var webClient = require('web.web_client');

var QWeb = core.qweb;

var CHAT_WINDOW_WIDTH = 325 + 5;  // 5 pixels between windows

// CHAT WINDOW MANAGER
var ChatWindowManager = Class.extend({

    init: function (chatManager) {
        this._chatManager = chatManager;

        this._chatSessions = [];
        this._displayState = {
            chatWindowsHidden: false, // chat windows aren't displayed when discuss is open
            hiddenSessions: [],
            hiddenUnreadCounter: 0, // total number of unread msgs in hidden chat windows
            nbSlots: 0,
            spaceLeft: 0,
            windowsDropdownIsOpen: false, // used to keep dropdown open when closing chat windows
        };
        this._newChatSession = undefined;

        var chatBus = this._chatManager.getChatBus();

        chatBus.on('update_message', this, this._onUpdateMessage);
        chatBus.on('new_message', this, this._onNewMessage);
        chatBus.on('anyone_listening', this, this._onAnyoneListening);
        chatBus.on('unsubscribe_from_channel', this, this._onUnsubscribeFromChannel);
        chatBus.on('update_conversation_unread_counter', this, this._onUpdateConversationUnreadCounter);
        chatBus.on('update_dm_presence', this, this._onUpdateDmPresence);
        chatBus.on('detach_conversation', this, this._onDetachConversation);
        chatBus.on('open_chat', this, this.openChat);
        chatBus.on('close_chat', this, this.closeChat);

        core.bus.on('resize', this, _.debounce(this._repositionWindows.bind(this), 100));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {mail.Object.ChatSession} chatSession
     * @param {Object} options
     */
    closeChat: function (chatSession, options) {
        var session = _.find(this._chatSessions, function (session) {
            return session.getID() === chatSession.getID();
        });
        if (session) {
            this._closeChat(session, options);
        }
    },
    /**
     * @param {mail.model.Conversation} conversation
     * @param {Object} [options]
     * @param {boolean} [options.passively] if set to true, open the chat window
     *   without focusing the input and marking messages as read if it is not
     *   open yet, and do nothing otherwise
     */
    openChat: function (conversation, options) {
        var self = this;
        options = options || {};
        var chatSession = this._getChatSession(conversation.getID());
        if (!chatSession) {
            var windowOptions = {
                autofocus: !options.passively,
                status: conversation.getType() === 'mailbox' ? undefined : conversation.getStatus(),
            };
            chatSession = new ChatSession(this, conversation, _.extend(options, {
                chatManager: this._chatManager,
                windowOptions: windowOptions,
            }));

            var removeNewChat = false;
            if (options.passively) {
                this._chatSessions.push(chatSession); // simply insert the window to the left
            } else if (this._newChatSession &&
                       this._newChatSession.partnerID &&
                       this._newChatSession.partnerID === conversation.directPartnerID) {
                // the window takes the place of the 'newChatSession' window
                this._chatSessions[_.indexOf(this._chatSessions, this._newChatSession)] = chatSession;
                removeNewChat = true;
            } else {
                this._addChatSession(chatSession); // add session such that window is visible
            }

            chatSession.window.appendTo($('body'))
                .then(function () {
                    self._repositionWindows({ removeNewChat: removeNewChat });
                    var conversation = self._chatManager.getConversation(chatSession.getID());
                    return conversation.getMessages();
                }).then(function (messages) {
                    chatSession.render(messages);
                    chatSession.window.threadWidget.scrollToBottom();
                    setTimeout(function () {
                        chatSession.window.threadWidget.$el.on('scroll', null, _.debounce(function () {
                            if (!chatSession.keepUnread && chatSession.window.threadWidget.isAtBottom()) {
                                conversation.markAsSeen();
                            }
                        }, 100));
                    }, 0); // setTimeout to prevent to execute handler on first scrollTo, which is asynchronous
                    if (options.passively) {
                        // mark first unread messages as seen when focusing the window, then on scroll to bottom as usual
                        chatSession.window.$('.o_mail_thread, .o_conversation_composer').one('click', function () {
                            conversation.markAsSeen();
                        });
                    } else if (!self._displayState.chatWindowsHidden && !conversation.isFolded()) {
                        conversation.markAsSeen();
                    }
                });
        } else if (!options.passively) {
            if (chatSession.window.isHidden()) {
                this._makeSessionVisible(chatSession);
            } else if (conversation.isFolded() !== chatSession.window.isFolded()) {
                chatSession.window.toggleFold(conversation.isFolded());
            }
        }
    },
    /**
     * Open chat window without a session ('new conversation')
     */
    openChatWithoutSession: function () {
        if (!this._newChatSession) {
            this._newChatSession = {
                id: '_open',
                window: new ConversationWindow(webClient, undefined),
            };
            this._newChatSession.window.on('close_chat_session', this, this._closeNewChat.bind(this));
            this._newChatSession.window.on('open_dm_session', this, this._openDmSession.bind(this));
            this._addChatSession(this._newChatSession);
            this._newChatSession.window.appendTo($('body')).then(this._repositionWindows.bind(this));
        } else {
            if (this._newChatSession.window.isHidden()) {
                this._makeSessionVisible(this._newChatSession);
            } else if (this._newChatSession.window.isFolded()) {
                this._newChatSession.window.toggleFold(false);
            }
        }
    },
    /**
     * @param {integer} chatID
     */
    removeChatSession: function (chatID) {
        this._chatSessions = _.reject(this._chatSessions, function (chatSession) {
            return chatSession.getID() === chatID;
        });
        this._repositionWindows();
        var conversation = this._chatManager.getConversation(chatID);
        conversation.close();
    },
    /**
     * Called when unfolding the chat window
     *
     * @param {mail.model.Conversation} conversation
     */
    toggleFoldChat: function (conversation) {
        var session = _.find(this._chatSessions, function (chatSession) {
            return chatSession.getID() === conversation.getID();
        });
        if (session) {
            session.window.toggleFold(conversation.isFolded());
        }
    },
    /**
     * Update the fold state of `conversation` from `foldState`
     *
     * @param {mail.model.Conversation} conversation
     * @param {string} foldState
     */
    updateConversationFoldState: function (conversation, foldState) {
        // update fold state from data
        if (conversation.isFolded() !== (foldState === 'folded')) {
            conversation._folded = (foldState === 'folded');
            this.toggleFoldChat(conversation);
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
        this._computeAvailableSlots(this._chatSessions.length+1);
        this._chatSessions.splice(this._displayState.nbSlots-1, 0, chatSession);
    },
    /**
     * @private
     * @param {Object} chatSession
     * @param {boolean} [chatSession.keepUnread]
     * @param {Object} chatSession.window
     * @param {Object} [options]
     * @param {boolean} [options.keepOpenIfUnread]
     */
    _closeChat: function (chatSession, options) {
        if (options && options.keepOpenIfUnread && chatSession.keepUnread) {
            return;
        }
        this._chatSessions = _.without(this._chatSessions, chatSession);
        chatSession.window.destroy();
        this._repositionWindows();
    },
    /**
     * @private
     */
    _closeNewChat: function () {
        this._chatSessions = _.without(this._chatSessions, this._newChatSession);
        this._repositionWindows({ removeNewChat: true });
    },
    /**
     * @private
     * @param {integer} nbWindows
     */
    _computeAvailableSlots: function (nbWindows) {
        if (config.device.isMobile) {
            this._displayState.nbSlots = 1; // one chat window full screen in mobile
            return;
        }
        var width = window.innerWidth;
        var nbSlots = Math.floor(width/CHAT_WINDOW_WIDTH);
        var spaceLeft = width - (Math.min(nbSlots, nbWindows)*CHAT_WINDOW_WIDTH);
        if (nbSlots < nbWindows && spaceLeft < 50) {
            nbSlots--;  // leave at least 50px for the hidden windows dropdown button
            spaceLeft += CHAT_WINDOW_WIDTH;
        }
        this._displayState.nbSlots = nbSlots;
        this._displayState.spaceLeft = spaceLeft;
    },
    /**
     * @private
     */
    _destroyNewChat: function () {
        this._newChatSession.window.destroy();
        this._newChatSession = undefined;
    },
    /**
     * Get chat session matching id `chatID`
     *
     * @private
     * @param {integer} chatID
     * @return {Object|undefined} the chat session, if exists
     */
    _getChatSession: function (chatID) {
        return _.find(this._chatSessions, function (chatSession) {
            return chatSession.getID() === chatID;
        });
    },
    /**
     * Get chat session in hidden chat session matching id `chatID`
     *
     * @private
     * @param {integer} chatID
     * @return {Object|undefined} the hidden chat session, if exists
     */
    _getHiddenSession: function (chatID) {
        return _.find(this._displayState.hiddenSessions, function (chatSession) {
            return chatSession.getID() === chatID;
        });
    },
    /**
     * @private
     * @param {Object} session
     * @param {Widget} session.window
     */
    _makeSessionVisible: function (session) {
        utils.swap(this._chatSessions, session, this._chatSessions[this._displayState.nbSlots-1]);
        this._repositionWindows();
        session.window.toggleFold(false);
    },
    /**
     * @private
     * @param {integer} partnerID
     */
    _openDmSession: function (partnerID) {
        this._newChatSession.partnerID = partnerID;
        var dm = this._chatManager.getDmFromPartnerID(partnerID);
        if (!dm) {
            this._chatManager.openAndDetachDm(partnerID);
        } else {
            var dmSession = this._getChatSession(dm.getID());
            if (!dmSession) {
                dm.detach();
            } else {
                this._closeChat(dmSession);
                dm._folded = false; // AKU: FIXME
                this.openChat(dm);
            }
        }
    },
    /**
     * @private
     */
    _repositionHiddenSessionsDropdown: function () {
        // Unfold dropdown to the left if there is enough place
        var $dropdownUL = this._displayState.$hiddenWindowsDropdown.children('ul');
        if (this._displayState.spaceLeft > $dropdownUL.width() + 10) {
            $dropdownUL.addClass('dropdown-menu-right');
        }
    },
    /**
     * @private
     */
    _renderHiddenSessionsDropdown: function () {
        var $dropdown = $(QWeb.render('mail.AbstractConversationWindowsDropdown', {
            sessions: this._displayState.hiddenSessions,
            open: this._displayState.windowsDropdownIsOpen,
            unreadCounter: this._displayState.hiddenUnreadCounter,
            widget: { isMobile: config.device.isMobile },
        }));
        return $dropdown;
    },
    /**
     * @private
     * @param {Object} [options]
     * @param {boolean} [options.removeNewChat]
     */
    _repositionWindows: function (options) {
        var self = this;
        if (options && options.removeNewChat) {
            this._destroyNewChat();
        }
        if (this._displayState.chatWindowsHidden) {
            return;
        }
        this._computeAvailableSlots(this._chatSessions.length);
        var hiddenSessions = [];
        var hiddenUnreadCounter = 0;
        var nbSlots = this._displayState.nbSlots;
        _.each(this._chatSessions, function (session, index) {
            if (index < nbSlots) {
                session.window.$el.css({ right: CHAT_WINDOW_WIDTH*index, bottom: 0 });
                session.window.do_show();
            } else {
                hiddenSessions.push(session);
                hiddenUnreadCounter += session.window.getUnreadCounter();
                session.window.do_hide();
            }
        });
        this._displayState.hiddenSessions = hiddenSessions;
        this._displayState.hiddenUnreadCounter = hiddenUnreadCounter;

        if (this._displayState.$hiddenWindowsDropdown) {
            this._displayState.$hiddenWindowsDropdown.remove();
        }
        if (hiddenSessions.length) {
            this._displayState.$hiddenWindowsDropdown = this._renderHiddenSessionsDropdown();
            var $hiddenWindowsDropdown = this._displayState.$hiddenWindowsDropdown;
            $hiddenWindowsDropdown.css({ right: CHAT_WINDOW_WIDTH * nbSlots, bottom: 0 })
                                    .appendTo($('body'));
            this._repositionHiddenSessionsDropdown();
            this._displayState.windowsDropdownIsOpen = false;

            $hiddenWindowsDropdown.on('click', '.o_conversation_window_header', function (event) {
                var sessionID = $(event.currentTarget).data('session-id');
                var session = self._getHiddenSession(sessionID);
                if (session) {
                    self._makeSessionVisible(session);
                }
            });
            $hiddenWindowsDropdown.on('click', '.o_conversation_window_close', function (event) {
                var sessionID = $(event.currentTarget).closest('.o_conversation_window_header').data('session-id');
                var session = self._getHiddenSession(sessionID);
                if (session) {
                    session.window.on_click_close(event);
                    self._displayState.windowsDropdownIsOpen = true;  // keep the dropdown open
                }
            });
        }
    },
    /**
     * @private
     * @param {mail.model.Message} message
     * @param {boolean} scrollBottom
     */
    _updateSessions: function (message, scrollBottom) {
        var self = this;
        _.each(this._chatSessions, function (session) {
            if (_.contains(message.getConversationIDs(), session.getID())) {
                var conversation = self._chatManager.getConversation(session.getID());
                var messageVisible = !self._displayState.chatWindowsHidden && !session.window.isFolded() &&
                                      !session.window.isHidden() && session.window.threadWidget.isAtBottom();
                if (messageVisible && !session.keepUnread) {
                    conversation.markAsSeen();
                }
                conversation.getMessages()
                    .then(function (messages) {
                        session.window.render(messages);
                        if (scrollBottom && messageVisible) {
                            session.window.threadWidget.scrollToBottom();
                        }
                    });
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {mail.model.Conversation} conversation
     * @param {Object} query
     */
    _onAnyoneListening: function (conversation, query) {
        _.each(this._chatSessions, function (session) {
            if (conversation.getID() === session.getID() && session.window.threadWidget.isAtBottom() && !session.window.isHidden()) {
                query.isDisplayed = true;
            }
        });
    },
    /**
     * @private
     * @param {mail.model.Conversation} conversation
     */
    _onDetachConversation: function (conversation) {
        var chatSession = this._getChatSession(conversation.getID());
        if (!chatSession || chatSession.window.isFolded()) {
            conversation.detach();
        } else if (chatSession.window.isHidden()) {
            this._makeSessionVisible(chatSession);
        } else {
            chatSession.window.focusInput();
        }
    },
    /**
     * @private
     * @param {boolean} open
     */
    _onDiscussOpen: function (open) {
        this._displayState.chatWindowsHidden = open;
        if (open) {
            $('body').addClass('o_no_conversation_window');
        } else {
            $('body').removeClass('o_no_conversation_window');
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
     * @param {integer} messageID
     */
    _onToggleStarStatus: function (messageID) {
        var message = this._chatManager.getMessage(messageID);
        message.toggleStarStatus();
    },
    /**
     * @private
     * @param {integer} channelID
     */
    _onUnsubscribeFromChannel: function (channelID) {
        var self = this;
        _.each(this._chatSessions, function (session) {
            if (channelID === session.getID()) {
                self._closeChat(session);
            }
        });
    },
    /**
     * @private
     * @param {mail.model.Conversation} conversation
     */
    _onUpdateConversationUnreadCounter: function (conversation) {
        var self = this;
        this._displayState.hiddenUnreadCounter = 0;
        _.each(this._chatSessions, function (session) {
            if (conversation.getID() === session.getID()) {
                if (conversation.getUnreadCounter() === 0) {
                    session.keepUnread = false;
                }
            }
            if (session.window.isHidden()) {
                self._displayState.hiddenUnreadCounter += session.window.getUnreadCounter();
            }
        });
        if (this._displayState.$hiddenWindowsDropdown) {
            this._displayState.$hiddenWindowsDropdown.html(this._renderHiddenSessionsDropdown().html());
            this._repositionHiddenSessionsDropdown();
        }
    },
    /**
     * @private
     * @param {mail.model.Conversation} conversation
     */
    _onUpdateDmPresence: function (conversation) {
        _.each(this._chatSessions, function (session) {
            if (conversation.getID() === session.getID()) {
                session.window.updateStatus(conversation.getStatus());
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

});

return ChatWindowManager;

});
