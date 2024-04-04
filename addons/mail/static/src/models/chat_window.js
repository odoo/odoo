/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'ChatWindow',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * Close this chat window.
         *
         * @param {Object} [param0={}]
         * @param {boolean} [param0.notifyServer]
         */
        close({ notifyServer } = {}) {
            if (notifyServer === undefined) {
                notifyServer = !this.messaging.device.isSmall;
            }
            if (this.messaging.device.isSmall && !this.messaging.discuss.discussView) {
                // If we are in mobile and discuss is not open, it means the
                // chat window was opened from the messaging menu. In that
                // case it should be re-opened to simulate it was always
                // there in the background.
                this.messaging.messagingMenu.update({ isOpen: true });
            }
            // Flux specific: 'closed' fold state should only be saved on the
            // server when manually closing the chat window. Delete at destroy
            // or sync from server value for example should not save the value.
            if (this.thread && notifyServer && !this.messaging.currentGuest) {
                this.thread.notifyFoldStateToServer('closed');
            }
            if (this.exists()) {
                this.delete();
            }
        },
        expand() {
            if (this.thread) {
                this.thread.open({ expanded: true });
            }
        },
        /**
         * Programmatically auto-focus an existing chat window.
         */
        focus() {
            if (!this.thread) {
                this.update({ isDoFocus: true });
            }
            if (this.threadView && this.threadView.composerView) {
                this.threadView.composerView.update({ doFocus: true });
            }
        },
        focusNextVisibleUnfoldedChatWindow() {
            const nextVisibleUnfoldedChatWindow = this._getNextVisibleUnfoldedChatWindow();
            if (nextVisibleUnfoldedChatWindow) {
                nextVisibleUnfoldedChatWindow.focus();
            }
        },
        focusPreviousVisibleUnfoldedChatWindow() {
            const previousVisibleUnfoldedChatWindow =
                this._getNextVisibleUnfoldedChatWindow({ reverse: true });
            if (previousVisibleUnfoldedChatWindow) {
                previousVisibleUnfoldedChatWindow.focus();
            }
        },
        /**
         * @param {Object} [param0={}]
         * @param {boolean} [param0.notifyServer]
         */
        fold({ notifyServer } = {}) {
            if (notifyServer === undefined) {
                notifyServer = !this.messaging.device.isSmall;
            }
            this.update({ isFolded: true });
            // Flux specific: manually folding the chat window should save the
            // new state on the server.
            if (this.thread && notifyServer && !this.messaging.currentGuest) {
                this.thread.notifyFoldStateToServer('folded');
            }
        },
        /**
         * Makes this chat window active, which consists of making it visible,
         * unfolding it, and focusing it if the user isn't on a mobile device.
         *
         * @param {Object} [options]
         */
        makeActive(options) {
            this.makeVisible();
            this.unfold(options);
            if ((options && options.focus !== undefined) ? options.focus : !this.messaging.device.isMobileDevice) {
                this.focus();
            }
        },
        /**
         * Makes this chat window visible by swapping it with the last visible
         * chat window, or do nothing if it is already visible.
         */
        makeVisible() {
            if (this.isVisible) {
                return;
            }
            const lastVisible = this.manager.lastVisible;
            this.manager.swap(this, lastVisible);
        },
        /**
         * Called when selecting an item in the autocomplete input of the
         * 'new_message' chat window.
         *
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        async onAutocompleteSelect(ev, ui) {
            const chat = await this.messaging.getChat({ partnerId: ui.item.id });
            if (!chat) {
                return;
            }
            this.messaging.chatWindowManager.openThread(chat.thread, {
                makeActive: true,
                replaceNewMessage: true,
            });
        },
        /**
         * Called when typing in the autocomplete input of the 'new_message' chat
         * window.
         *
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        onAutocompleteSource(req, res) {
            this.messaging.models['Partner'].imSearch({
                callback: (partners) => {
                    const suggestions = partners.map(partner => {
                        return {
                            id: partner.id,
                            value: partner.nameOrDisplayName,
                            label: partner.nameOrDisplayName,
                        };
                    });
                    res(_.sortBy(suggestions, 'label'));
                },
                keyword: _.escape(req.term),
                limit: 10,
            });
        },
        onClickFromChatWindowHiddenMenu() {
            this.makeActive();
            this.manager.closeHiddenMenu();
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickCamera(ev) {
            ev.stopPropagation();
            if (this.thread.hasPendingRtcRequest) {
                return;
            }
            await this.thread.toggleCall({ startWithVideo: true });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickClose(ev) {
            ev.stopPropagation();
            if (!this.exists()) {
                return;
            }
            this.close();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickExpand(ev) {
            if (!this.exists()) {
                return;
            }
            ev.stopPropagation();
            this.expand();
        },
        /**
         * Called when clicking on header of chat window. Usually folds the chat
         * window.
         */
        onClickHeader(ev) {
            if (!this.exists() || this.messaging.device.isSmall) {
                return;
            }
            if (this.isFolded) {
                this.unfold();
                this.focus();
            } else {
                this.saveThreadScrollTop();
                this.fold();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickHideCallSettingsMenu(ev) {
            markEventHandled(ev, 'ChatWindow.onClickCommand');
            this.update({ isCallSettingsMenuOpen: false });
        },
        /**
         * Handles click on the "stop adding users" button.
         *
         * @param {MouseEvent} ev
         */
        onClickHideInviteForm(ev) {
            markEventHandled(ev, 'ChatWindow.onClickCommand');
            this.update({ channelInvitationForm: clear() });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickHideMemberList(ev) {
            markEventHandled(ev, 'ChatWindow.onClickHideMemberList');
            this.update({ isMemberListOpened: false });
            if (this.threadViewer.threadView) {
                this.threadViewer.threadView.addComponentHint('member-list-hidden');
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickPhone(ev) {
            ev.stopPropagation();
            if (this.thread.hasPendingRtcRequest) {
                return;
            }
            await this.thread.toggleCall();
        },
        /**
         * Handles click on the "add users" button.
         *
         * @param {MouseEvent} ev
         */
        onClickShowInviteForm(ev) {
            markEventHandled(ev, 'ChatWindow.onClickCommand');
            this.update({
                channelInvitationForm: {
                    doFocusOnSearchInput: true,
                },
                isMemberListOpened: false,
            });
            if (!this.messaging.isCurrentUserGuest) {
                this.channelInvitationForm.searchPartnersToInvite();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickShowCallSettingsMenu(ev) {
            markEventHandled(ev, 'ChatWindow.onClickCommand');
            this.update({
                isCallSettingsMenuOpen: true,
                isMemberListOpened: false,
            });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickShowMemberList(ev) {
            markEventHandled(ev, 'ChatWindow.onClickShowMemberList');
            this.update({
                channelInvitationForm: clear(),
                isCallSettingsMenuOpen: false,
                isMemberListOpened: true,
            });
        },
        /**
         * @param {Event} ev
         */
        onFocusInNewMessageFormInput(ev) {
            if (this.exists()) {
                this.update({ isFocused: true });
            }
        },
        /**
         * Focus out the chat window.
         */
        onFocusout() {
            if (!this.exists()) {
                // ignore focus out due to record being deleted
                return;
            }
            this.update({ isFocused: false });
        },
        /**
         * @param {KeyboardEvent} ev
         */
        onKeydown(ev) {
            if (!this.exists()) {
                return;
            }
            switch (ev.key) {
                case 'Tab':
                    ev.preventDefault();
                    if (ev.shiftKey) {
                        this.focusPreviousVisibleUnfoldedChatWindow();
                    } else {
                        this.focusNextVisibleUnfoldedChatWindow();
                    }
                    break;
                case 'Escape':
                    if (isEventHandled(ev, 'ComposerTextInput.closeSuggestions')) {
                        break;
                    }
                    if (isEventHandled(ev, 'Composer.closeEmojisPopover')) {
                        break;
                    }
                    ev.preventDefault();
                    this.focusNextVisibleUnfoldedChatWindow();
                    this.close();
                    break;
            }
        },
        /**
         * Save the scroll positions of the chat window in the store.
         * This is useful in order to remount chat windows and keep previous
         * scroll positions. This is necessary because when toggling on/off
         * home menu, the chat windows have to be remade from scratch.
         */
        saveThreadScrollTop() {
            if (
                !this.threadView ||
                !this.threadView.messageListView ||
                !this.threadView.messageListView.component ||
                !this.threadViewer
            ) {
                return;
            }
            if (
                this.threadViewer.threadView &&
                this.threadViewer.threadView.componentHintList.length > 0
            ) {
                // the current scroll position is likely incorrect due to the
                // presence of hints to adjust it
                return;
            }
            this.threadViewer.saveThreadCacheScrollHeightAsInitial(
                this.threadView.messageListView.getScrollableElement().scrollHeight
            );
            this.threadViewer.saveThreadCacheScrollPositionsAsInitial(
                this.threadView.messageListView.getScrollableElement().scrollTop
            );
        },
        /**
         * @param {Object} [param0={}]
         * @param {boolean} [param0.notifyServer]
         */
        unfold({ notifyServer } = {}) {
            if (notifyServer === undefined) {
                notifyServer = !this.messaging.device.isSmall;
            }
            this.update({ isFolded: false });
            // Flux specific: manually opening the chat window should save the
            // new state on the server.
            if (this.thread && notifyServer && !this.messaging.currentGuest) {
                this.thread.notifyFoldStateToServer('open');
            }
        },
        /**
         * Cycles to the next possible visible and unfolded chat window starting
         * from the `currentChatWindow`, following the natural order based on the
         * current text direction, and with the possibility to `reverse` based on
         * the given parameter.
         *
         * @private
         * @param {Object} [param0={}]
         * @param {boolean} [param0.reverse=false]
         * @returns {ChatWindow|undefined}
         */
        _getNextVisibleUnfoldedChatWindow({ reverse = false } = {}) {
            const orderedVisible = this.manager.allOrderedVisible;
            /**
             * Return index of next visible chat window of a given visible chat
             * window index. The direction of "next" chat window depends on
             * `reverse` option.
             *
             * @param {integer} index
             * @returns {integer}
             */
            const _getNextIndex = index => {
                const directionOffset = reverse ? 1 : -1;
                let nextIndex = index + directionOffset;
                if (nextIndex > orderedVisible.length - 1) {
                    nextIndex = 0;
                }
                if (nextIndex < 0) {
                    nextIndex = orderedVisible.length - 1;
                }
                return nextIndex;
            };

            const currentIndex = orderedVisible.findIndex(visible => visible === this);
            let nextIndex = _getNextIndex(currentIndex);
            let nextToFocus = orderedVisible[nextIndex];
            while (nextToFocus.isFolded) {
                nextIndex = _getNextIndex(nextIndex);
                nextToFocus = orderedVisible[nextIndex];
            }
            return nextToFocus;
        },
    },
    fields: {
        /**
         * Model for the component with the controls for RTC related settings.
         */
        callSettingsMenu: one('CallSettingsMenu', {
            compute() {
                if (this.isCallSettingsMenuOpen) {
                    return {};
                }
                return clear();
            },
            inverse: 'chatWindowOwner',
        }),
        /**
         * Determines the channel invitation form displayed by this chat window
         * (if any). Only makes sense if hasInviteFeature is true.
         */
        channelInvitationForm: one('ChannelInvitationForm', {
            inverse: 'chatWindow',
        }),
        channelMemberListView: one('ChannelMemberListView', {
            compute() {
                if (this.thread && this.thread.hasMemberListFeature && this.isMemberListOpened) {
                    return {};
                }
                return clear();
            },
            inverse: 'chatWindowOwner',
        }),
        chatWindowHeaderView: one('ChatWindowHeaderView', {
            default: {},
            inverse: 'chatWindowOwner',
        }),
        componentStyle: attr({
            compute() {
                const textDirection = this.messaging.locale.textDirection;
                const offsetFrom = textDirection === 'rtl' ? 'left' : 'right';
                const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
                return `${offsetFrom}: ${this.visibleOffset}px; ${oppositeFrom}: auto`;
            },
        }),
        /**
         * Determines whether the buttons to start a RTC call should be displayed.
         */
        hasCallButtons: attr({
            compute() {
                if (!this.thread || !this.thread.channel) {
                    return clear();
                }
                return this.thread.rtcSessions.length === 0 && ['channel', 'chat', 'group'].includes(this.thread.channel.channel_type);
            },
            default: false,
        }),
        hasCloseAsBackButton: attr({
            compute() {
                if (this.isVisible && this.messaging.device.isSmall) {
                    return true;
                }
                return clear();
            },
            default: false,
        }),
        /**
         * States whether this chat window has the invite feature.
         */
        hasInviteFeature: attr({
            compute() {
                return Boolean(
                    this.thread && this.thread.hasInviteFeature &&
                    this.messaging && this.messaging.device && this.messaging.device.isSmall
                );
            },
        }),
        /**
         * Determines whether "new message form" should be displayed.
         */
        hasNewMessageForm: attr({
            compute() {
                return this.isVisible && !this.isFolded && !this.thread;
            },
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            compute() {
                return this.isVisible && !this.isFolded && !!this.thread && !this.isMemberListOpened && !this.channelInvitationForm && !this.isCallSettingsMenuOpen;
            },
        }),
        isCallSettingsMenuOpen: attr({
            default: false,
        }),
        /**
         * Determine whether the chat window should be programmatically
         * focused by observed component of chat window. Those components
         * are responsible to unmark this record afterwards, otherwise
         * any re-render will programmatically set focus again!
         */
        isDoFocus: attr({
            default: false,
        }),
        isExpandable: attr({
            compute() {
                if (this.isVisible && !this.messaging.device.isSmall && this.thread) {
                    return true;
                }
                return clear();
            },
            default: false,
        }),
        /**
         * States whether `this` is focused. Useful for visual clue.
         */
        isFocused: attr({
            default: false,
        }),
        /**
         * Determines whether `this` is folded.
         */
        isFolded: attr({
            default: false,
        }),
        isFullscreen: attr({
            compute() {
                if (this.isVisible && this.messaging.device.isSmall) {
                    return true;
                }
                return clear();
            },
            default: false,
        }),
        /**
         * Determines whether the member list of this chat window is opened.
         * Only makes sense if this thread hasMemberListFeature is true.
         */
        isMemberListOpened: attr({
            default: false,
        }),
        /**
         * States whether `this` is visible or not. Should be considered
         * read-only. Setting this value manually will not make it visible.
         * @see `makeVisible`
         */
        isVisible: attr({
            compute() {
                if (!this.manager) {
                    return false;
                }
                return this.manager.allOrderedVisible.includes(this);
            },
        }),
        manager: one('ChatWindowManager', {
            inverse: 'chatWindows',
            readonly: true,
        }),
        managerAsNewMessage: one('ChatWindowManager', {
            identifying: true,
            inverse: 'newMessageChatWindow',
        }),
        name: attr({
            compute() {
                if (this.thread) {
                    return this.thread.displayName;
                }
                return this.env._t("New message");
            },
        }),
        newMessageAutocompleteInputView: one('AutocompleteInputView', {
            compute() {
                if (this.hasNewMessageForm) {
                    return {};
                }
                return clear();
            },
            inverse: 'chatWindowOwnerAsNewMessage',
        }),
        /**
         * The content of placeholder for the autocomplete input of
         * 'new_message' chat window.
         */
        newMessageFormInputPlaceholder: attr({
            compute() {
                return this.env._t("Search user...");
            },
        }),
        /**
         * Determines the `Thread` that should be displayed by `this`.
         * If no `Thread` is linked, `this` is considered "new message".
         */
        thread: one('Thread', {
            identifying: true,
            inverse: 'chatWindow',
        }),
        /**
         * States the `ThreadView` displaying `this.thread`.
         */
        threadView: one('ThreadView', {
            related: 'threadViewer.threadView',
        }),
        /**
         * Determines the `ThreadViewer` managing the display of `this.thread`.
         */
        threadViewer: one('ThreadViewer', {
            compute() {
                return {
                    compact: true,
                    hasThreadView: this.hasThreadView,
                    thread: this.thread ? this.thread : clear(),
                };
            },
            inverse: 'chatWindow',
            required: true,
        }),
        /**
         * This field handle the "order" (index) of the visible chatWindow inside the UI.
         *
         * Using LTR, the right-most chat window has index 0, and the number is incrementing from right to left.
         * Using RTL, the left-most chat window has index 0, and the number is incrementing from left to right.
         */
        visibleIndex: attr({
            compute() {
                if (!this.manager) {
                    return clear();
                }
                const visible = this.manager.visual.visible;
                const index = visible.findIndex(visible => visible.chatWindow === this);
                if (index === -1) {
                    return clear();
                }
                return index;
            },
        }),
        visibleOffset: attr({
            compute() {
                if (!this.manager) {
                    return 0;
                }
                const visible = this.manager.visual.visible;
                const index = visible.findIndex(visible => visible.chatWindow === this);
                if (index === -1) {
                    return 0;
                }
                return visible[index].offset;
            },
        }),
    },
});
