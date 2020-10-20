/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

function factory(dependencies) {

    class ThreadViewTopBar extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickHideMemberList = this.onClickHideMemberList.bind(this);
            this.onClickInboxMarkAllAsRead = this.onClickInboxMarkAllAsRead.bind(this);
            this.onClickInviteButton = this.onClickInviteButton.bind(this);
            this.onClickShowMemberList = this.onClickShowMemberList.bind(this);
            this.onClickTopbarThreadName = this.onClickTopbarThreadName.bind(this);
            this.onClickUnstarAll = this.onClickUnstarAll.bind(this);
            this.onInputThreadNameInput = this.onInputThreadNameInput.bind(this);
            this.onKeyDownThreadNameInput = this.onKeyDownThreadNameInput.bind(this);
            this.onMouseEnterTopBarThreadName = this.onMouseEnterTopBarThreadName.bind(this);
            this.onMouseLeaveTopBarThreadName = this.onMouseLeaveTopBarThreadName.bind(this);
            this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
            this.onClickTopbarThreadDescription = this.onClickTopbarThreadDescription.bind(this);
            this.onInputThreadDescriptionInput = this.onInputThreadDescriptionInput.bind(this);
            this.onKeyDownThreadDescriptionInput = this.onKeyDownThreadDescriptionInput.bind(this);
            this.onMouseEnterTopBarThreadDescription = this.onMouseEnterTopBarThreadDescription.bind(this);
            this.onMouseLeaveTopBarThreadDescription = this.onMouseLeaveTopBarThreadDescription.bind(this);
            this.onClickSearch = this.onClickSearch.bind(this);
            document.addEventListener('click', this._onClickCaptureGlobal, true);
            return super._created();
        }

        /**
         * @override
         */
        _willDelete() {
            document.removeEventListener('click', this._onClickCaptureGlobal, true);
            return super._willDelete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

       /**
         * Handles click on the "hide member list" button.
         *
         * @param {Event} ev
         */
        onClickHideMemberList(ev) {
            this.threadView.update({ isMemberListOpened: false });
            this.threadView.addComponentHint('member-list-hidden');
        }

        /**
         * Handles click on the "mark all as read" button of Inbox.
         *
         * @param {MouseEvent} ev
         */
        onClickInboxMarkAllAsRead(ev) {
            this.messaging.models['mail.message'].markAllAsRead();
        }

        /**
         * Handles click on the "invite" button.
         *
         * @param {MouseEvent} ev
         */
        onClickInviteButton(ev) {
            if (this.threadView.channelInvitationForm.component) {
                return;
            }
            if (!this.messaging.isCurrentUserGuest) {
                this.threadView.channelInvitationForm.update({ doFocusOnSearchInput: true });
                this.threadView.channelInvitationForm.searchPartnersToInvite();
            }
        }

        /**
         * Handles click on the "search" button.
         *
         * @param {MouseEvent} ev
         */
        onClickSearch(ev) {
            this.threadView.threadViewer.toggleSearchBox();
        }

        /**
         * Handles click on the "show member list" button.
         *
         * @param {Event} ev
         */
        onClickShowMemberList(ev) {
            this.threadView.update({ isMemberListOpened: true });
        }

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
        }

        /**
         * Handles click on the "thread description" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onClickTopbarThreadDescription(ev) {
            if (!this.thread || !this.thread.isChannelDescriptionChangeable) {
                return;
            }
            // Guests cannot edit description
            if (this.messaging.isCurrentUserGuest) {
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
        }

        /**
         * Handles click on the "unstar all" button of Starred box.
         *
         * @param {MouseEvent} ev
         */
        onClickUnstarAll(ev) {
            this.messaging.models['mail.message'].unstarAll();
        }

        /**
         * Handles OWL update on this top bar component.
         */
        onComponentUpdate() {
            if (this.doFocusOnThreadNameInput) {
                this.threadNameInputRef.el.focus();
                this.update({ doFocusOnThreadNameInput: clear() });
            }
            if (this.doFocusOnThreadDescriptionInput) {
                this.threadDescriptionInputRef.el.focus();
                this.update({ doFocusOnThreadDescriptionInput: clear() });
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
        }

        /**
         * Handles input on the "thread name" input of this top bar.
         *
         * @param {InputEvent} ev
         */
        onInputThreadNameInput(ev) {
            this.update({ pendingThreadName: ev.target.value });
        }

        /**
         * Handles input on the "thread description" input of this top bar.
         *
         * @param {InputEvent} ev
         */
        onInputThreadDescriptionInput(ev) {
            this.update({ pendingThreadDescription: ev.target.value });
        }

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
        }

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
        }

        /**
         * Handles mouseenter on the "thread name" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseEnterTopBarThreadName(ev) {
            if (!this.thread || !this.thread.isChannelRenamable) {
                return;
            }
            this.update({ isMouseOverThreadName: true });
        }

        /**
         * Handles mouseenter on the "thread description" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseEnterTopBarThreadDescription(ev) {
            if (!this.thread || !this.thread.isChannelDescriptionChangeable) {
                return;
            }
            this.update({ isMouseOverThreadDescription: true });
        }

        /**
         * Handles mouseleave on the "thread name" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseLeaveTopBarThreadName(ev) {
            this.update({ isMouseOverThreadName: false });
        }

        /**
         * Handles mouseleave on the "thread description" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseLeaveTopBarThreadDescription(ev) {
            this.update({ isMouseOverThreadDescription: false });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _applyThreadRename() {
            const newName = this.pendingThreadName;
            this.update({
                isEditingThreadName: false,
                pendingThreadName: clear(),
            });
            if (this.thread.channel_type === 'chat' && newName !== this.thread.custom_channel_name) {
                this.thread.setCustomName(newName);
            }
            if (newName && this.thread.channel_type === 'channel' && newName !== this.thread.name) {
                this.thread.rename(newName);
            }
            if (this.thread.channel_type === 'group' && newName !== this.thread.name) {
                this.thread.rename(newName);
            }
        }

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
        }

        /**
         * @private
         */
        _discardThreadRename() {
            this.update({
                isEditingThreadName: false,
                pendingThreadName: clear(),
            });
        }

        /**
         * @private
         */
        _discardThreadChangeDescription() {
            this.update({
                isEditingThreadDescription: false,
                pendingThreadDescription: clear(),
            });
        }

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (this.isEditingThreadName && this.threadNameInputRef.el && !this.threadNameInputRef.el.contains(ev.target)) {
                this._applyThreadRename();
            }
            if (this.isEditingThreadDescription && this.threadDescriptionInputRef.el && !this.threadDescriptionInputRef.el.contains(ev.target)) {
                this._applyThreadChangeDescription();
            }
        }

    }

    ThreadViewTopBar.fields = {
        /**
         * Determines whether this thread name input needs to be focused.
         */
        doFocusOnThreadNameInput: attr(),
        /**
         * Determines whether this thread description input needs to be focused.
         */
        doFocusOnThreadDescriptionInput: attr(),
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
        thread: many2one('mail.thread', {
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
        threadView: one2one('mail.thread_view', {
            inverse: 'topbar',
            required: true,
        }),
    };

    ThreadViewTopBar.modelName = 'mail.thread_view_topbar';

    return ThreadViewTopBar;
}

registerNewModel('mail.thread_view_topbar', factory);
