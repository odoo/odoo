/** @odoo-module **/

import { attr, one } from '@mail/model/model_field';
import { registerModel } from '@mail/model/model_core';
import { clear, insertAndReplace, link, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'DiscussPublicView',
    identifyingFields: ['messaging'],
    recordMethods: {
        /**
         * Creates and displays the thread view and clears the welcome view.
         */
        async switchToThreadView() {
            this.update({
                threadViewer: insertAndReplace({
                    extraClass: 'flex-grow-1',
                    hasMemberList: true,
                    hasThreadView: true,
                    hasTopbar: true,
                    thread: link(this.channel),
                }),
                welcomeView: clear(),
            });
            if (this.isChannelTokenSecret) {
                // Change the URL to avoid leaking the invitation link.
                window.history.replaceState(window.history.state, null, `/discuss/channel/${this.channel.id}${window.location.search}`);
            }
            if (this.channel.defaultDisplayMode === 'video_full_screen') {
                await this.channel.toggleCall({ startWithVideo: true });
                await this.threadView.rtcCallViewer.activateFullScreen();
            }
        },
        /**
         * Creates and displays the welcome view and clears the thread viewer.
         */
        switchToWelcomeView() {
            this.update({
                threadViewer: clear(),
                welcomeView: insertAndReplace({
                    channel: link(this.channel),
                    isDoFocusGuestNameInput: true,
                    originalGuestName: this.messaging.currentGuest && this.messaging.currentGuest.name,
                    pendingGuestName: this.messaging.currentGuest && this.messaging.currentGuest.name,
                }),
            });
            if (this.welcomeView.mediaPreview) {
                this.welcomeView.mediaPreview.enableMicrophone();
                this.welcomeView.mediaPreview.enableVideo();
            }
        },
        _computeMessagingAsPublicView() {
            return replace(this.messaging);
        },
    },
    fields: {
        /**
         * States the channel linked to this discuss public view.
         */
        channel: one('Thread', {
            readonly: true,
            required: true,
        }),
        isChannelTokenSecret: attr({
            default: true,
        }),
        messagingAsPublicView: one('Messaging', {
            compute: '_computeMessagingAsPublicView',
            inverse: 'discussPublicView',
            readonly: true,
        }),
        shouldAddGuestAsMemberOnJoin: attr({
            default: false,
            readonly: true,
        }),
        shouldDisplayWelcomeViewInitially: attr({
            default: false,
            readonly: true,
        }),
        /**
         * States the thread view linked to this discuss public view.
         */
        threadView: one('ThreadView', {
            readonly: true,
            related: 'threadViewer.threadView',
        }),
        /**
         * States the thread viewer linked to this discuss public view.
         */
        threadViewer: one('ThreadViewer', {
            inverse: 'discussPublicView',
            isCausal: true,
        }),
        /**
         * States the welcome view linked to this discuss public view.
         */
        welcomeView: one('WelcomeView', {
            inverse: 'discussPublicView',
            isCausal: true,
        }),
    },
});
