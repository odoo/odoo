odoo.define('mail.store.state', function (require) {
'use strict';

const config = require('web.config');

/**
 * @param {Object} [alteration] used for tests to partially alter state initially
 * @return {Object}
 */
function init(alteration) {
    let state = {
        MESSAGE_FETCH_LIMIT: 30,
        PREVIEW_MSG_MAX_SIZE: 350,
        attachments: {},
        attachmentNextTemporaryId: -1,
        cannedResponses: {},
        /**
         * State slice related to Chat Windows & Chat Window Manager
         */
        chatWindowManager: {
            /**
             * Reference to docked chat window Id (either 'new_message' or a
             * minimized thread local Id) that should be auto-focus. If this
             * value is set and differs from locally value tracked by chat
             * window manager, it should auto-focus the corresponding chat
             * window. For instance, if this value is 'new_message', it should
             * auto-focus the 'new_message' docked chat window.
             */
            autofocusChatWindowLocalId: undefined,
            /**
             * Counter used to determine when an autofocus behaviour should
             * occur. This is necessary in case the
             * autofocusChatWindowLocalId does not change, but we want to
             * autofocus it nonetheless.
             */
            autofocusCounter: 0,
            /**
             * Ordered list of chat windows, from right to left when docked.
             */
            chatWindowLocalIds: [],
            /**
             * Computed data from docked chat windows and their screen position.
             * To be used by the dock chat window manager to show docked chat
             * windows on screen. This property should only be modified by the
             * action `_computeChatWindows`. New object is assigned on
             * changes.
             */
            computed: {
                /**
                 * Amount of visible slots available for chat windows.
                 */
                availableVisibleSlots: 0,
                /**
                 * Data related to the hidden menu.
                 */
                hidden: {
                    /**
                     * List of ordered hidden docked chat windows.
                     */
                    chatWindowLocalIds: [],
                    /**
                     * Whether hidden menu is visible or not
                     */
                    isVisible: false,
                    /**
                     * Offset of hidden menu starting point from the starting
                     * point of dock chat window manager. Makes only sense if
                     * it is visible.
                     */
                    offset: 0,
                },
                /**
                 * Data related to visible chat windows. Index determine order
                 * of docked chat windows.
                 *
                 *  Value:
                 *
                 *  {
                 *      chatWindowLocalId,
                 *      offset,
                 *  }
                 *
                 * Offset is offset of starting point of chat window from starting
                 * point of chat window manager. Chat windows are ordered by
                 * their `chatWindowLocalIds` order.
                 */
                visible: [],
            },
            /**
             * Tracked internal autofocus counter of chat window manager.
             * This is used to dismiss autofocus on chat window manager in
             * case it is mounted and the autofocus counter has not changed.
             */
            notifiedAutofocusCounter: 0,
            /**
             * Stored chat window states (scroll positions, composer text & composer attachments).
             * Useful to restore chat window UI state when showing/hiding home menu.
             * This is necessary because toggling home menu cleans the DOM, so chat windows need
             * re-mount.
             *
             * Format:
             *    {
             *       [chatWindowLocalId]: {
             *           composerAttachmentLocalIds {string[]},
             *           composerTextInputHtmlContent {string},
             *           scrollTop {integer},
             *       },
             *    }
             */
            storedChatWindowStates: {}
        },
        commands: {},
        /**
         * State slice related to Composers.
         * (key: composerId, value: store data of component)
         */
        composers: {},
        currentPartnerLocalId: undefined,
        /**
         * State slice related to Dialogs & Dialog Manager
         */
        dialogManager: {
            /**
             * Ordered list of dialogs data, from bottom to top.
             * Each item is an object with format { Component, id, info },
             * where Component is an owl component class, id is the Id of the
             * dialog, and info is an object with props provided to dialog item.
             */
            dialogs: [],
        },
        /**
         * State slice related to the Discuss app
         */
        discuss: {
            /**
             * active mobile navbar tab, either 'mailbox', 'chat', or 'channel'.
             */
            activeMobileNavbarTabId: 'mailbox',
            /**
             * Current thread set on discuss app
             */
            activeThreadLocalId: null,
            /**
             * Domain of the messages in the thread. Determine the thread cache
             * to use with provided thread local Id.
             */
            domain: [],
            /**
             * Amount of times "mark as read" from the control panel has been
             * clicked by user while discuss app is open. This is used to
             * display rainbow man.
             */
            inboxMarkAsReadCounter: 0,
            /**
             * Whether the discuss app is open or not. Useful to determine
             * whether the discuss or chat window logic should be applied.
             */
            isOpen: false,
            /**
             * The menu_id of discuss app, received on mail/init_messaging and
             * used to open discuss from elsewhere.
             */
            menu_id: null,
            /**
             * Stored state of composers of a thread. Composer state is stored
             * on changing thread, and is recover on re-selecting this thread.
             *
             * - Key: threadLocalId
             * - Value:
             *      {
             *          attachmentLocalIds,
             *          textInputHtmlContent,
             *      }
             */
            storedThreadComposers: {},
            /**
             * Stringified domain. This is computed once in order to avoid
             * making JSON.stringify whenever we need the stringified domain.
             * Stringified domain is used to determine the thread cache local
             * Id, so that components can connect on store to read on thread
             * cache changes.
             */
            stringifiedDomain: '[]',
            /**
             * Targeted thread in the discuss app. Used to autoscroll and have
             * special style on such thread item in desktop (sidebar) or in
             * mobile (mobileNavbarTab, thread preview, mailbox selection, etc.)
             */
            targetThreadCounter: 0,
            targetThreadLocalId: null,
        },
        /**
         * State slice related to global window object dynamic properties.
         *
         * This is useful for components that have some computation relying on
         * those data, like the chat window manager that uses the global window
         * width to determine the chat windows to display on screen.
         */
        globalWindow: {
            innerHeight: window.innerHeight,
            innerWidth: window.innerWidth,
        },
        isMobile: config.device.isMobile,
        isMyselfModerator: false,
        mailFailures: {},
        messages: {},
        /**
         * State slice related to Messaging Menu in the Systray
         */
        messagingMenu: {
            /**
             * Tab selected in the messaging menu.
             * Either 'all', 'chat' or 'channel'.
             */
            activeTabId: 'all',
            /**
             * Determine whether the mobile new message input is visible or not.
             */
            isMobileNewMessageToggled: false,
            /**
             * Determine whether the messaging menu dropdown is open or not.
             */
            isOpen: false,
        },
        moderatedChannelIds: [],
        outOfFocusUnreadMessageCounter: 0,
        partners: {},
        temporaryAttachmentLocalIds: {}, // key: filename, value: temporaryAttachmentLocalId
        threads: {},
        threadCaches: {},
    };
    if (alteration) {
        state = Object.assign(state, alteration);
    }
    return state;
}

return { init };

});
