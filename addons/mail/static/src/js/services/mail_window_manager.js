odoo.define('mail.Manager.Window', function (require) {
"use strict";

var MailManager = require('mail.Manager');
var ThreadWindow = require('mail.ThreadWindow');

var config = require('web.config');
var core = require('web.core');
var utils = require('web.utils');

var QWeb = core.qweb;
var _t = core._t;

/**
 * Mail Window Manager
 *
 * This part of the mail manager is responsible for the management of thread
 * windows.
 */
MailManager.include({
    custom_events: _.extend({}, MailManager.prototype.custom_events, {
        close_blank_thread_window: '_onCloseBlankThreadWindow',
    }),

    // width of 'hidden thread window' dropdown button
    HIDDEN_THREAD_WINDOW_DROPDOWN_BUTTON_WIDTH: 50,
    // where thread windows are appended
    THREAD_WINDOW_APPENDTO: 'body',
    // width of a thread window (+ 5 pixels between windows)
    THREAD_WINDOW_WIDTH: 325 + 5,

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Open the blank thread window (i.e. the thread window without any thread
     * linked to it). Make it if there is no blank thread window yet.
     */
    openBlankThreadWindow: function () {
        var blankThreadWindow = this._getBlankThreadWindow();
        if (!blankThreadWindow) {
            blankThreadWindow = new ThreadWindow(this, null);
            this._addThreadWindow(blankThreadWindow);
            blankThreadWindow.appendTo(this.THREAD_WINDOW_APPENDTO)
                .then(this._repositionThreadWindows.bind(this));
        } else {
            if (blankThreadWindow.isHidden()) {
                this._makeThreadWindowVisible(blankThreadWindow);
            } else if (blankThreadWindow.isFolded()) {
                blankThreadWindow.toggleFold(false);
            }
        }
    },
    /**
     * Open a DM chat in a thread window. This is useful when selecting a DM
     * chatin the blank thread window, so that it replaces it with the DM chat
     * window.
     *
     * @param {integer} partnerID
     */
    openDMChatWindowFromBlankThreadWindow: function (partnerID) {
        var dmChat = this.getDMChatFromPartnerID(partnerID);
        if (!dmChat) {
            this._openAndDetachDMChat(partnerID);
        } else {
            this.openThreadWindow(dmChat.getID());
        }
        this._closeBlankThreadWindow();
    },
    /**
     * Open the thread window if discuss is not opened
     *
     * @override
     * @param {integer|string} threadID
     */
    openThread: function (threadID) {
        if (!this._isDiscussOpen()) {
            var thread = this.getThread(threadID);
            if (thread) {
                thread.detach();
            }
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Open a thread in a thread window
     *
     * @param {integer} threadID a valid thread ID
     * @param {Object} [options]
     * @param {boolean} [options.passively] if set to true, open the thread
     *   window without focusing the input and marking messages as read if it
     *   is not open yet, and do nothing otherwise.
     * @param {boolean} [options.keepFoldState=false] if set to true, keep the
     *   fold state of the thread
     */
    openThreadWindow: function (threadID, options) {
        var self = this;
        options = options || {};
        // valid threadID, therefore no check
        var thread = this.getThread(threadID);
        if (thread.isCreatingWindow) {
            // abort creating a chat window, to prevent open chat window twice.
            // This may happen due to concurrent calls to this method from
            // messaging menu preview click and handling of longpolling chat
            // window state.
            return;
        }
        var threadWindow = this._getThreadWindow(threadID);
        var def = $.when();
        if (!threadWindow) {
            thread.isCreatingWindow = true;
            def = thread.fetchMessages().then(function () {
                threadWindow = self._makeNewThreadWindow(thread, options);
                self._placeNewThreadWindow(threadWindow, options.passively);
                return threadWindow.appendTo($(self.THREAD_WINDOW_APPENDTO));
            }).then(function () {
                self._repositionThreadWindows();
                threadWindow.render();
                threadWindow.scrollToBottom();
                if (
                    !self._areAllThreadWindowsHidden() &&
                    !thread.isFolded() &&
                    !threadWindow.isPassive()
                ) {
                    thread.markAsRead();
                }
            }).fail(function () {
                // thread window could not be open, which may happen due to
                // access error while fetching messages to the document.
                // abort opening the thread window in this case.
                thread.close();
            }).always(function () {
                thread.isCreatingWindow = false;
            });
        }
        def.then(function () {
            threadWindow.updateVisualFoldState();
        });
    },
    /**
     * Called when a thread has its window state that has been changed, so its
     * thread window view should be changed to match the model.
     *
     * @param {integer|string} threadID
     * @param {Object} options option to be applied on opening thread window, if
     *   the thread is detached
     * @param {boolean} [options.passively=false] if set, the window will behave
     *   passively.
     */
    updateThreadWindow: function (threadID, options) {
        var thread = this.getThread(threadID);
        if (thread) {
            if (thread.isDetached()) {
                _.extend(options, { keepFoldState: true });
                this.openThreadWindow(threadID, options);
            } else {
                this._closeThreadWindow(threadID);
            }
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add the thread window such that it will be the left-most visible window.
     * Note that adding a new thread window may decrement the amount of
     * available slots for visible thread windows.
     * For example:
     *
     * - global width of 800px
     * - button width of 100px
     * - thread width of 250px
     *
     * Without button: 3 thread windows (3*250px = 750px < 800px)
     *    With button: 2 thread windows (2*250px + 100px = 600px < 800px)
     *
     * So in order for the thread window to be the left-most visible window,
     * we should compute available slots after insertion of the thread window.
     *
     * @private
     * @param {mail.ThreadWindow} threadWindow
     */
    _addThreadWindow: function (threadWindow) {
        this._threadWindows.push(threadWindow);
        this._computeAvailableSlotsForThreadWindows();
        this._threadWindows.pop();
        this._threadWindows.splice(this._availableSlotsForThreadWindows-1, 0, threadWindow);
    },
    /**
     * States whether all the thread windows are hidden or not.
     * When discuss is open, the thread windows are hidden.
     *
     * @private
     * @returns {boolean}
     */
    _areAllThreadWindowsHidden: function () {
        return $(this.THREAD_WINDOW_APPENDTO).hasClass('o_no_thread_window');
    },
    /**
     * Close the thread window linked to the thread with ID `threadID`.
     * If there is no window linked to this thread, do nothing.
     *
     * @private
     * @param {integer|string} threadID
     */
    _closeThreadWindow: function (threadID) {
        var threadWindow = _.find(this._threadWindows, function (threadWindow) {
            return threadWindow.getID() === threadID;
        });
        if (threadWindow) {
            this._threadWindows = _.without(this._threadWindows, threadWindow);
            this._repositionThreadWindows();
            threadWindow.destroy();
        }
    },
    /**
     * Close the blank thread window.
     */
    _closeBlankThreadWindow: function () {
        var blankThreadWindow = this._getBlankThreadWindow();
        if (blankThreadWindow) {
            this._closeThreadWindow(blankThreadWindow.getID());
        }
    },
    /**
     * Compute the number of available slots to display thread windows on the
     * screen. This is based on the width of the screen, and the width of a
     * single thread window.
     *
     * The available slots attributes are updated as a consequence of this
     * method call.
     *
     * @private
     */
    _computeAvailableSlotsForThreadWindows: function () {
        if (config.device.isMobile) {
            // one thread window full screen in mobile
            this._availableSlotsForThreadWindows = 1;
            return;
        }
        var GLOBAL_WIDTH = this._getGlobalWidth();
        var THREAD_WINDOW_NUM = this._threadWindows.length;
        var availableSlots = Math.floor(GLOBAL_WIDTH/this.THREAD_WINDOW_WIDTH);
        var spaceLeft = GLOBAL_WIDTH - (Math.min(availableSlots, THREAD_WINDOW_NUM)*this.THREAD_WINDOW_WIDTH);
        if (availableSlots < THREAD_WINDOW_NUM && spaceLeft < this.HIDDEN_THREAD_WINDOW_DROPDOWN_BUTTON_WIDTH) {
            // leave at least space for the hidden windows dropdown button
            availableSlots--;
            spaceLeft += this.THREAD_WINDOW_WIDTH;
        }

        this._availableSlotsForThreadWindows = availableSlots;
        this._spaceLeftForThreadWindows = spaceLeft;
    },
    /**
     * Get the blank thread window, which is the special thread window that has
     * no thread linked to it.
     *
     * This is useful in case a DM chat window may replace the blank thread
     * window, when we want to open a DM chat from the blank thread window.
     *
     * @private
     * @returns {mail.ThreadWindow|undefined} the "blank thread" window,
     *   if it exists, otherwise undefined
     */
    _getBlankThreadWindow: function () {
        return _.find(this._threadWindows, function (threadWindow) {
            return threadWindow.getID() === '_blank';
        });
    },
    /**
     * Get the width of the browser, which is useful to determine how many
     * open thread windows are visible or hidden.
     *
     * @private
     * @returns {integer}
     */
    _getGlobalWidth: function () {
        return window.innerWidth;
    },
    /**
     * Get thread window in the hidden windows matching ID `threadID`.
     *
     * Note: hidden windows are open windows that cannot be displayed
     * due to having more thread windows open than available slots for thread
     * windows on the screen. These thread windows are displayed in the hidden
     * thread window dropdown menu.
     *
     * @private
     * @param {integer|string} threadID
     * @returns {mail.ThreadWindow|undefined} the hidden thread window,
     *   if exists
     */
    _getHiddenThreadWindow: function (threadID) {
        return _.find(this._hiddenThreadWindows, function (threadWindow) {
            return threadWindow.getID() === threadID;
        });
    },
    /**
     * Get thread window matching ID `threadID`
     *
     * @private
     * @param {integer} threadID
     * @returns {mail.ThreadWindow|undefined} the thread window, if exists
     */
    _getThreadWindow: function (threadID) {
        return _.find(this._threadWindows, function (threadWindow) {
            return threadWindow.getID() === threadID;
        });
    },
    /**
     * @override
     * @private
     */
    _initializeInternalState: function () {
        this._super.apply(this, arguments);

        this._availableSlotsForThreadWindows = 0;
        this._hiddenThreadWindows = [];
        // used to keep dropdown open when closing thread windows
        this._keepHiddenThreadWindowsDropdownOpen = false;
        this._spaceLeftForThreadWindows = 0;
        this._threadWindows = [];
        // jQuery element for the dropdown of hidden thread windows
        // see _renderHiddenThreadWindowsDropdown
        this._$hiddenThreadWindowsDropdown = null;
    },
    /**
     * @override
     * @private
     */
    _listenOnBuses: function () {
        this._super.apply(this, arguments);
        this._mailBus
            .on('update_message', this, this._onUpdateMessage)
            .on('new_message', this, this._onNewMessage)
            .on('new_channel', this, this._onNewChannel)
            .on('is_thread_bottom_visible', this, this._onIsThreadBottomVisible)
            .on('unsubscribe_from_channel', this, this._onUnsubscribeFromChannel)
            .on('update_thread_unread_counter', this, this._onUpdateThreadUnreadCounter)
            .on('update_dm_presence', this, this._onUpdateDmPresence)
            .on('update_typing_partners', this, this._onTypingPartnersUpdated);

        core.bus.on('resize', this, _.debounce(this._repositionThreadWindows.bind(this), 100));
    },
    /**
     * Make the hidden thread window dropdown menu, that is render it and set
     * event listener on this dropdown menu DOM element.
     *
     * @private
     */
    _makeHiddenThreadWindowsDropdown: function () {
        var self = this;
        if (this._$hiddenThreadWindowsDropdown) {
            this._$hiddenThreadWindowsDropdown.remove();
        }
        if (this._hiddenThreadWindows.length) {
            this._$hiddenThreadWindowsDropdown = this._renderHiddenThreadWindowsDropdown();
            var $hiddenWindowsDropdown = this._$hiddenThreadWindowsDropdown;
            $hiddenWindowsDropdown.css({right: this.THREAD_WINDOW_WIDTH * this._availableSlotsForThreadWindows, bottom: 0 })
                                  .appendTo(this.THREAD_WINDOW_APPENDTO);
            this._repositionHiddenWindowsDropdown();
            this._keepHiddenThreadWindowsDropdownOpen = false;

            $hiddenWindowsDropdown
                .on('click', '.o_thread_window_header', function (ev) {
                    var threadID = $(ev.currentTarget).data('thread-id');
                    var threadWindow = self._getHiddenThreadWindow(threadID);
                    if (threadWindow) {
                        self._makeThreadWindowVisible(threadWindow);
                    }
                })
                .on('click', '.o_thread_window_close', function (ev) {
                    var threadID = $(ev.currentTarget).closest('.o_thread_window_header')
                                                      .data('thread-id');
                    var threadWindow = self._getHiddenThreadWindow(threadID);
                    if (threadWindow) {
                        threadWindow.close();
                        // keep the dropdown open
                        self._keepHiddenThreadWindowsDropdownOpen = true;
                    }
                });
        }
    },
    /**
     * Make a new thread window linked to a thread.
     *
     * @private
     * @param {mail.model.Thread} thread
     * @param {Object} options
     * @param {boolean} [options.passively=false]
     */
    _makeNewThreadWindow: function (thread, options) {
        return new ThreadWindow(this, thread, _.extend(options, {
            autofocus: !options.passively,
        }));
    },
    /**
     * Make an open thread window fully visible on screen.
     *
     * This method assumes that the thread window is hidden (i.e. in the hidden
     * dropdown menu). To make it visible, it swap the position of this thread
     * window with the last thread window that is visible (i.e. the left-most
     * visible thread window).
     *
     * @private
     * @param {mail.ThreadWindow} threadWindow
     */
    _makeThreadWindowVisible: function (threadWindow) {
        utils.swap(
            this._threadWindows,
            threadWindow,
            this._threadWindows[this._availableSlotsForThreadWindows-1]
        );
        this._repositionThreadWindows();
        threadWindow.toggleFold(false);
    },
    /**
     * Open and detach the DM chat in a thread window.
     *
     * This method assumes that no such DM chat exists locally, so it is kind
     * of a "create DM chat and open DM chat window" operation
     *
     * @private
     * @param {integer} partnerID
     * @returns {$.Promise<integer>} resolved with ID of the DM chat
     */
    _openAndDetachDMChat: function (partnerID) {
        return this._rpc({
            model: 'mail.channel',
            method: 'channel_get_and_minimize',
            args: [[partnerID]],
        })
        .then(this._addChannel.bind(this));
    },
    /**
     * On opening a new thread window, place it with other thread windows:
     *
     *  - if it has been open with the blank thread window, replace the blank
     *    thread window with this one
     *  - if it has been open passively, simply but it after all windows
     *  - otherwise, make it the left-most visible thread window
     *
     * @param {mail.ThreadWindow} threadWindow a thread window that is linked
     *   to a thread (this must not be the blank thread window)
     * @param {boolean} [passively=false] if set, if the thread window does not
     *   replace the blank thread window, it is add at the tail of the list of
     *   thread windows, which might be put in the thread window hidden dropdown
     *   menu if there are not enough space on the screen.
     */
    _placeNewThreadWindow: function (threadWindow, passively) {
        var thread = this.getThread(threadWindow.getID());
        // replace the blank thread window?
        // the thread window should be a DM
        var blankThreadWindow = this._getBlankThreadWindow();
        if (
            blankThreadWindow &&
            thread.getType() === 'dm_chat' &&
            thread.getDirectPartnerID() === blankThreadWindow.directPartnerID
        ) {
            // the window takes the place of the 'blank' thread window
            var index = _.indexOf(this._threadWindows, blankThreadWindow);
            this._threadWindows[index] = threadWindow;
            blankThreadWindow.destroy();
        } else if (passively) {
            // simply insert the window to the left
            this._threadWindows.push(threadWindow);
        } else {
            // add window such that it is visible
            this._addThreadWindow(threadWindow);
        }
    },
    /**
     * Unfold dropdown to the left if there is enough space on the screen.
     *
     * @private
     */
    _repositionHiddenWindowsDropdown: function () {
        var $dropdownUL = this._$hiddenThreadWindowsDropdown.children('ul');
        if (this._spaceLeftForThreadWindows > $dropdownUL.width() + 10) {
            $dropdownUL.addClass('dropdown-menu-right');
        }
    },
    /**
     * Load the template of the hidden thread window dropdown
     *
     * @private
     * @returns {jQuery.Element}
     */
    _renderHiddenThreadWindowsDropdown: function () {
        var $dropdown = $(QWeb.render('mail.HiddenThreadWindowsDropdown', {
            threadWindows: this._hiddenThreadWindows,
            open: this._keepHiddenThreadWindowsDropdownOpen,
            unreadCounter: this._hiddenThreadWindowsUnreadCounter,
            widget: {
                isMobile: function () {
                    return config.device.isMobile;
                },
            },
        }));
        return $dropdown;
    },
    /**
     * Reposition the thread windows that should be hidden on the screen.
     * Thread windows that have an index equal or greater than `index` in the
     * attribute `threadWindows` should be hidden. Those thread windows are put
     * in the hidden thread window dropdown menu.
     *
     * This function assumes that we have already computed the available slots.
     *
     * @private
     */
    _repositionHiddenThreadWindows: function () {
        var hiddenWindows = [];
        var hiddenUnreadCounter = 0;
        var index = this._availableSlotsForThreadWindows;
        while (index < this._threadWindows.length) {
            var threadWindow = this._threadWindows[index];
            hiddenWindows.push(threadWindow);
            hiddenUnreadCounter += threadWindow.getUnreadCounter();
            threadWindow.do_hide();
            index++;
        }
        this._hiddenThreadWindows = hiddenWindows;
        this._hiddenThreadWindowsUnreadCounter = hiddenUnreadCounter;

        this._makeHiddenThreadWindowsDropdown();
    },
    /**
     * Reposition the thread windows, based on the size of the screen:
     *
     *  - display thread windows by increasing order of index in
     *    `_threadWindows` attribute, from right to left on the screen
     *  - if there is no enough space to show all windows at once, display
     *    a dropdown menu for hidden windows.
     *
     * This method should be called whenever there is a change of state of a
     * thread in a window. Also, when this method is called, all the windows
     * are visible and stacked in the top-left corner of the screen.
     *
     * @private
     */
    _repositionThreadWindows: function () {
        this._computeAvailableSlotsForThreadWindows();

        this._repositionVisibleThreadWindows();
        this._repositionHiddenThreadWindows();
    },
    /**
     * Reposition the thread windows that should be visible on the screen.
     *
     * This function assumes that we have already computed the available slots.
     *
     * @private
     */
    _repositionVisibleThreadWindows: function () {
        var index = 0;
        while (
            index < this._availableSlotsForThreadWindows &&
            index < this._threadWindows.length
        ) {
            var threadWindow = this._threadWindows[index];
            var cssProps = {bottom: 0};
            cssProps[_t.database.parameters.direction === 'rtl' ? 'left' : 'right'] = this.THREAD_WINDOW_WIDTH*index;
            threadWindow.$el.css(cssProps);
            threadWindow.do_show();
            index++;
        }
    },
    /**
     * Update thread windows state of threads that have `message`.
     * This is either a new message or an updated message.
     *
     * @private
     * @param {mail.model.Message} message
     * @param {Object} options
     * @param {boolean} [options.keepBottom=false] if set, thread windows with
     *   this message should scroll to the bottom if their bottoms are currently
     *   visible.
     * @param {boolean} [options.passively=false] if set, thread windows with
     *   this message become passive, so that they are marked as read only when
     *   the focus is on the thread window.
     */
    _updateThreadWindowsFromMessage: function (message, options) {
        _.each(this._threadWindows, function (threadWindow) {
            if (_.contains(message.getThreadIDs(), threadWindow.getID())) {
                threadWindow.update(options);
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when manually closing the blank thread window.
     *
     * @private
     */
    _onCloseBlankThreadWindow: function () {
        this._closeBlankThreadWindow();
    },
    /**
     * @private
     * @param {boolean} open
     */
    _onDiscussOpen: function (open) {
        this._super.apply(this, arguments);

        if (open) {
            $(this.THREAD_WINDOW_APPENDTO).addClass('o_no_thread_window');
        } else {
            $(this.THREAD_WINDOW_APPENDTO).removeClass('o_no_thread_window');
            this._repositionThreadWindows();
        }
    },
    /**
     * Called when someone asks window manager whether the bottom of `thread` is
     * visible or not. An object `query` is provided in order to reponse on the
     * key `isVisible`.
     *
     * @private
     * @param {mail.model.Thread} thread
     * @param {Object} query
     * @param {boolean} query.isVisible write on it
     */
    _onIsThreadBottomVisible: function (thread, query) {
        _.each(this._threadWindows, function (threadWindow) {
            if (
                thread.getID() === threadWindow.getID() &&
                threadWindow.isAtBottom() &&
                !threadWindow.isHidden()
            ) {
                query.isVisible = true;
            }
        });
    },
    /**
     * Show or hide window of this channel when a new channel is added.
     *
     * @private
     * @param {mail.model.Channel} channel
     */
    _onNewChannel: function (channel) {
        if (channel.isDetached()) {
            this.openThreadWindow(channel.getID(), { keepFoldState: true, passively: true });
        } else {
            this._closeThreadWindow(channel.getID());
        }
    },
    /**
     * Update thread window containing this message when a new message is added.
     *
     * @private
     * @param {Object} message
     */
    _onNewMessage: function (message) {
        this._updateThreadWindowsFromMessage(message, { keepBottom: true, passively: true });
    },
    /**
     * @private
     * @param {integer|string} threadID
     */
    _onTypingPartnersUpdated: function (threadID) {
        var threadWindow = this._getThreadWindow(threadID);
        if (!threadWindow) {
            return;
        }
        var thread = this.getThread(threadID);
        if (thread.isChannel()) {
            // call getMentionpartnerSuggestions in order to correctly fetch members
            thread.getMentionPartnerSuggestions().then(function () {
                threadWindow.renderTypingNotificationBar();
            });
        }
    },
    /**
     * Close the thread window when unsusbscribe from a channel.
     *
     * @private
     * @param {integer} channelID
     */
    _onUnsubscribeFromChannel: function (channelID) {
        this._closeThreadWindow(channelID);
    },
    /**
     * Called when a thread has its unread counter that has changed.
     * The unread counter on the thread windows should be updated.
     *
     * @private
     * @param {mail.model.Thread} thread
     */
    _onUpdateThreadUnreadCounter: function (thread) {
        var self = this;
        this._hiddenThreadWindowsUnreadCounter = 0;
        _.each(this._threadWindows, function (threadWindow) {
            if (thread.getID() === threadWindow.getID()) {
                threadWindow.renderHeader();
                if (thread.getUnreadCounter() === 0) {
                    threadWindow.removePassive();
                }
            }
            if (threadWindow.isHidden()) {
                self._hiddenThreadWindowsUnreadCounter += threadWindow.getUnreadCounter();
            }
        });
        if (this._$hiddenThreadWindowsDropdown) {
            this._$hiddenThreadWindowsDropdown.html(
                this._renderHiddenThreadWindowsDropdown().html());
            this._repositionHiddenWindowsDropdown();
        }
    },
    /**
     * Called when there is a change of the im status of the user linked to
     * DMs. The header of the thread window should be updated accordingly,
     * in order to display the correct new im status of this users.
     *
     * @private
     * @param {mail.model.Thread} thread
     */
    _onUpdateDmPresence: function (thread) {
        _.each(this._threadWindows, function (threadWindow) {
            if (thread.getID() === threadWindow.getID()) {
                threadWindow.renderHeader();
            }
        });
    },
    /**
     * Called when a message has been updated.
     *
     * @private
     * @param {Object} message
     */
    _onUpdateMessage: function (message) {
        this._updateThreadWindowsFromMessage(message, { keepBottom: false });
    },

});

return MailManager;

});
