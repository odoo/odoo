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
            this.onClickInboxMarkAllAsRead = this.onClickInboxMarkAllAsRead.bind(this);
            this.onClickInviteButton = this.onClickInviteButton.bind(this);
            this.onClickTopbarThreadName = this.onClickTopbarThreadName.bind(this);
            this.onClickUnstarAll = this.onClickUnstarAll.bind(this);
            this.onInputThreadNameInput = this.onInputThreadNameInput.bind(this);
            this.onKeyDownThreadNameInput = this.onKeyDownThreadNameInput.bind(this);
            this.onMouseEnterTopBarThreadName = this.onMouseEnterTopBarThreadName.bind(this);
            this.onMouseLeaveTopBarThreadName = this.onMouseLeaveTopBarThreadName.bind(this);
            this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
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
            this.threadView.channelInvitationForm.update({ doFocusOnSearchInput: true });
            this.threadView.channelInvitationForm.searchPartnersToInvite();
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
         * Handles mouseleave on the "thread name" of this top bar.
         *
         * @param {MouseEvent} ev
         */
        onMouseLeaveTopBarThreadName(ev) {
            this.update({ isMouseOverThreadName: false });
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
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (!this.threadNameInputRef) {
                return;
            }
            if (this.threadNameInputRef.el && this.threadNameInputRef.el.contains(ev.target)) {
                return;
            }
            if (this.isEditingThreadName) {
                this._applyThreadRename();
            }
        }

    }

    ThreadViewTopBar.fields = {
        /**
         * Determines whether this thread name input needs to be focused.
         */
        doFocusOnThreadNameInput: attr(),
        /**
         * Determines the direction to set on the selection of this thread name
         * input. This value is not a representation of current selection, but
         * an instruction to set a new selection. Must be set together with
         * `doSetSelectionEndOnThreadNameInput` and `doSetSelectionStartOnThreadNameInput`
         * to have an effect.
         */
        doSetSelectionDirectionOnThreadNameInput: attr(),
        /**
         * Determines the ending position where to place the selection on this
         * thread name input (zero-based index). This value is not a
         * representation of current selection, but an instruction to set a new
         * selection. Must be set together with `doSetSelectionDirectionOnThreadNameInput`
         * and `doSetSelectionStartOnThreadNameInput` to have an effect.
         */
        doSetSelectionEndOnThreadNameInput: attr(),
        /**
         * Determines the starting position where to place the selection on this
         * thread name input (zero-based index). This value is not a
         * representation of current selection, but an instruction to set a new
         * selection. Must be set together with `doSetSelectionDirectionOnThreadNameInput` and
         * `doSetSelectionEndOnThreadNameInput` to have an effect.
         */
        doSetSelectionStartOnThreadNameInput: attr(),
        /**
         * Determines whether this thread is currently being renamed.
         */
        isEditingThreadName: attr({
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
         * Determines the pending name of this thread, which is the new name of
         * the thread as the current user is currently typing it, with the goal
         * of renaming the thread.
         * This value can either be applied or discarded.
         */
        pendingThreadName: attr({
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
