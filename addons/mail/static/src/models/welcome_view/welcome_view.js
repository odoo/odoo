/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

function factory(dependencies) {

    const getNextGuestNameInputId = (function () {
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
         * Updates guest if needed then displays the thread view instead of the
         * welcome view.
         */
        async joinChannel() {
            if (this.hasGuestNameChanged) {
                await this.messaging.models['mail.guest'].performRpcGuestUpdateName({
                    id: this.messaging.currentGuest.id,
                    name: this.pendingGuestName.trim(),
                });
            }
            if (this.discussPublicView.shouldAddGuestAsMemberOnJoin) {
                await this.performRpcAddGuestAsMember();
            }
            this.discussPublicView.switchToThreadView();
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickJoinButton(ev) {
            this.joinChannel();
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
                this.joinChannel();
            }
        }

        /**
         * Adds the current guest to members of the channel linked to this
         * welcome view.
         */
        async performRpcAddGuestAsMember() {
            await this.env.services.rpc({
                route: '/mail/channel/add_guest_as_member',
                params: {
                    channel_id: this.channel.id,
                    channel_uuid: this.channel.uuid,
                },
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeGuestNameInputUniqueId() {
            return `o_WelcomeView_guestNameInput_${getNextGuestNameInputId()}`;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasGuestNameChanged() {
            return Boolean(this.messaging.currentGuest && this.originalGuestName !== this.pendingGuestName);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsJoinButtonDisabled() {
            return Boolean(this.messaging.currentGuest && this.pendingGuestName.trim() === '');
        }

        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMediaPreview() {
            return (this.channel && this.channel.defaultDisplayMode === 'video_full_screen')
                ? insertAndReplace()
                : clear();
        }

        /**
         * @private
         */
        _handleFocus() {
            if (this.isDoFocusGuestNameInput) {
                if (!this.guestNameInputRef.el) {
                    return;
                }
                this.update({ isDoFocusGuestNameInput: false });
                this.guestNameInputRef.el.focus();
                // place cursor at end of text
                const { length } = (this.pendingGuestName || '');
                this.guestNameInputRef.el.setSelectionRange(length, length);
            }
        }

        /**
         * Updates `pendingGuestName` with the value of the input element
         * referred by `guestNameInputRef`.
         *
         * @private
         */
        _updateGuestNameWithInputValue() {
            this.update({ pendingGuestName: this.guestNameInputRef.el.value });
        }

    }

    WelcomeView.fields = {
        /**
         * States the channel to redirect to once the user clicks on the
         * 'joinButton'.
         */
        channel: one2one('mail.thread', {
            readonly: true,
            required: true,
        }),
        /**
         * States discuss public view on which this welcome view is displayed.
         */
        discussPublicView: one2one('mail.discuss_public_view', {
            inverse: 'welcomeView',
            readonly: true,
            required: true,
        }),
        /**
         * States the OWL ref the to input element containing the
         * 'pendingGuestName'.
         */
        guestNameInputRef: attr(),
        /**
         * States the value to use for `id`, `for`, and `name` attributes of
         * the guest name input and its label.
         *
         * Necessary to ensure the uniqueness.
         */
        guestNameInputUniqueId: attr({
            compute: '_computeGuestNameInputUniqueId',
            readonly: true,
        }),
        /**
         * Determines whether the guest's name has been updated.
         *
         * Useful to determine whether a RPC should be done to update the name
         * server side.
         */
        hasGuestNameChanged: attr({
            compute: '_computeHasGuestNameChanged',
            readonly: true,
        }),
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
         * States the media preview embedded in this welcome view.
         */
        mediaPreview: one2one('mail.media_preview', {
            compute: '_computeMediaPreview',
            isCausal: true,
            readonly: true,
        }),
        /**
         * States the name the guest had when landing on the welcome view.
         *
         * Useful to determine whether the name has changed.
         */
        originalGuestName: attr(),
        /**
         * Determines the value of the 'guestNameInput'.
         *
         * Will be used to update the current guest's name when joining the
         * channel by clicking on the 'joinButton'.
         */
        pendingGuestName: attr(),
    };
    WelcomeView.identifyingFields = ['messaging'];
    WelcomeView.modelName = 'mail.welcome_view';

    return WelcomeView;
}

registerNewModel('mail.welcome_view', factory);
