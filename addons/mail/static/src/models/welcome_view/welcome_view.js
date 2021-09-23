/** @odoo-module **/

import { attr, one2one } from '@mail/model/model_field';
import { browser } from "@web/core/browser/browser";
import { create } from '@mail/model/model_field_command';
import { registerNewModel } from '@mail/model/model_core';

function factory(dependencies) {

    const getNextGuestNameInputId = (function() {
        let id = 0;
        return () => ++id;
    })();

    class WelcomeView extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickJoinButton = this.onClickJoinButton.bind(this);
            this.onInputGuestNameInput = this.onInputGuestNameInput.bind(this);
            this.onKeydownGuestNameInput = this.onKeydownGuestNameInput.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {string} name 
         */
        static async updateGuestNameServerSide(name) {
            await this.env.services.rpc({
                route: '/mail/guest/update_name',
                params: { name },
            });
        }

        /**
         * @param {MouseEvent} ev 
         */
        async onClickJoinButton(ev) {
            this.updateGuestNameIfAnyThenJoinChannel();
        }

        /**
         * Handles OWL update on this WelcomeView component.
         */
        onComponentUpdate() {
            this._handleFocus();
        }

        /**
         * @param {KeyboardEvent} ev 
         */
        onInputGuestNameInput(ev) {
            this._updateGuestNameWithInputValue();
        }

        /**
         * @param {KeyboardEvent} ev 
         */
        onKeydownGuestNameInput(ev) {
            if (ev.key === 'Enter') {
                this.updateGuestNameIfAnyThenJoinChannel();
            }
        }

        /**
         * Redirects users to the related channel. If the current user is a
         * guest, first updates their username with the value of guestNameInput.
         */
        async updateGuestNameIfAnyThenJoinChannel() {
            if (this.messaging.currentGuest) {
                await this.messaging.models['mail.welcome_view'].updateGuestNameServerSide(this.pendingGuestName.trim());
            }
            browser.location.href = `/discuss/channel/${this.channel.id}`;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _handleFocus() {
            if (this.isDoFocusGuestNameInput) {
                if (!this.guestNameInputRef.el) {
                    return
                }
                this.update({ isDoFocusGuestNameInput: false });
                this.guestNameInputRef.el.focus();
                // place cursor at end of text
                const { length } = (this.pendingGuestName || '');
                this.guestNameInputRef.el.setSelectionRange(length, length);
            }
        }

        /**
         * @private
         */
        _updateGuestNameWithInputValue() {
            this.update({ pendingGuestName: this.guestNameInputRef.el.value });
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsJoinButtonDisabled() {
            return Boolean(this.messaging.currentGuest && !this.pendingGuestName.trim());
        }

    }

    WelcomeView.fields = {
        /**
         * The channel to redirect to once the user clicks on the 'joinButton'.
         */
        channel: one2one('mail.thread', {
            required: true,
        }),
        /**
         * Used as a value for `id`, `for`, and `name` attributes of the guest
         * name input and its label. Necessary to ensure the uniqueness.
         */
        guestNameInputUniqueId: attr({
            default: `o_WelcomeView_guestNameInput_${getNextGuestNameInputId()}`,
        }),
        /**
         * Ref the to input element containing the 'pendingGuestName'.
         */
        guestNameInputRef: attr(),
        /**
         * Determines whether the 'guestNameInput' should be focused the next
         * time the component is updated.
         */
        isDoFocusGuestNameInput: attr(),
        /**
         * Determines whether the 'joinButton' is disabled.
         * 
         * Shall be disabled when 'pendingGuestName' is an empty string while
         * the current user is a guest.
         */
        isJoinButtonDisabled: attr({
            compute: '_computeIsJoinButtonDisabled'
        }),
        /**
         * The MediaPreview linked to the current WelcomeView.
         */
        mediaPreview: one2one('mail.media_preview', {
            default: create(),
            isCausal: true,
            readonly: true,
            required: true,
        }),
        /**
         * The value of the 'guestNameInput'.
         * 
         * Will be used to update the current guest's name when joining the
         * channel by clicking on the 'joinButton'.
         */
        pendingGuestName: attr(),
    };

    WelcomeView.modelName = 'mail.welcome_view';

    return WelcomeView;
}

registerNewModel('mail.welcome_view', factory);
