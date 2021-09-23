/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Popover extends dependencies['mail.model'] {

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
         * Closes the popover when clicking outside, if appropriate.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (!this.component) {
                this.delete();
                return;
            }
            if (this.component.el.contains(ev.target)) {
                return;
            }
            this.delete();
        }

    }

    Popover.fields = {
        /**
         * HTML element that is used as anchor position for this popover.
         */
        anchorRef: attr({
            required: true,
        }),
        /**
         * States the OWL component of this popover.
         */
        component: attr(),
        /**
         * If set, this popover is owned by the discuss record.
         */
        discussOwner: one2one('mail.discuss', {
            readonly: true,
            inverse: 'invitePopover',
        }),
        /**
         * Position of the popover relative to its anchor point.
         * Valid values: 'top', 'right', 'bottom', 'left'
         */
        position: attr({
            default: 'top',
        }),
        /**
         * The record that represents the content inside the popover.
         */
        target: one2one('mail.model'),
        /**
         * Name of the component the target of popover is.
         */
        targetComponentName: attr(),
        /**
         * If set, this popover is owned by a thread view topbar record.
         */
        threadViewTopbarOwner: one2one('mail.thread_view_topbar', {
            readonly: true,
            inverse: 'invitePopover',
        }),
        /**
         * The type of this popover. Can be any (stringified) value.
         * Used to determine part of identity of this popover.
         * @see `_createRecordLocalId`
         */
        type: attr({
            readonly: true,
        }),
    };

    Popover.identifyingFields = [['discussOwner', 'threadViewTopbarOwner'], 'type'];
    Popover.modelName = 'mail.popover';

    return Popover;
}

registerNewModel('mail.popover', factory);
