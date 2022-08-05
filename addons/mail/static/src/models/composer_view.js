/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, link } from '@mail/model/model_field_command';
import { addLink, escapeAndCompactTextContent, parseAndTransform } from '@mail/js/utils';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

import { escape, sprintf } from '@web/core/utils/strings';
import { url } from '@web/core/utils/urls';

registerModel({
    name: 'ComposerView',
    identifyingMode: 'xor',
    lifecycleHooks: {
        _created() {
            document.addEventListener('click', this.onClickCaptureGlobal, true);
        },
        _willDelete() {
            document.removeEventListener('click', this.onClickCaptureGlobal, true);
        },
    },
    recordMethods: {
        /**
         * Closes the suggestion list.
         */
        closeSuggestions() {
            this.update({ suggestionDelimiterPosition: clear() });
        },
        /**
         * Returns whether the given html element is inside this composer view,
         * including whether it's inside the emoji popover when active.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        contains(element) {
            // emoji popover is outside but should be considered inside
            if (this.emojisPopoverView && this.emojisPopoverView.contains(element)) {
                return true;
            }
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        /**
         * Hides the composer, which only makes sense if the composer is
         * currently used as a Discuss Inbox reply composer or as message
         * editing.
         */
        discard() {
            if (this.messageViewInEditing) {
                this.messageViewInEditing.stopEditing();
                return;
            }
            if (this.threadView && this.threadView.replyingToMessageView) {
                const { threadView } = this;
                if (this.threadView.thread === this.messaging.inbox.thread) {
                    this.delete();
                }
                threadView.update({ replyingToMessageView: clear() });
            }
        },
        /**
         * Called when current partner is inserting some input in composer.
         * Useful to notify current partner is currently typing something in the
         * composer of this thread to all other members.
         */
        handleCurrentPartnerIsTyping() {
            if (!this.composer.thread || !this.composer.thread.channel) {
                return; // not supported for non-thread composer (eg. messaging editing)
            }
            if (
                this.suggestionModelName === 'ChannelCommand' ||
                this._getCommandFromText(this.composer.textInputContent)
            ) {
                return;
            }
            if (this.composer.thread.typingMembers.includes(this.composer.thread.channel.memberOfCurrentUser)) {
                this.composer.thread.refreshCurrentPartnerIsTyping();
            } else {
                this.composer.thread.registerCurrentPartnerIsTyping();
            }
        },
        /**
         * Inserts text content in text input based on selection.
         *
         * @param {string} content
         */
        insertIntoTextInput(content) {
            const partA = this.composer.textInputContent.slice(0, this.composer.textInputCursorStart);
            const partB = this.composer.textInputContent.slice(
                this.composer.textInputCursorEnd,
                this.composer.textInputContent.length
            );
            let suggestionDelimiterPosition = this.suggestionDelimiterPosition;
            if (
                suggestionDelimiterPosition !== undefined &&
                suggestionDelimiterPosition >= this.composer.textInputCursorStart
            ) {
                suggestionDelimiterPosition = suggestionDelimiterPosition + content.length;
            }
            this.composer.update({
                textInputContent: partA + content + partB,
                textInputCursorEnd: this.composer.textInputCursorStart + content.length,
                textInputCursorStart: this.composer.textInputCursorStart + content.length,
            });
            for (const composerView of this.composer.composerViews) {
                composerView.update({ hasToRestoreContent: true });
            }
            this.update({ suggestionDelimiterPosition });
        },
        /**
         * Inserts the active suggestion at the current cursor position.
         */
        insertSuggestion() {
            const cursorPosition = this.composer.textInputCursorStart;
            let textLeft = this.composer.textInputContent.substring(
                0,
                this.suggestionDelimiterPosition + 1
            );
            let textRight = this.composer.textInputContent.substring(
                cursorPosition,
                this.composer.textInputContent.length
            );
            if (this.suggestionDelimiter === ':') {
                textLeft = this.composer.textInputContent.substring(
                    0,
                    this.suggestionDelimiterPosition
                );
                textRight = this.composer.textInputContent.substring(
                    cursorPosition,
                    this.composer.textInputContent.length
                );
            }
            const recordReplacement = this.composerSuggestionListView.activeSuggestionView.mentionText;
            const updateData = {
                textInputContent: textLeft + recordReplacement + ' ' + textRight,
                textInputCursorEnd: textLeft.length + recordReplacement.length + 1,
                textInputCursorStart: textLeft.length + recordReplacement.length + 1,
            };
            // Specific cases for channel and partner mentions: the message with
            // the mention will appear in the target channel, or be notified to
            // the target partner.
            if (this.composerSuggestionListView.activeSuggestionView.suggestable.thread) {
                Object.assign(updateData, { rawMentionedChannels: link(this.composerSuggestionListView.activeSuggestionView.suggestable.thread) });
            }
            if (this.composerSuggestionListView.activeSuggestionView.suggestable.partner) {
                Object.assign(updateData, { rawMentionedPartners: link(this.composerSuggestionListView.activeSuggestionView.suggestable.partner) });
            }
            this.composer.update(updateData);
            for (const composerView of this.composer.composerViews) {
                composerView.update({ hasToRestoreContent: true });
            }
        },
        /**
         * Called when clicking on attachment button.
         */
        onClickAddAttachment() {
            this.fileUploader.openBrowserFileUploader();
            if (!this.messaging.device.isMobileDevice) {
                this.update({ doFocus: true });
            }
        },
        /**
         * Handles click on the emojis button.
         */
        onClickButtonEmojis() {
            if (!this.emojisPopoverView) {
                this.update({ emojisPopoverView: {} });
            } else {
                this.update({ emojisPopoverView: clear() });
            }
        },
        /**
         * Handles click on the cancel link.
         *
         * @param {MouseEvent} ev
         */
        onClickCancelLink(ev) {
            ev.preventDefault();
            if (this.exists()) {
                this.discard();
            }
        },
        /**
         * Discards the composer when clicking away.
         *
         * @private
         * @param {MouseEvent} ev
         */
        async onClickCaptureGlobal(ev) {
            if (this.contains(ev.target)) {
                return;
            }
            // Let event be handled by bubbling handlers first
            await new Promise(this.messaging.browser.setTimeout);
            if (isEventHandled(ev, 'MessageActionList.replyTo')) {
                return;
            }
            if (this.exists()) {
                this.discard();
            }
        },
        /**
         * Called when clicking on "discard" button.
         *
         * @param {MouseEvent} ev
         */
        onClickDiscard(ev) {
            this.discard();
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickEmoji(ev) {
            this.saveStateInStore();
            this.insertIntoTextInput(ev.currentTarget.dataset.codepoints);
            if (!this.messaging.device.isMobileDevice) {
                this.update({ doFocus: true });
            }
            this.update({ emojisPopoverView: clear() });
        },
        /**
         * Called when clicking on "expand" button.
         */
        onClickFullComposer() {
            this.openFullComposer();
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickReplyingToMessage(ev) {
            this.threadView.replyingToMessageView.update({ doHighlight: true });
        },
        /**
         * Handles click on the save link.
         *
         * @param {MouseEvent} ev
         */
        onClickSaveLink(ev) {
            ev.preventDefault();
            this.sendMessage();
        },
        /**
         * Called when clicking on "send" button.
         */
        onClickSend() {
            this.sendMessage();
            this.update({ doFocus: true });
        },
        /**
         * Handles click on the "stop replying" button.
         *
         * @param {MouseEvent} ev
         */
        onClickStopReplying(ev) {
            this.threadView.update({
                replyingToMessageView: clear(),
            });
        },
        onClickTextarea() {
            if (!this.exists()) {
                return;
            }
            // clicking might change the cursor position
            this.saveStateInStore();
        },
        onFocusinTextarea() {
            if (!this.exists()) {
                return;
            }
            this.update({ isFocused: true });
        },
        onFocusoutTextarea() {
            if (!this.exists()) {
                return;
            }
            this.saveStateInStore();
            this.update({ isFocused: false });
        },
        onInputTextarea() {
            if (!this.exists()) {
                return;
            }
            this.saveStateInStore();
            if (this.textareaLastInputValue !== this.textareaRef.el.value) {
                this.handleCurrentPartnerIsTyping();
            }
            this.update({ textareaLastInputValue: this.textareaRef.el.value });
            this.updateTextInputHeight();
        },
        /**
         * @param {KeyboardEvent} ev
         */
        onKeydown(ev) {
            if (ev.key === 'Escape') {
                if (isEventHandled(ev, 'ComposerTextInput.closeSuggestions')) {
                    return;
                }
                if (isEventHandled(ev, 'Composer.closeEmojisPopover')) {
                    return;
                }
                ev.preventDefault();
                this.discard();
            }
        },
        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        onKeydownButtonEmojis(ev) {
            if (ev.key === 'Escape' && this.emojisPopoverView) {
                this.update({
                    doFocus: true,
                    emojisPopoverView: clear(),
                });
                markEventHandled(ev, 'Composer.closeEmojisPopover');
            }
        },
        /**
         * @param {KeyboardEvent} ev
         */
        onKeydownTextarea(ev) {
            if (!this.exists()) {
                return;
            }
            switch (ev.key) {
                case 'Escape':
                    if (this.hasSuggestions) {
                        ev.preventDefault();
                        this.closeSuggestions();
                        markEventHandled(ev, 'ComposerTextInput.closeSuggestions');
                    }
                    break;
                // UP, DOWN, TAB: prevent moving cursor if navigation in mention suggestions
                case 'ArrowUp':
                case 'PageUp':
                case 'ArrowDown':
                case 'PageDown':
                case 'Home':
                case 'End':
                case 'Tab':
                    if (this.hasSuggestions) {
                        // We use preventDefault here to avoid keys native actions but actions are handled in keyUp
                        ev.preventDefault();
                    }
                    break;
                // ENTER: submit the message only if the dropdown mention proposition is not displayed
                case 'Enter':
                    this.onKeydownTextareaEnter(ev);
                    break;
            }
        },
        /**
         * @param {KeyboardEvent} ev
         */
        onKeydownTextareaEnter(ev) {
            if (!this.exists()) {
                return;
            }
            if (this.hasSuggestions) {
                ev.preventDefault();
                return;
            }
            if (
                this.sendShortcuts.includes('ctrl-enter') &&
                !ev.altKey &&
                ev.ctrlKey &&
                !ev.metaKey &&
                !ev.shiftKey
            ) {
                this.sendMessage();
                ev.preventDefault();
                return;
            }
            if (
                this.sendShortcuts.includes('enter') &&
                !ev.altKey &&
                !ev.ctrlKey &&
                !ev.metaKey &&
                !ev.shiftKey
            ) {
                this.sendMessage();
                ev.preventDefault();
                return;
            }
            if (
                this.sendShortcuts.includes('meta-enter') &&
                !ev.altKey &&
                !ev.ctrlKey &&
                ev.metaKey &&
                !ev.shiftKey
            ) {
                this.sendMessage();
                ev.preventDefault();
                return;
            }
        },
        /**
          * Key events management is performed in a Keyup to avoid intempestive RPC calls
          *
          * @param {KeyboardEvent} ev
          */
        onKeyupTextarea(ev) {
            if (!this.exists()) {
                return;
            }
            switch (ev.key) {
                case 'Escape':
                    // already handled in _onKeydownTextarea, break to avoid default
                    break;
                // ENTER, HOME, END, UP, DOWN, PAGE UP, PAGE DOWN, TAB: check if navigation in mention suggestions
                case 'Enter':
                    if (this.hasSuggestions) {
                        this.insertSuggestion();
                        this.closeSuggestions();
                        this.update({ doFocus: true });
                    }
                    break;
                case 'ArrowUp':
                case 'PageUp':
                    if (ev.key === 'ArrowUp' && !this.hasSuggestions && !this.composer.textInputContent && this.threadView) {
                        this.threadView.startEditingLastMessageFromCurrentUser();
                        break;
                    }
                    if (this.composerSuggestionListView) {
                        this.composerSuggestionListView.setPreviousSuggestionViewActive();
                        this.composerSuggestionListView.update({ hasToScrollToActiveSuggestionView: true });
                    }
                    break;
                case 'ArrowDown':
                case 'PageDown':
                    if (ev.key === 'ArrowDown' && !this.hasSuggestions && !this.composer.textInputContent && this.threadView) {
                        this.threadView.startEditingLastMessageFromCurrentUser();
                        break;
                    }
                    if (this.composerSuggestionListView) {
                        this.composerSuggestionListView.setNextSuggestionViewActive();
                        this.composerSuggestionListView.update({ hasToScrollToActiveSuggestionView: true });
                    }
                    break;
                case 'Home':
                    if (this.composerSuggestionListView) {
                        this.composerSuggestionListView.setFirstSuggestionViewActive();
                        this.composerSuggestionListView.update({ hasToScrollToActiveSuggestionView: true });
                    }
                    break;
                case 'End':
                    if (this.composerSuggestionListView) {
                        this.composerSuggestionListView.setLastSuggestionViewActive();
                        this.composerSuggestionListView.update({ hasToScrollToActiveSuggestionView: true });
                    }
                    break;
                case 'Tab':
                    if (this.composerSuggestionListView) {
                        if (ev.shiftKey) {
                            this.composerSuggestionListView.setPreviousSuggestionViewActive();
                            this.composerSuggestionListView.update({ hasToScrollToActiveSuggestionView: true });
                        } else {
                            this.composerSuggestionListView.setNextSuggestionViewActive();
                            this.composerSuggestionListView.update({ hasToScrollToActiveSuggestionView: true });
                        }
                    }
                    break;
                case 'Alt':
                case 'AltGraph':
                case 'CapsLock':
                case 'Control':
                case 'Fn':
                case 'FnLock':
                case 'Hyper':
                case 'Meta':
                case 'NumLock':
                case 'ScrollLock':
                case 'Shift':
                case 'ShiftSuper':
                case 'Symbol':
                case 'SymbolLock':
                    // prevent modifier keys from resetting the suggestion state
                    break;
                // Otherwise, check if a mention is typed
                default:
                    this.saveStateInStore();
            }
        },
        /**
         * @param {ClipboardEvent} ev
         */
        async onPasteTextInput(ev) {
            if (!ev.clipboardData || !ev.clipboardData.files) {
                return;
            }
            await this.fileUploader.uploadFiles(ev.clipboardData.files);
        },
        /**
         * Open the full composer modal.
         */
        async openFullComposer() {
            const attachmentIds = this.composer.attachments.map(attachment => attachment.id);
            const context = {
                default_attachment_ids: attachmentIds,
                default_body: escapeAndCompactTextContent(this.composer.textInputContent),
                default_is_log: this.composer.isLog,
                default_model: this.composer.activeThread.model,
                default_partner_ids: this.composer.recipients.map(partner => partner.id),
                default_res_id: this.composer.activeThread.id,
                mail_post_autofollow: this.composer.activeThread.hasWriteAccess,
            };

            const action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: context,
            };
            const composer = this.composer;
            const options = {
                onClose: () => {
                    if (!composer.exists()) {
                        return;
                    }
                    composer._reset();
                    if (composer.activeThread) {
                        composer.activeThread.fetchData(['messages']);
                    }
                },
            };
            await this.env.services.action.doAction(action, options);
        },
        /**
         * Post a message in provided composer's thread based on current composer fields values.
         */
        async postMessage() {
            const composer = this.composer;
            const postData = this._getMessageData();
            const params = {
                'post_data': postData,
                'thread_id': composer.thread.id,
                'thread_model': composer.thread.model,
            };
            try {
                composer.update({ isPostingMessage: true });
                if (composer.thread.model === 'mail.channel') {
                    Object.assign(postData, {
                        subtype_xmlid: 'mail.mt_comment',
                    });
                } else {
                    Object.assign(postData, {
                        subtype_xmlid: composer.isLog ? 'mail.mt_note' : 'mail.mt_comment',
                    });
                    if (!composer.isLog) {
                        params.context = { mail_post_autofollow: this.composer.activeThread.hasWriteAccess };
                    }
                }
                if (this.threadView && this.threadView.replyingToMessageView && this.threadView.thread !== this.messaging.inbox.thread) {
                    postData.parent_id = this.threadView.replyingToMessageView.message.id;
                }
                const { threadView = {} } = this;
                const chatter = this.chatter;
                const { thread: chatterThread } = this.chatter || {};
                const { thread: threadViewThread } = threadView;
                // Keep a reference to messaging: composer could be
                // unmounted while awaiting the prc promise. In this
                // case, this would be undefined.
                const messaging = this.messaging;
                const messageData = await this.messaging.rpc({ route: `/mail/message/post`, params });
                if (!messaging.exists()) {
                    return;
                }
                const message = messaging.models['Message'].insert(
                    messaging.models['Message'].convertData(messageData)
                );
                if (this.messaging.hasLinkPreviewFeature && !message.isBodyEmpty) {
                    this.messaging.rpc({
                        route: `/mail/link_preview`,
                        params: {
                            message_id: message.id
                        }
                    }, { shadow: true });
                }
                for (const threadView of message.originThread.threadViews) {
                    // Reset auto scroll to be able to see the newly posted message.
                    threadView.update({ hasAutoScrollOnMessageReceived: true });
                    threadView.addComponentHint('message-posted', { message });
                }
                if (chatter && chatter.exists() && chatter.hasParentReloadOnMessagePosted) {
                    chatter.reloadParentView();
                }
                if (chatterThread) {
                    if (this.exists()) {
                        this.delete();
                    }
                    if (chatterThread.exists()) {
                        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
                        chatterThread.fetchData(['followers', 'messages', 'suggestedRecipients']);
                    }
                }
                if (threadViewThread) {
                    if (threadViewThread === messaging.inbox.thread) {
                        messaging.notify({
                            message: sprintf(messaging.env._t(`Message posted on "%s"`), message.originThread.displayName),
                            type: 'info',
                        });
                        if (this.exists()) {
                            this.delete();
                        }
                    }
                    if (threadView && threadView.exists()) {
                        threadView.update({ replyingToMessageView: clear() });
                    }
                }
                if (composer.exists()) {
                    composer._reset();
                }
            } finally {
                if (composer.exists()) {
                    composer.update({ isPostingMessage: false });
                }
            }
        },
        /**
         * Saves the composer text input state in store
         */
        saveStateInStore() {
            this.composer.update({
                textInputContent: this.textareaRef.el.value,
                textInputCursorEnd: this.textareaRef.el.selectionEnd,
                textInputCursorStart: this.textareaRef.el.selectionStart,
                textInputSelectionDirection: this.textareaRef.el.selectionDirection,
            });
        },
        /**
         * Send a message in the composer on related thread.
         *
         * Sending of the message could be aborted if it cannot be posted like if there are attachments
         * currently uploading or if there is no text content and no attachments.
         */
        async sendMessage() {
            if (!this.composer.canPostMessage) {
                if (this.composer.hasUploadingAttachment) {
                    this.messaging.notify({
                        message: this.env._t("Please wait while the file is uploading."),
                        type: 'warning',
                    });
                }
                return;
            }
            if (this.messageViewInEditing) {
                this.updateMessage();
                return;
            }
            if (this.composer.thread.channel) {
                const command = this._getCommandFromText(this.composer.textInputContent);
                if (command) {
                    await command.execute({ channel: this.composer.thread, body: this.composer.textInputContent });
                    if (this.composer.exists()) {
                        this.composer._reset();
                    }
                    return;
                }
                this.composer.thread.unregisterCurrentPartnerIsTyping({ immediateNotify: true });
            }
            this.postMessage();
        },
        /**
         * Updates the textarea height of text input.
         */
        updateTextInputHeight() {
            this.mirroredTextareaRef.el.value = this.composer.textInputContent;
            this.textareaRef.el.style.height = this.mirroredTextareaRef.el.scrollHeight + 'px';
        },
        /**
         * Update a posted message when the message is ready.
         */
        async updateMessage() {
            const composer = this.composer;
            if (!composer.textInputContent) {
                this.messageViewInEditing.messageActionList.update({ deleteConfirmDialog: {} });
                return;
            }
            const escapedAndCompactContent = escapeAndCompactTextContent(composer.textInputContent);
            let body = escapedAndCompactContent.replace(/&nbsp;/g, ' ').trim();
            body = this._generateMentionsLinks(body);
            body = parseAndTransform(body, addLink);
            body = this._generateEmojisOnHtml(body);
            let data = {
                body: body,
                attachment_ids: composer.attachments.concat(this.messageViewInEditing.message.attachments).map(attachment => attachment.id),
            };
            try {
                composer.update({ isPostingMessage: true });
                const messageViewInEditing = this.messageViewInEditing;
                await messageViewInEditing.message.updateContent(data);
                if (messageViewInEditing.exists()) {
                    messageViewInEditing.stopEditing();
                }
            } finally {
                if (composer.exists()) {
                    composer.update({ isPostingMessage: false });
                }
            }
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeAttachmentList() {
            return (this.composer && this.composer.attachments.length > 0)
                ? {}
                : clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeComposerSuggestedRecipientListView() {
            if (this.hasHeader && this.hasFollowers && !this.composer.isLog) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeComposer() {
            if (this.threadView) {
                // When replying to a message, always use the composer from that message's thread
                if (this.threadView && this.threadView.replyingToMessageView) {
                    return this.threadView.replyingToMessageView.message.originThread.composer;
                }
                if (this.threadView.thread && this.threadView.thread.composer) {
                    return this.threadView.thread.composer;
                }
            }
            if (this.messageViewInEditing && this.messageViewInEditing.composerForEditing) {
                return this.messageViewInEditing.composerForEditing;
            }
            if (this.chatter && this.chatter.thread && this.chatter.thread.composer) {
                return this.chatter.thread.composer;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeCurrentPartnerAvatar() {
            if (this.messaging.currentUser) {
                return url('/web/image', {
                    field: 'avatar_128',
                    id: this.messaging.currentUser.id,
                    model: 'res.users',
                });
            }
            return '/web/static/img/user_menu_avatar.png';
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeDropZoneView() {
            if (this.useDragVisibleDropZone.isVisible) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasDiscardButton() {
            if (this.messageViewInEditing) {
                return false;
            }
            if (this.messaging.device.isSmall) {
                return false;
            }
            if (!this.threadView) {
                return clear();
            }
            if (this.threadView.threadViewer.discuss) {
                return this.threadView.threadViewer.discuss.activeThread === this.messaging.inbox.thread;
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasCurrentPartnerAvatar() {
            if (this.messageViewInEditing) {
                return false;
            }
            if (!this.threadView) {
                return clear();
            }
            if (this.threadView.threadViewer.chatWindow) {
                return false;
            }
            if (this.threadView.threadViewer.discuss) {
                return !this.messaging.device.isSmall;
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasFollowers() {
            if (this.chatter) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasFooter() {
            return Boolean(
                this.hasThreadTyping ||
                this.composer.attachments.length > 0 ||
                this.messageViewInEditing ||
                !this.isCompact
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasHeader() {
            return Boolean(
                (this.hasThreadName && this.composer.thread) ||
                (this.hasFollowers && !this.composer.isLog) ||
                (this.threadView && this.threadView.replyingToMessageView)
            );
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasMentionSuggestionsBelowPosition() {
            if (this.chatter) {
                return true;
            }
            if (this.messageViewInEditing) {
                return false;
            }
            return clear();
        },
        /**
         * @private
         * @return {boolean}
         */
        _computeHasSuggestions() {
            return this.mainSuggestions.length > 0 || this.extraSuggestions.length > 0;
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasThreadTyping() {
            if (this.threadView) {
                return this.threadView.hasComposerThreadTyping;
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsCompact() {
            if (this.chatter) {
                return false;
            }
            if (this.messageViewInEditing) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInDiscuss() {
            return Boolean(
                (this.threadView && (this.threadView.threadViewer.discuss || this.threadView.threadViewer.discussPublicView)) ||
                (this.messageViewInEditing && this.messageViewInEditing.isInDiscuss)
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInChatWindow() {
            return Boolean(
                (this.threadView && this.threadView.threadViewer.chatWindow) ||
                (this.messageViewInEditing && this.messageViewInEditing.isInChatWindow)
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInChatter() {
            return Boolean(
                (this.threadView && this.threadView.threadViewer.chatter) ||
                (this.messageViewInEditing && this.messageViewInEditing.isInChatter)
            );
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasSendButton() {
            if (this.messageViewInEditing) {
                return false;
            }
            if (this.threadView && this.threadView.threadViewer.chatWindow) {
                return this.messaging.device.isSmall;
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsExpandable() {
            if (this.chatter) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasThreadName() {
            if (this.threadView) {
                return this.threadView.hasComposerThreadName;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeSendButtonText() {
            if (
                this.composer &&
                this.composer.isLog &&
                this.composer.activeThread &&
                this.composer.activeThread.model !== 'mail.channel'
            ) {
                return this.env._t("Log");
            }
            return this.env._t("Send");
        },
        /**
         * @private
         * @returns {string[]}
         */
         _computeSendShortcuts() {
            if (this.chatter) {
                return ['ctrl-enter', 'meta-enter'];
            }
            if (this.messageViewInEditing) {
                return ['enter'];
            }
            if (this.threadView) {
                if (!this.messaging.device) {
                    return clear();
                }
                // Actually in mobile there is a send button, so we need there 'enter' to allow new
                // line. Hence, we want to use a different shortcut 'ctrl/meta enter' to send for
                // small screen size with a non-mailing channel. Here send will be done on clicking
                // the button or using the 'ctrl/meta enter' shortcut.
                if (
                    this.messaging.device.isSmall ||
                    (
                        this.messaging.discuss.threadView === this.threadView &&
                        this.messaging.discuss.activeThread === this.messaging.inbox.thread
                    )
                ) {
                    return ['ctrl-enter', 'meta-enter'];
                }
                return ['enter'];
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionDelimiter() {
            if (
                !this.composer ||
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionDelimiterPosition >= this.composer.textInputContent.length
            ) {
                return clear();
            }
            return this.composer.textInputContent[this.suggestionDelimiterPosition];
        },
        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionModelName() {
            switch (this.suggestionDelimiter) {
                case '@':
                    return 'Partner';
                case ':':
                    return 'CannedResponse';
                case '/':
                    return 'ChannelCommand';
                case '#':
                    return 'Thread';
                default:
                    return clear();
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionSearchTerm() {
            if (
                !this.composer ||
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionDelimiterPosition >= this.composer.textInputCursorStart
            ) {
                return clear();
            }
            return this.composer.textInputContent.substring(this.suggestionDelimiterPosition + 1, this.composer.textInputCursorStart);
        },
        /**
         * Executes the given async function, only when the last function
         * executed by this method terminates. If there is already a pending
         * function it is replaced by the new one. This ensures the result of
         * these function come in the same order as the call order, and it also
         * allows to skip obsolete intermediate calls.
         *
         * @private
         * @param {function} func
         */
        async _executeOrQueueFunction(func) {
            if (this.hasMentionRpcInProgress) {
                this.update({ nextMentionRpcFunction: func });
                return;
            }
            this.update({
                hasMentionRpcInProgress: true,
                nextMentionRpcFunction: clear(),
            });
            await func();
            if (this.exists()) {
                this.update({ hasMentionRpcInProgress: false });
                if (this.nextMentionRpcFunction) {
                    this._executeOrQueueFunction(this.nextMentionRpcFunction);
                }
            }
        },
        /**
         * @private
         * @param {string} htmlString
         * @returns {string}
         */
        _generateEmojisOnHtml(htmlString) {
            for (const emoji of this.messaging.emojiRegistry.allEmojis) {
                for (const source of emoji.sources) {
                    const escapedSource = String(source).replace(
                        /([.*+?=^!:${}()|[\]/\\])/g,
                        '\\$1');
                    const regexp = new RegExp(
                        '(\\s|^)(' + escapedSource + ')(?=\\s|$)',
                        'g');
                    htmlString = htmlString.replace(regexp, '$1' + emoji.codepoints);
                }
            }
            return htmlString;
        },
        /**
         *
         * Generates the html link related to the mentioned partner
         *
         * @private
         * @param {string} body
         * @returns {string}
         */
        _generateMentionsLinks(body) {
            // List of mention data to insert in the body.
            // Useful to do the final replace after parsing to avoid using the
            // same tag twice if two different mentions have the same name.
            const mentions = [];
            for (const partner of this.composer.mentionedPartners) {
                const placeholder = `@-mention-partner-${partner.id}`;
                const text = `@${escape(partner.name)}`;
                mentions.push({
                    class: 'o_mail_redirect',
                    id: partner.id,
                    model: 'res.partner',
                    placeholder,
                    text,
                });
                body = body.replace(text, placeholder);
            }
            for (const channel of this.composer.mentionedChannels) {
                const placeholder = `#-mention-channel-${channel.id}`;
                const text = `#${escape(channel.name)}`;
                mentions.push({
                    class: 'o_channel_redirect',
                    id: channel.id,
                    model: 'mail.channel',
                    placeholder,
                    text,
                });
                body = body.replace(text, placeholder);
            }
            const baseHREF = url('/web');
            for (const mention of mentions) {
                const href = `href='${baseHREF}#model=${mention.model}&id=${mention.id}'`;
                const attClass = `class='${mention.class}'`;
                const dataOeId = `data-oe-id='${mention.id}'`;
                const dataOeModel = `data-oe-model='${mention.model}'`;
                const target = `target='_blank'`;
                const link = `<a ${href} ${attClass} ${dataOeId} ${dataOeModel} ${target}>${mention.text}</a>`;
                body = body.replace(mention.placeholder, link);
            }
            return body;
        },
        /**
         * @private
         * @param {string} content html content
         * @returns {ChannelCommand|undefined} command, if any in the content
         */
        _getCommandFromText(content) {
            if (content.startsWith('/')) {
                const firstWord = content.substring(1).split(/\s/)[0];
                return this.messaging.commands.find(command => {
                    if (command.name !== firstWord) {
                        return false;
                    }
                    if (command.channel_types) {
                        return Boolean(this.composer.thread.channel) && command.channel_types.includes(this.composer.thread.channel.channel_type);
                    }
                    return true;
                });
            }
            return undefined;
        },
        /**
         * Gather data for message post.
         *
         * @private
         * @returns {Object}
         */
        _getMessageData() {
            const escapedAndCompactContent = escapeAndCompactTextContent(this.composer.textInputContent);
            let body = escapedAndCompactContent.replace(/&nbsp;/g, ' ').trim();
            // This message will be received from the mail composer as html content
            // subtype but the urls will not be linkified. If the mail composer
            // takes the responsibility to linkify the urls we end up with double
            // linkification a bit everywhere. Ideally we want to keep the content
            // as text internally and only make html enrichment at display time but
            // the current design makes this quite hard to do.
            body = this._generateMentionsLinks(body);
            body = parseAndTransform(body, addLink);
            body = this._generateEmojisOnHtml(body);
            return {
                attachment_ids: this.composer.attachments.map(attachment => attachment.id),
                body,
                message_type: 'comment',
                partner_ids: this.composer.recipients.map(partner => partner.id),
            };
        },
        /**
         * Handles change of this composer. Useful to reset the state of the
         * composer text input.
         */
        _onChangeComposer() {
            this.update({ hasToRestoreContent: true });
        },
        /**
         * @private
         */
        _onChangeDetectSuggestionDelimiterPosition() {
            if (!this.composer) {
                return;
            }
            if (this.composer.textInputCursorStart !== this.composer.textInputCursorEnd) {
                // avoid interfering with multi-char selection
                return this.update({ suggestionDelimiterPosition: clear() });
            }
            const candidatePositions = [];
            // keep the current delimiter if it is still valid
            if (
                this.suggestionDelimiterPosition !== undefined &&
                this.suggestionDelimiterPosition < this.composer.textInputCursorStart
            ) {
                candidatePositions.push(this.suggestionDelimiterPosition);
            }
            // consider the char before the current cursor position if the
            // current delimiter is no longer valid (or if there is none)
            if (this.composer.textInputCursorStart > 0) {
                candidatePositions.push(this.composer.textInputCursorStart - 1);
            }
            const suggestionDelimiters = ['@', ':', '#', '/'];
            for (const candidatePosition of candidatePositions) {
                if (
                    candidatePosition < 0 ||
                    candidatePosition >= this.composer.textInputContent.length
                ) {
                    continue;
                }
                const candidateChar = this.composer.textInputContent[candidatePosition];
                if (candidateChar === '/' && candidatePosition !== 0) {
                    continue;
                }
                if (!suggestionDelimiters.includes(candidateChar)) {
                    continue;
                }
                const charBeforeCandidate = this.composer.textInputContent[candidatePosition - 1];
                if (charBeforeCandidate && !/\s/.test(charBeforeCandidate)) {
                    continue;
                }
                this.update({ suggestionDelimiterPosition: candidatePosition });
                return;
            }
            return this.update({ suggestionDelimiterPosition: clear() });
        },
        /**
         * Updates the suggestion state based on the currently saved composer
         * state (in particular content and cursor position).
         *
         * @private
         */
        _onChangeUpdateSuggestionList() {
            if (this.messaging.isCurrentUserGuest) {
                return;
            }
            // Update the suggestion list immediately for a reactive UX...
            this._updateSuggestionList();
            // ...and then update it again after the server returned data.
            this._executeOrQueueFunction(async () => {
                if (
                    !this.exists() ||
                    this.suggestionDelimiterPosition === undefined ||
                    this.suggestionSearchTerm === undefined ||
                    !this.suggestionModelName
                ) {
                    return; // ignore obsolete call
                }
                const model = this.messaging.models[this.suggestionModelName];
                const searchTerm = this.suggestionSearchTerm;
                await model.fetchSuggestions(searchTerm, { thread: this.composer.activeThread });
                if (!this.exists()) {
                    return;
                }
                this._updateSuggestionList();
                if (
                    this.suggestionSearchTerm &&
                    this.suggestionSearchTerm === searchTerm &&
                    this.suggestionModelName &&
                    this.messaging.models[this.suggestionModelName] === model &&
                    !this.hasSuggestions
                ) {
                    this.closeSuggestions();
                }
            });
        },
        /**
         * Updates the current suggestion list. This method should be called
         * whenever the UI has to be refreshed following change in state.
         *
         * This method should ideally be a compute, but its dependencies are
         * currently too complex to express due to accessing plenty of fields
         * from all records of dynamic models.
         *
         * @private
         */
        _updateSuggestionList() {
            if (
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionSearchTerm === undefined ||
                !this.suggestionModelName
            ) {
                return;
            }
            const model = this.messaging.models[this.suggestionModelName];
            const [
                mainSuggestedRecords,
                extraSuggestedRecords = [],
            ] = model.searchSuggestions(this.suggestionSearchTerm, { thread: this.composer.activeThread });
            const sortFunction = model.getSuggestionSortFunction(this.suggestionSearchTerm, { thread: this.composer.activeThread });
            mainSuggestedRecords.sort(sortFunction);
            extraSuggestedRecords.sort(sortFunction);
            // arbitrary limit to avoid displaying too many elements at once
            // ideally a load more mechanism should be introduced
            const limit = 8;
            mainSuggestedRecords.length = Math.min(mainSuggestedRecords.length, limit);
            extraSuggestedRecords.length = Math.min(extraSuggestedRecords.length, limit - mainSuggestedRecords.length);
            this.update({
                extraSuggestions: extraSuggestedRecords.map(record => record.suggestable),
                mainSuggestions: mainSuggestedRecords.map(record => record.suggestable),
            });
            if (this.composerSuggestionListView) {
                this.composerSuggestionListView.update({ hasToScrollToActiveSuggestionView: true });
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeComposerSuggestionListView() {
            if (this.hasSuggestions) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         */
        _onSuggestionDelimiterPositionChanged() {
            if (this.suggestionDelimiterPosition === undefined) {
                this.update({
                    extraSuggestions: clear(),
                    mainSuggestions: clear(),
                });
            }
        },
    },
    fields: {
        /**
         * Determines the attachment list that will be used to display the attachments.
         */
        attachmentList: one('AttachmentList', {
            compute: '_computeAttachmentList',
            inverse: 'composerViewOwner',
            isCausal: true,
        }),
        /**
         * States the ref to the html node of the emojis button.
         */
        buttonEmojisRef: attr(),
        /**
         * States the chatter which this composer allows editing (if any).
         */
        chatter: one('Chatter', {
            identifying: true,
            inverse: 'composerView',
        }),
        /**
         * States the OWL component of this composer view.
         */
        component: attr(),
        /**
         * States the composer state that is displayed by this composer view.
         */
        composer: one('Composer', {
            compute: '_computeComposer',
            inverse: 'composerViews',
            required: true,
        }),
        composerSuggestedRecipientListView: one('ComposerSuggestedRecipientListView', {
            compute: '_computeComposerSuggestedRecipientListView',
            inverse: 'composerViewOwner',
            isCausal: true,
        }),
        composerSuggestionListView: one('ComposerSuggestionListView', {
            compute: '_computeComposerSuggestionListView',
            inverse: 'composerViewOwner',
            isCausal: true,
        }),
        /**
         * Current partner image URL.
         */
        currentPartnerAvatar: attr({
            compute: '_computeCurrentPartnerAvatar',
        }),
        /**
         * Determines whether this composer should be focused at next render.
         */
        doFocus: attr(),
        dropZoneView: one('DropZoneView', {
            compute: '_computeDropZoneView',
            inverse: 'composerViewOwner',
            isCausal: true,
        }),
        /**
         * Determines the emojis popover that is active on this composer view.
         */
        emojisPopoverView: one('PopoverView', {
            inverse: 'composerViewOwnerAsEmoji',
            isCausal: true,
        }),
        extraSuggestions: many('ComposerSuggestable'),
        fileUploader: one('FileUploader', {
            default: {},
            inverse: 'composerView',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        hasCurrentPartnerAvatar: attr({
            default: true,
            compute: '_computeHasCurrentPartnerAvatar',
        }),
        hasDiscardButton: attr({
            compute: '_computeHasDiscardButton',
            default: false,
        }),
        hasFollowers: attr({
            compute: '_computeHasFollowers',
            default: false,
        }),
        /**
         * Determines whether composer should display a footer.
         */
        hasFooter: attr({
            compute: '_computeHasFooter',
        }),
        /**
         * Determine whether the composer should display a header.
         */
        hasHeader: attr({
            compute: '_computeHasHeader',
        }),
        /**
         * Determines whether there is a mention RPC currently in progress.
         * Useful to queue a new call if there is already one pending.
         */
        hasMentionRpcInProgress: attr({
            default: false,
        }),
        hasMentionSuggestionsBelowPosition: attr({
            compute: '_computeHasMentionSuggestionsBelowPosition',
            default: false,
        }),
        hasSendButton: attr({
            compute: '_computeHasSendButton',
            default: true,
        }),
        /**
         * States whether there is any result currently found for the current
         * suggestion delimiter and search term, if applicable.
         */
        hasSuggestions: attr({
            compute: '_computeHasSuggestions',
            default: false,
        }),
        hasThreadName: attr({
            compute: '_computeHasThreadName',
            default: false,
        }),
        hasThreadTyping: attr({
            compute: '_computeHasThreadTyping',
            default: false,
        }),
        /**
         * Determines whether the content of this composer should be restored in
         * this view. Useful to avoid restoring the state when its change was
         * from a user action, in particular to prevent the cursor from jumping
         * to its previous position after the user clicked on the textarea while
         * it didn't have the focus anymore.
         */
        hasToRestoreContent: attr({
            default: false,
        }),
        isCompact: attr({
            compute: '_computeIsCompact',
            default: true,
        }),
        isExpandable: attr({
            compute: '_computeIsExpandable',
            default: false,
        }),
        isFocused: attr({
            default: false,
        }),
        /**
         * Determines if we are in the Discuss view.
         */
        isInDiscuss: attr({
            compute: '_computeIsInDiscuss',
        }),
        /**
         * Determines if we are in the ChatWindow view.
         */
        isInChatWindow: attr({
            compute: '_computeIsInChatWindow',
        }),
        /**
         * Determines if we are in the Chatter view.
         */
        isInChatter: attr({
            compute: '_computeIsInChatter',
        }),
        /**
         * Last content of textarea from input event. Useful to determine
         * whether the current partner is typing something.
         */
        textareaLastInputValue: attr({
            default: "",
        }),
        mainSuggestions: many('ComposerSuggestable'),
        /**
         * States the message view on which this composer allows editing (if any).
         */
        messageViewInEditing: one('MessageView', {
            identifying: true,
            inverse: 'composerViewInEditing',
        }),
        /**
         * This is the invisible textarea used to compute the composer height
         * based on the text content. We need it to downsize the textarea
         * properly without flicker.
         */
        mirroredTextareaRef: attr(),
        /**
         * Determines the next function to execute after the current mention
         * RPC is done, if any.
         */
        nextMentionRpcFunction: attr(),
        /**
         * Determines the label on the send button of this composer view.
         */
        sendButtonText: attr({
            compute: '_computeSendButtonText',
        }),
        /**
         * Keyboard shortcuts from text input to send message.
         * The format is an array of string that can contain 'enter',
         * 'ctrl-enter', and/or 'meta-enter'.
         */
        sendShortcuts: attr({
            compute: '_computeSendShortcuts',
            default: [],
        }),
        /**
         * States which type of suggestion is currently in progress, if any.
         * The value of this field contains the magic char that corresponds to
         * the suggestion currently in progress, and it must be one of these:
         * canned responses (:), channels (#), commands (/) and partners (@)
         */
        suggestionDelimiter: attr({
            compute: '_computeSuggestionDelimiter',
        }),
        /**
         * States the position inside textInputContent of the suggestion
         * delimiter currently in consideration. Useful if the delimiter char
         * appears multiple times in the content.
         * Note: the position is 0 based so it's important to compare to
         * `undefined` when checking for the absence of a value.
         */
        suggestionDelimiterPosition: attr(),
        /**
         * States the target model name of the suggestion currently in progress,
         * if any.
         */
        suggestionModelName: attr({
            compute: '_computeSuggestionModelName',
        }),
        /**
         * States the search term to use for suggestions (if any).
         */
        suggestionSearchTerm: attr({
            compute: '_computeSuggestionSearchTerm',
        }),
        /**
         * Reference of the textarea. Useful to set height, selection and content.
         */
        textareaRef: attr(),
        /**
         * States the thread view on which this composer allows editing (if any).
         */
        threadView: one('ThreadView', {
            identifying: true,
            inverse: 'composerView',
        }),
        useDragVisibleDropZone: one('UseDragVisibleDropZone', {
            default: {},
            inverse: 'composerViewOwner',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
    onChanges: [
        {
            dependencies: ['composer'],
            methodName: '_onChangeComposer',
        },
        {
            dependencies: ['composer.textInputContent', 'composer.textInputCursorEnd', 'composer.textInputCursorStart'],
            methodName: '_onChangeDetectSuggestionDelimiterPosition',
        },
        {
            dependencies: ['suggestionDelimiterPosition', 'suggestionModelName', 'suggestionSearchTerm', 'composer.activeThread'],
            methodName: '_onChangeUpdateSuggestionList',
        },
        {
            dependencies: ['suggestionDelimiterPosition'],
            methodName: '_onSuggestionDelimiterPositionChanged',
        },
    ],
});
