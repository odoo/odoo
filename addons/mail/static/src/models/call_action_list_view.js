/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'CallActionListView',
    identifyingFields: ['callMainView'],
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
            if (this.channel.hasPendingRtcRequest) {
                return;
            }
            await this.channel.leaveCall();
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
            if (this.channel.hasPendingRtcRequest) {
                return;
            }
            await this.channel.toggleCall();
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickToggleVideoCall(ev) {
            if (this.channel.hasPendingRtcRequest) {
                return;
            }
            await this.channel.toggleCall({
                startWithVideo: true,
            });
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeCallButtonTitle() {
            if (!this.channel) {
                return clear();
            }
            if (this.channel.rtc) {
                return this.env._t("Disconnect");
            } else {
                return this.env._t("Join Call");
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeCameraButtonTitle() {
            if (this.messaging.rtc.sendUserVideo) {
                return this.env._t("Stop camera");
            } else {
                return this.env._t("Turn camera on");
            }
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeHeadphoneButtonTitle() {
            if (!this.messaging.rtc.currentRtcSession) {
                return clear();
            }
            if (this.messaging.rtc.currentRtcSession.isDeaf) {
                return this.env._t("Undeafen");
            } else {
                return this.env._t("Deafen");
            }
        },
        /**
         * @private
         */
        _computeIsSmall() {
            return Boolean(this.callView && this.callView.threadView.compact && !this.callView.isFullScreen);
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeMicrophoneButtonTitle() {
            if (!this.messaging.rtc.currentRtcSession) {
                return clear();
            }
            if (this.messaging.rtc.currentRtcSession.isMute) {
                return this.env._t("Unmute");
            } else {
                return this.env._t("Mute");
            }
        },
        /**
         * @returns {string}
         */
        _computeScreenSharingButtonTitle() {
            if (this.messaging.rtc.sendDisplay) {
                return this.env._t("Stop screen sharing");
            } else {
                return this.env._t("Share screen");
            }
        },
    },
    fields: {
        callButtonTitle: attr({
            compute: '_computeCallButtonTitle',
            default: '',
        }),
        callMainView: one('CallMainView', {
            inverse: 'callActionListView',
            readonly: true,
            required: true,
        }),
        callView: one('CallView', {
            related: 'callMainView.callView',
            required: true,
        }),
        cameraButtonTitle: attr({
            compute: '_computeCameraButtonTitle',
            default: '',
        }),
        channel: one('Thread', {
            related: 'callMainView.channel',
            required: true,
        }),
        headphoneButtonTitle: attr({
            compute: '_computeHeadphoneButtonTitle',
            default: '',
        }),
        isSmall: attr({
            compute: '_computeIsSmall',
        }),
        microphoneButtonTitle: attr({
            compute: '_computeMicrophoneButtonTitle',
        }),
        callOptionMenu: one('CallOptionMenu', {
            default: insertAndReplace(),
            inverse: 'callActionListView',
            isCausal: true,
        }),
        screenSharingButtonTitle: attr({
            compute: '_computeScreenSharingButtonTitle',
            default: '',
        }),
    },
});
