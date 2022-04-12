/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'DiscussView',
    identifyingFields: ['discuss'],
    recordMethods: {
        /**
         * Handles click on the "Start a meeting" button.
         *
         * @param {MouseEvent} ev
         */
        async onClickStartAMeetingButton(ev) {
            const meetingChannel = await this.messaging.models['Thread'].createGroupChat({
                default_display_mode: 'video_full_screen',
                partners_to: [this.messaging.currentPartner.id],
            });
            meetingChannel.toggleCall({ startWithVideo: true });
            await meetingChannel.open({ focus: false });
            if (!meetingChannel.exists() || !this.discuss.threadView) {
                return;
            }
            this.discuss.threadView.topbar.openInvitePopoverView();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMobileAddItemHeaderAutocompleteInputView() {
            if (
                this.messaging.device.isMobile &&
                (this.discuss.isAddingChannel || this.discuss.isAddingChat)
            ) {
                return insertAndReplace();
            }
            return clear();
        },
    },
    fields: {
        mobileAddItemHeaderAutocompleteInputView: one('AutocompleteInputView', {
            compute: '_computeMobileAddItemHeaderAutocompleteInputView',
            inverse: 'discussViewOwnerAsMobileAddItemHeader',
            isCausal: true,
        }),
        discuss: one('Discuss', {
            inverse: 'discussView',
            readonly: true,
            required: true,
        }),
    },
});
