/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

function factory(dependencies) {

    class PopoverView extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        _created() {
            this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
            document.addEventListener('click', this._onClickCaptureGlobal, true);
        }

        _willDelete() {
            document.removeEventListener('click', this._onClickCaptureGlobal, true);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {owl.Ref}
         */
        _computeAnchorRef() {
            if (this.threadViewTopbarOwner) {
                return this.threadViewTopbarOwner.inviteButtonRef;
            }
            return clear();
        }

        /**
         * @private
         * @returns {string}
         */
        _computePosition() {
            if (this.threadViewTopbarOwner) {
                return 'bottom';
            }
            return clear();
        }

        /**
         * Closes the popover when clicking outside, if appropriate.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (!this.component || !this.component.el) {
                return;
            }
            if (this.anchorRef && this.anchorRef.el && this.anchorRef.el.contains(ev.target)) {
                return;
            }
            if (this.component.el.contains(ev.target)) {
                return;
            }
            this.delete();
        }

    }

    PopoverView.fields = {
        /**
         * HTML element that is used as anchor position for this popover view.
         */
        anchorRef: attr({
            compute: '_computeAnchorRef',
            required: true,
        }),
        /**
         * The record that represents the content inside the popover view.
         */
        channelInvitationForm: one2one('mail.channel_invitation_form', {
            inverse: 'popoverView',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        /**
         * States the OWL component of this popover view.
         */
        component: attr(),
        /**
         * Position of the popover view relative to its anchor point.
         * Valid values: 'top', 'right', 'bottom', 'left'
         */
        position: attr({
            compute: '_computePosition',
            default: 'top',
        }),
        /**
         * If set, this popover view is owned by a thread view topbar record.
         */
        threadViewTopbarOwner: one2one('mail.thread_view_topbar', {
            inverse: 'invitePopoverView',
            readonly: true,
        }),
    };

    PopoverView.identifyingFields = ['threadViewTopbarOwner', 'channelInvitationForm'];
    PopoverView.modelName = 'mail.popover_view';

    return PopoverView;
}

registerNewModel('mail.popover_view', factory);
