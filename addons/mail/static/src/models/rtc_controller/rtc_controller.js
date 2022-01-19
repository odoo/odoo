/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'RtcController',
    identifyingFields: ['callViewer'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickCamera(ev) {
            this.messaging.rtc.toggleUserVideo();
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickDeafen(ev) {
            if (this.messaging.rtc.currentRtcSession.isDeaf) {
                this.messaging.rtc.undeafen();
            } else {
                this.messaging.rtc.deafen();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickMicrophone(ev) {
            if (this.messaging.rtc.currentRtcSession.isMute) {
                if (this.messaging.rtc.currentRtcSession.isSelfMuted) {
                    this.messaging.rtc.unmute();
                }
                if (this.messaging.rtc.currentRtcSession.isDeaf) {
                    this.messaging.rtc.undeafen();
                }
            } else {
                this.messaging.rtc.mute();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickRejectCall(ev) {
            if (this.callViewer.threadView.thread.hasPendingRtcRequest) {
                return;
            }
            await this.callViewer.threadView.thread.leaveCall();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickScreen(ev) {
            this.messaging.rtc.toggleScreenShare();
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickToggleAudioCall(ev) {
            if (this.callViewer.threadView.thread.hasPendingRtcRequest) {
                return;
            }
            await this.callViewer.threadView.thread.toggleCall();
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickToggleVideoCall(ev) {
            if (this.callViewer.threadView.thread.hasPendingRtcRequest) {
                return;
            }
            await this.callViewer.threadView.thread.toggleCall({
                startWithVideo: true,
            });
        },
        /**
         * @private
         */
        _computeIsSmall() {
            return Boolean(this.callViewer && this.callViewer.threadView.compact && !this.callViewer.isFullScreen);
        },
    },
    fields: {
        callViewer: one('RtcCallViewer', {
            inverse: 'rtcController',
            readonly: true,
            required: true,
        }),
        isSmall: attr({
            compute: '_computeIsSmall',
        }),
        rtcOptionList: one('RtcOptionList', {
            default: insertAndReplace(),
            inverse: 'rtcController',
            isCausal: true,
        }),
    },
});
