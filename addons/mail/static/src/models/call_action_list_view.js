/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'CallActionListView',
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
        onClickMore(ev) {
            this.update({ moreMenuPopoverView: this.moreMenuPopoverView ? clear() : {} });
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickRejectCall(ev) {
            if (this.thread.hasPendingRtcRequest) {
                return;
            }
            await this.thread.leaveCall();
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
            if (this.thread.hasPendingRtcRequest) {
                return;
            }
            await this.thread.toggleCall();
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickToggleVideoCall(ev) {
            if (this.thread.hasPendingRtcRequest) {
                return;
            }
            await this.thread.toggleCall({
                startWithVideo: true,
            });
        },
    },
    fields: {
        callButtonTitle: attr({
            compute() {
                if (!this.thread) {
                    return clear();
                }
                if (this.thread.rtc) {
                    return this.env._t("Disconnect");
                } else {
                    return this.env._t("Join Call");
                }
            },
            default: '',
        }),
        callMainView: one('CallMainView', {
            identifying: true,
            inverse: 'callActionListView',
        }),
        callView: one('CallView', {
            related: 'callMainView.callView',
            required: true,
        }),
        cameraButtonTitle: attr({
            compute() {
                if (this.messaging.rtc.sendUserVideo) {
                    return this.env._t("Stop camera");
                } else {
                    return this.env._t("Turn camera on");
                }
            },
            default: '',
        }),
        headphoneButtonTitle: attr({
            compute() {
                if (!this.messaging.rtc.currentRtcSession) {
                    return clear();
                }
                if (this.messaging.rtc.currentRtcSession.isDeaf) {
                    return this.env._t("Undeafen");
                } else {
                    return this.env._t("Deafen");
                }
            },
            default: '',
        }),
        isSmall: attr({
            compute() {
                return Boolean(this.callView && this.callView.threadView.compact && !this.callView.isFullScreen);
            },
        }),
        microphoneButtonTitle: attr({
            compute() {
                if (!this.messaging.rtc.currentRtcSession) {
                    return clear();
                }
                if (this.messaging.rtc.currentRtcSession.isMute) {
                    return this.env._t("Unmute");
                } else {
                    return this.env._t("Mute");
                }
            },
        }),
        moreButtonRef: attr(),
        moreMenuPopoverView: one('PopoverView', {
            inverse: 'callActionListViewOwnerAsMoreMenu',
        }),
        screenSharingButtonTitle: attr({
            compute() {
                if (this.messaging.rtc.sendDisplay) {
                    return this.env._t("Stop screen sharing");
                } else {
                    return this.env._t("Share screen");
                }
            },
            default: '',
        }),
        thread: one('Thread', {
            related: 'callMainView.thread',
            required: true,
        }),
    },
});
