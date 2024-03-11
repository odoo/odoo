/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ThreadViewTopbar',
    lifecycleHooks: {
        _created() {
            document.addEventListener('click', this._onClickCaptureGlobal, true);
        },
        _willDelete() {
            document.removeEventListener('click', this._onClickCaptureGlobal, true);
        },
    },
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        async onClickCamera(ev) {
            if (this.thread.hasPendingRtcRequest) {
                return;
            }
            await this.thread.toggleCall({
                startWithVideo: true,
            });
        },
        /**
         * @param {Event} ev
         */
        onClickHideCallSettingsMenu(ev) {
            this.threadView.update({ isCallSettingsMenuOpen: false });
        },
        /**
         * Handles click on the "hide member list" button.
         *
         * @param {Event} ev
         */
         onClickHideMemberList(ev) {
            this.threadView.update({ isMemberListOpened: false });
            this.threadView.addComponentHint('member-list-hidden');
        },
        /**
         * Handles click on the "mark all as read" button of Inbox.
         *
         * @param {MouseEvent} ev
         */
        onClickInboxMarkAllAsRead(ev) {
            this.messaging.models['Message'].markAllAsRead();
        },
        /**
         * Handles click on the "invite" button.
         *
         * @param {MouseEvent} ev
         */
        onClickInviteButton(ev) {
            if (this.invitePopoverView) {
                this.update({ invitePopoverView: clear() });
            } else {
                this.openInvitePopoverView();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickPhone(ev) {
            if (this.thread.hasPendingRtcRequest) {
                return;
            }
            await this.thread.toggleCall();
        },
        /**
         * @param {Event} ev
         */
        onClickShowCallSettingsMenu(ev) {
            // FIXME maybe find another way to prevent both being open at the same time?
            this.threadView.update({
                isCallSettingsMenuOpen: true,
                isMemberListOpened: false,
            });
        },
        /**
         * Handles click on the "show member list" button.
         *
         * @param {Event} ev
         */
        onClickShowMemberList(ev) {
            this.threadView.update({
                isCallSettingsMenuOpen: false,
                isMemberListOpened: true,
            });
        },
        /**
         * Handles click on the "thread name" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onClickTopbarThreadName(ev) {
            if (!this.thread || !this.thread.isChannelRenamable) {
                return;
            }
            // Guests cannot edit thread name
            if (this.messaging.isCurrentUserGuest) {
                return;
            }
            const selection = window.getSelection();
            this.update({
                doFocusOnThreadNameInput: true,
                doSetSelectionDirectionOnThreadNameInput: selection.anchorOffset < selection.focusOffset ? 'forward' : 'backward',
                doSetSelectionEndOnThreadNameInput: Math.max(selection.focusOffset, selection.anchorOffset),
                doSetSelectionStartOnThreadNameInput: Math.min(selection.focusOffset, selection.anchorOffset),
                isEditingThreadName: true,
                isMouseOverThreadName: false,
                pendingThreadName: this.thread.displayName,
            });
        },
        /**
         * Handles click on the "thread description" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onClickTopbarThreadDescription(ev) {
            if (!this.thread || !this.thread.isDescriptionEditableByCurrentUser) {
                return;
            }
            const selection = window.getSelection();
            this.update({
                doFocusOnThreadDescriptionInput: true,
                doSetSelectionDirectionOnThreadDescriptionInput: selection.anchorOffset < selection.focusOffset ? 'forward' : 'backward',
                doSetSelectionEndOnThreadDescriptionInput: Math.max(selection.focusOffset, selection.anchorOffset),
                doSetSelectionStartOnThreadDescriptionInput: Math.min(selection.focusOffset, selection.anchorOffset),
                isEditingThreadDescription: true,
                isMouseOverThreadDescription: false,
                pendingThreadDescription: this.thread.description || "",
            });
        },
        /**
         * Handles click on the "unstar all" button of Starred box.
         *
         * @param {MouseEvent} ev
         */
        onClickUnstarAll(ev) {
            this.messaging.models['Message'].unstarAll();
        },
        /**
         * Handles click on the guest name.
         *
         * @param {MouseEvent} ev
         */
        onClickUserName(ev) {
            if (!this.messaging.isCurrentUserGuest) {
                return;
            }
            const selection = window.getSelection();
            this.update({
                doFocusOnGuestNameInput: true,
                doSetSelectionDirectionOnGuestNameInput: selection.anchorOffset < selection.focusOffset ? 'forward' : 'backward',
                doSetSelectionEndOnGuestNameInput: Math.max(selection.focusOffset, selection.anchorOffset),
                doSetSelectionStartOnGuestNameInput: Math.min(selection.focusOffset, selection.anchorOffset),
                isEditingGuestName: true,
                isMouseOverUserName: false,
                pendingGuestName: this.messaging.currentGuest.name,
            });
        },
        /**
         * Handles OWL update on this top bar component.
         */
        onComponentUpdate() {
            if (this.doFocusOnGuestNameInput) {
                this.guestNameInputRef.el.focus();
                this.update({ doFocusOnGuestNameInput: clear() });
            }
            if (this.doFocusOnThreadNameInput) {
                this.threadNameInputRef.el.focus();
                this.update({ doFocusOnThreadNameInput: clear() });
            }
            if (this.doFocusOnThreadDescriptionInput) {
                this.threadDescriptionInputRef.el.focus();
                this.update({ doFocusOnThreadDescriptionInput: clear() });
            }
            if (
                this.doSetSelectionStartOnGuestNameInput !== undefined &&
                this.doSetSelectionEndOnGuestNameInput !== undefined &&
                this.doSetSelectionDirectionOnGuestNameInput !== undefined
            ) {
                this.guestNameInputRef.el.setSelectionRange(
                    this.doSetSelectionStartOnGuestNameInput,
                    this.doSetSelectionEndOnGuestNameInput,
                    this.doSetSelectionDirectionOnGuestNameInput
                );
                this.update({
                    doSetSelectionDirectionOnGuestNameInput: clear(),
                    doSetSelectionEndOnGuestNameInput: clear(),
                    doSetSelectionStartOnGuestNameInput: clear(),
                });
            }
            if (
                this.doSetSelectionStartOnThreadNameInput !== undefined &&
                this.doSetSelectionEndOnThreadNameInput !== undefined &&
                this.doSetSelectionDirectionOnThreadNameInput !== undefined
            ) {
                this.threadNameInputRef.el.setSelectionRange(
                    this.doSetSelectionStartOnThreadNameInput,
                    this.doSetSelectionEndOnThreadNameInput,
                    this.doSetSelectionDirectionOnThreadNameInput
                );
                this.update({
                    doSetSelectionDirectionOnThreadNameInput: clear(),
                    doSetSelectionEndOnThreadNameInput: clear(),
                    doSetSelectionStartOnThreadNameInput: clear(),
                });
            }
            if (
                this.doSetSelectionStartOnThreadDescriptionInput !== undefined &&
                this.doSetSelectionEndOnThreadDescriptionInput !== undefined &&
                this.doSetSelectionDirectionOnThreadDescriptionInput !== undefined
            ) {
                this.threadDescriptionInputRef.el.setSelectionRange(
                    this.doSetSelectionStartOnThreadDescriptionInput,
                    this.doSetSelectionEndOnThreadDescriptionInput,
                    this.doSetSelectionDirectionOnThreadDescriptionInput
                );
                this.update({
                    doSetSelectionDirectionOnThreadDescriptionInput: clear(),
                    doSetSelectionEndOnThreadDescriptionInput: clear(),
                    doSetSelectionStartOnThreadDescriptionInput: clear(),
                });
            }
        },
        /**
         * @param {KeyboardEvent} ev
         */
        onInputGuestNameInput(ev) {
            this.update({ pendingGuestName: this.guestNameInputRef.el.value });
        },
        /**
         * Handles input on the "thread name" input of this top bar.
         *
         * @param {InputEvent} ev
         */
        onInputThreadNameInput(ev) {
            this.update({ pendingThreadName: ev.target.value });
        },
        /**
         * Handles input on the "thread description" input of this top bar.
         *
         * @param {InputEvent} ev
         */
        onInputThreadDescriptionInput(ev) {
            this.update({ pendingThreadDescription: ev.target.value });
        },
        /**
         * Handles keydown on the "guest name" input of this top bar.
         *
         * @param {KeyboardEvent} ev
         */
        onKeyDownGuestNameInput(ev) {
            switch (ev.key) {
                case 'Enter':
                    if (this.pendingGuestName.trim() !== '') {
                        this._applyGuestRename();
                    }
                    break;
                case 'Escape':
                    this._resetGuestNameInput();
                    break;
            }
        },
        /**
         * Handles keydown on the "thread name" input of this top bar.
         *
         * @param {KeyboardEvent} ev
         */
        onKeyDownThreadNameInput(ev) {
            switch (ev.key) {
                case 'Enter':
                    this._applyThreadRename();
                    break;
                case 'Escape':
                    this._discardThreadRename();
                    break;
            }
        },
        /**
         * Handles keydown on the "thread description" input of this top bar.
         *
         * @param {KeyboardEvent} ev
         */
        onKeyDownThreadDescriptionInput(ev) {
            switch (ev.key) {
                case 'Enter':
                    this._applyThreadChangeDescription();
                    break;
                case 'Escape':
                    this._discardThreadChangeDescription();
                    break;
            }
        },
        /**
         * Handles mouseenter on the "thread name" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseEnterTopbarThreadName(ev) {
            if (!this.exists() || !this.thread || !this.thread.isChannelRenamable) {
                return;
            }
            this.update({ isMouseOverThreadName: true });
        },
        /**
         * Handles mouseenter on the "thread description" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseEnterTopbarThreadDescription(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ isMouseOverThreadDescription: true });
        },
        /**
         * Handles mouseenter on the "user name" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseEnterUserName(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ isMouseOverUserName: true });
        },
        /**
         * Handles mouseleave on the "thread name" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseLeaveTopbarThreadName(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ isMouseOverThreadName: false });
        },
        /**
         * Handles mouseleave on the "thread description" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseLeaveTopbarThreadDescription(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ isMouseOverThreadDescription: false });
        },
        /**
         * Handles mouseleave on the "user name" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseLeaveUserName(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ isMouseOverUserName: false });
        },
        /**
         * Open the invite popover view in this thread view topbar.
         */
        openInvitePopoverView() {
            this.update({ invitePopoverView: {} });
            if (this.messaging.isCurrentUserGuest) {
                return;
            }
            this.invitePopoverView.channelInvitationForm.update({ doFocusOnSearchInput: true });
            this.invitePopoverView.channelInvitationForm.searchPartnersToInvite();
        },
        /**
         * @private
         */
        _applyGuestRename() {
            if (this.hasGuestNameChanged) {
                this.messaging.models['Guest'].performRpcGuestUpdateName({
                    id: this.messaging.currentGuest.id,
                    name: this.pendingGuestName.trim(),
                });
            }
            this._resetGuestNameInput();
        },
        /**
         * @private
         */
        _applyThreadRename() {
            const newName = this.pendingThreadName;
            this.update({
                isEditingThreadName: false,
                pendingThreadName: clear(),
            });
            if (this.thread.channel.channel_type === 'chat' && newName !== this.thread.channel.custom_channel_name) {
                this.thread.setCustomName(newName);
            }
            if (newName && this.thread.channel.channel_type === 'channel' && newName !== this.thread.name) {
                this.thread.rename(newName);
            }
            if (this.thread.channel.channel_type === 'group' && newName !== this.thread.name) {
                this.thread.rename(newName);
            }
        },
        /**
         * @private
         */
        _applyThreadChangeDescription() {
            const newDescription = this.pendingThreadDescription || "";
            this.update({
                isEditingThreadDescription: false,
                pendingThreadDescription: clear(),
            });
            if (newDescription !== this.thread.description) {
                this.thread.changeDescription(newDescription);
            }
        },
        /**
         * @private
         */
        _discardThreadRename() {
            this.update({
                isEditingThreadName: false,
                pendingThreadName: clear(),
            });
        },
        /**
         * @private
         */
        _discardThreadChangeDescription() {
            this.update({
                isEditingThreadDescription: false,
                pendingThreadDescription: clear(),
            });
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (this.isEditingGuestName && this.guestNameInputRef.el && !this.guestNameInputRef.el.contains(ev.target)) {
                if (this.pendingGuestName.trim() !== '') {
                    this._applyGuestRename();
                } else {
                    this._resetGuestNameInput();
                }
            }
            if (this.isEditingThreadName && this.threadNameInputRef.el && !this.threadNameInputRef.el.contains(ev.target)) {
                this._applyThreadRename();
            }
            if (this.isEditingThreadDescription && this.threadDescriptionInputRef.el && !this.threadDescriptionInputRef.el.contains(ev.target)) {
                this._applyThreadChangeDescription();
            }
        },
        /**
         * @private
         */
        _resetGuestNameInput() {
            this.update({
                isEditingGuestName: false,
                pendingGuestName: clear(),
            });
        },
    },
    fields: {
        /**
         * States the URL of the profile picture of the current user.
         */
        avatarUrl: attr({
            compute() {
                if (this.messaging.isCurrentUserGuest) {
                    if (!this.thread) {
                        return '';
                    }
                    return `/mail/channel/${this.thread.id}/guest/${this.messaging.currentGuest.id}/avatar_128?unique=${this.messaging.currentGuest.name}`;
                }
                if (this.messaging.currentPartner) {
                    return this.messaging.currentPartner.avatarUrl;
                }
                return clear();
            },
            default: '',
        }),
        /**
         * Determines whether the guest name input needs to be focused.
         */
        doFocusOnGuestNameInput: attr(),
        /**
         * Determines whether this thread name input needs to be focused.
         */
        doFocusOnThreadNameInput: attr(),
        /**
         * Determines whether this thread description input needs to be focused.
         */
        doFocusOnThreadDescriptionInput: attr(),
        /**
         * Determines the direction to set on the selection of this guest name
         * input. This value is not a representation of current selection, but
         * an instruction to set a new selection. Must be set together with
         * `doSetSelectionEndOnGuestNameInput` and `doSetSelectionStartOnGuestNameInput`
         * to have an effect.
         */
        doSetSelectionDirectionOnGuestNameInput: attr(),
        /**
         * Determines the direction to set on the selection of this thread name
         * input. This value is not a representation of current selection, but
         * an instruction to set a new selection. Must be set together with
         * `doSetSelectionEndOnThreadNameInput` and `doSetSelectionStartOnThreadNameInput`
         * to have an effect.
         */
        doSetSelectionDirectionOnThreadNameInput: attr(),
        /**
         * Determines the direction to set on the selection of this thread description
         * input. This value is not a representation of current selection, but
         * an instruction to set a new selection. Must be set together with
         * `doSetSelectionEndOnThreadDescriptionInput` and `doSetSelectionStartOnThreadDescriptionInput`
         * to have an effect.
         */
        doSetSelectionDirectionOnThreadDescriptionInput: attr(),
        /**
         * Determines the ending position where to place the selection on this
         * guest name input (zero-based index). This value is not a
         * representation of current selection, but an instruction to set a new
         * selection. Must be set together with `doSetSelectionDirectionOnGuestNameInput`
         * and `doSetSelectionStartOnGuestNameInput` to have an effect.
         */
        doSetSelectionEndOnGuestNameInput: attr(),
        /**
         * Determines the ending position where to place the selection on this
         * thread name input (zero-based index). This value is not a
         * representation of current selection, but an instruction to set a new
         * selection. Must be set together with `doSetSelectionDirectionOnThreadNameInput`
         * and `doSetSelectionStartOnThreadNameInput` to have an effect.
         */
        doSetSelectionEndOnThreadNameInput: attr(),
        /**
         * Determines the ending position where to place the selection on this
         * thread description input (zero-based index). This value is not a
         * representation of current selection, but an instruction to set a new
         * selection. Must be set together with `doSetSelectionDirectionOnThreadDescriptionInput`
         * and `doSetSelectionStartOnThreadDescriptionInput` to have an effect.
         */
        doSetSelectionEndOnThreadDescriptionInput: attr(),
        /**
         * Determines the starting position where to place the selection on this
         * guest name input (zero-based index). This value is not a
         * representation of current selection, but an instruction to set a new
         * selection. Must be set together with `doSetSelectionDirectionOnGuestNameInput` and
         * `doSetSelectionEndOnGuestNameInput` to have an effect.
         */
        doSetSelectionStartOnGuestNameInput: attr(),
        /**
         * Determines the starting position where to place the selection on this
         * thread name input (zero-based index). This value is not a
         * representation of current selection, but an instruction to set a new
         * selection. Must be set together with `doSetSelectionDirectionOnThreadNameInput` and
         * `doSetSelectionEndOnThreadNameInput` to have an effect.
         */
        doSetSelectionStartOnThreadNameInput: attr(),
        /**
         * Determines the starting position where to place the selection on this
         * thread description input (zero-based index). This value is not a
         * representation of current selection, but an instruction to set a new
         * selection. Must be set together with `doSetSelectionDirectionOnThreadDescriptionInput` and
         * `doSetSelectionEndOnThreadDescriptionInput` to have an effect.
         */
        doSetSelectionStartOnThreadDescriptionInput: attr(),
        /**
         * States the OWL ref of the "guest name" input of this top bar.
         * Useful to focus it, or to know when a click is done outside of it.
         */
        guestNameInputRef: attr(),
        /**
         * Determines whether the guest's name has been updated.
         *
         * Useful to determine whether a RPC should be done to update the name
         * server side.
         */
        hasGuestNameChanged: attr({
            compute() {
                return Boolean(
                    this.messaging.currentGuest &&
                    this.pendingGuestName !== this.messaging.currentGuest.name
                );
            },
        }),
        /**
         * Determines whether description area should display on top bar.
         */
        hasDescriptionArea: attr({
            compute() {
                return Boolean(this.thread && (this.thread.description || this.thread.isDescriptionEditableByCurrentUser));
            },
        }),
        /**
         * Determines whether the guest is currently being renamed.
         */
        isEditingGuestName: attr({
            default: false,
        }),
        /**
         * States the OWL ref of the invite button.
         * Useful to provide anchor for the invite popover positioning.
         */
        inviteButtonRef: attr(),
        /**
         * If set, this is the record of invite button popover that is currently
         * open in the topbar.
         */
        invitePopoverView: one('PopoverView', {
            inverse: 'threadViewTopbarOwnerAsInvite',
        }),
        /**
         * States whether this thread description is highlighted.
         */
        isDescriptionHighlighted: attr({
            compute() {
                return Boolean(
                    this.isMouseOverThreadDescription &&
                    this.thread.isDescriptionEditableByCurrentUser
                );
            },
        }),
        /**
         * Determines whether this thread is currently being renamed.
         */
        isEditingThreadName: attr({
            default: false,
        }),
        /**
         * Determines whether this thread description is currently being changed.
         */
        isEditingThreadDescription: attr({
            default: false,
        }),
        /**
         * States whether the cursor is currently over this thread name in
         * the top bar.
         */
        isMouseOverThreadName: attr({
            default: false,
        }),
        /**
         * States whether the cursor is currently over this thread description in
         * the top bar.
         */
        isMouseOverThreadDescription: attr({
            default: false,
        }),
        /**
         * States whether the cursor is currently over the user name in this top
         * bar.
         */
        isMouseOverUserName: attr({
            default: false,
        }),
        /**
         * Determines the pending name of the guest, which is the new name of
         * the guest as the current guest is currently typing it, with the goal
         * of renaming the guest.
         * This value can either be applied or discarded.
         */
        pendingGuestName: attr({
            default: "",
        }),
        /**
         * Determines the pending name of this thread, which is the new name of
         * the thread as the current user is currently typing it, with the goal
         * of renaming the thread.
         * This value can either be applied or discarded.
         */
        pendingThreadName: attr({
            default: "",
        }),
        /**
         * Determines the pending description of this thread, which is the new description of
         * the thread as the current user is currently typing it, with the goal
         * of changing the description the thread.
         * This value can either be applied or discarded.
         */
        pendingThreadDescription: attr({
            default: "",
        }),
        /**
         * States the thread that is displayed by this top bar.
         */
        thread: one('Thread', {
            related: 'threadView.thread',
        }),
        /**
         * States the OWL ref of the "thread name" input of this top bar.
         * Useful to focus it, or to know when a click is done outside of it.
         */
        threadNameInputRef: attr(),
        /**
         * States the OWL ref of the thread description input of this top bar.
         * Useful to focus it, or to know when a click is done outside of it.
         */
        threadDescriptionInputRef: attr(),
        /**
         * States the thread view managing this top bar.
         */
        threadView: one('ThreadView', {
            identifying: true,
            inverse: 'topbar',
        }),
    },
});
