/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerPatch({
    name: 'Timer',
    recordMethods: {
        /**
         * @override
         */
        onTimeout() {
            if (this.blurManagerOwnerAsFrameRequest) {
                this.blurManagerOwnerAsFrameRequest.onRequestFrameTimerTimeout();
                return;
            }
            if (this.callMainViewAsShowOverlay) {
                this.callMainViewAsShowOverlay.onShowOverlayTimeout();
                return;
            }
            if (this.chatterOwnerAsAttachmentsLoader) {
                this.chatterOwnerAsAttachmentsLoader.onAttachmentsLoadingTimeout();
                return;
            }
            if (this.messageViewOwnerAsHighlight) {
                this.messageViewOwnerAsHighlight.onHighlightTimerTimeout();
                return;
            }
            if (this.rtcSessionOwnerAsBroadcast) {
                this.rtcSessionOwnerAsBroadcast.onBroadcastTimeout();
                return;
            }
            if (this.threadAsCurrentPartnerInactiveTypingTimerOwner) {
                this.threadAsCurrentPartnerInactiveTypingTimerOwner.onCurrentPartnerInactiveTypingTimeout();
                return;
            }
            if (this.threadAsCurrentPartnerLongTypingTimerOwner) {
                this.threadAsCurrentPartnerLongTypingTimerOwner.onCurrentPartnerLongTypingTimeout();
                return;
            }
            if (this.otherMemberLongTypingInThreadTimerOwner) {
                this.otherMemberLongTypingInThreadTimerOwner.onOtherMemberLongTypingTimeout();
                return;
            }
            if (this.throttleOwner) {
                this.throttleOwner.onTimeout();
                return;
            }
            return this._super();
        },
    },
    fields: {
        blurManagerOwnerAsFrameRequest: one('BlurManager', {
            identifying: true,
            inverse: 'frameRequestTimer',
        }),
        callMainViewAsShowOverlay: one('CallMainView', {
            identifying: true,
            inverse: 'showOverlayTimer',
        }),
        chatterOwnerAsAttachmentsLoader: one('Chatter', {
            identifying: true,
            inverse: 'attachmentsLoaderTimer',
        }),
        duration: {
            compute() {
                if (this.blurManagerOwnerAsFrameRequest) {
                    return Math.floor(1000 / 30); // 30 fps
                }
                if (this.callMainViewAsShowOverlay) {
                    return 3 * 1000;
                }
                if (this.chatterOwnerAsAttachmentsLoader) {
                    return this.messaging.loadingBaseDelayDuration;
                }
                if (this.messageViewOwnerAsHighlight) {
                    return 2 * 1000;
                }
                if (this.rtcSessionOwnerAsBroadcast) {
                    return 3 * 1000;
                }
                if (this.threadAsCurrentPartnerInactiveTypingTimerOwner) {
                    return 5 * 1000;
                }
                if (this.threadAsCurrentPartnerLongTypingTimerOwner) {
                    return 50 * 1000;
                }
                if (this.otherMemberLongTypingInThreadTimerOwner) {
                    return 60 * 1000;
                }
                if (this.throttleOwner) {
                    return this.throttleOwner.duration;
                }
                return this._super();
            },
        },
        messageViewOwnerAsHighlight: one('MessageView', {
            identifying: true,
            inverse: 'highlightTimer',
        }),
        otherMemberLongTypingInThreadTimerOwner: one('OtherMemberLongTypingInThreadTimer', {
            identifying: true,
            inverse: 'timer',
            isCausal: true,
        }),
        rtcSessionOwnerAsBroadcast: one('RtcSession', {
            identifying: true,
            inverse: 'broadcastTimer',
        }),
        threadAsCurrentPartnerInactiveTypingTimerOwner: one('Thread', {
            identifying: true,
            inverse: 'currentPartnerInactiveTypingTimer',
        }),
        threadAsCurrentPartnerLongTypingTimerOwner: one('Thread', {
            identifying: true,
            inverse: 'currentPartnerLongTypingTimer',
        }),
        throttleOwner: one('Throttle', {
            identifying: true,
            inverse: 'cooldownTimer',
        }),
    },
});
