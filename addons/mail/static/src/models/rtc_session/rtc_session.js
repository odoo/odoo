/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one, one2many } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

function factory(dependencies) {

    class RtcSession extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            this._timeoutId = undefined;
        }

        /**
         * @override
         */
        _willDelete() {
            this.reset();
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * restores the session to its default values
         */
        reset() {
            this._timeoutId && browser.clearTimeout(this._timeoutId);
            this._removeAudio();
            this.removeVideo();
            this.update({
                audioElement: clear(),
                isTalking: clear(),
            });
        }

        /**
         * cleanly removes the video stream of the session
         */
        removeVideo() {
            if (this.videoStream) {
                for (const track of this.videoStream.getTracks() || []) {
                    track.stop();
                }
            }
            this.update({
                videoStream: clear(),
            });
        }

        /**
         * @param {Object} param0
         * @param {MediaStream} param0.audioStream
         * @param {boolean} param0.isMuted
         * @param {boolean} param0.isTalking
         */
        async setAudio({ audioStream, isMuted, isTalking }) {
            const audioElement = this.audioElement || new window.Audio();
            try {
                audioElement.srcObject = audioStream;
            } catch (error) {
                this.update({ isAudioInError: true });
                console.error(error);
            }
            audioElement.load();
            if (this.partner && this.partner.volumeSetting) {
                audioElement.volume = this.partner.volumeSetting.volume;
            } else if (this.guest && this.guest.volumeSetting) {
                audioElement.volume = this.guest.volumeSetting.volume;
            } else {
                audioElement.volume = this.volume;
            }
            audioElement.muted = this.messaging.rtc.currentRtcSession.isDeaf;
            // Using both autoplay and play() as safari may prevent play() outside of user interactions
            // while some browsers may not support or block autoplay.
            audioElement.autoplay = true;
            this.update({
                audioElement,
                audioStream,
                isMuted,
                isTalking,
            });
            try {
                await audioElement.play();
                if (!this.exists()) {
                    return;
                }
                this.update({ isAudioInError: false });
            } catch (error) {
                if (typeof error === 'object' && error.name === 'NotAllowedError') {
                    // Ignored as some browsers may reject play() calls that do not
                    // originate from a user input.
                    return;
                }
                if (this.exists()) {
                    this.update({ isAudioInError: true });
                }
                console.error(error);
            }
        }

        /**
         * @param {number} volume
         */
        setVolume(volume) {
            /**
             * Manually updating the volume field as it will not update based on
             * the change of the volume property of the audioElement alone.
             */
            this.update({ volume });
            if (this.audioElement) {
                this.audioElement.volume = volume;
            }
            if (this.isOwnSession) {
                return;
            }
            if (this.partner && this.partner.volumeSetting) {
                this.partner.volumeSetting.update({ volume });
            }
            if (this.guest && this.guest.volumeSetting) {
                this.guest.volumeSetting.update({ volume });
            }
            if (this.messaging.isCurrentUserGuest) {
                return;
            }
            this.messaging.userSetting.saveVolumeSetting({
                partnerId: this.partner && this.partner.id,
                guestId: this.guest && this.guest.id,
                volume,
            });
        }

        /**
         * Toggles the deaf state of the current session, this must be a session
         * of the current partner.
         */
        async toggleDeaf() {
            if (!this.rtc) {
                return;
            }
            this.updateAndBroadcast({
                isDeaf: !this.isDeaf,
            });
            for (const session of this.messaging.models['mail.rtc_session'].all()) {
                if (!session.audioElement) {
                    continue;
                }
                session.audioElement.muted = this.isDeaf;
            }
            if (this.channel.rtc) {
                /**
                 * Ensures that the state of the microphone matches the deaf state
                 * and notifies peers.
                 */
                await this.async(() => this.channel.rtc.toggleMicrophone({
                    requestAudioDevice: false,
                }));
            }
        }

        /**
         * updates the record and notifies the server of the change
         *
         * @param {Object} data
         */
        updateAndBroadcast(data) {
            if (!this.rtc) {
                return;
            }
            this.update(data);
            this._debounce(async () => {
                if (!this.exists()) {
                    return;
                }
                await this.async(() => {
                    this.env.services.rpc(
                        {
                            route: '/mail/rtc/session/update_and_broadcast',
                            params: {
                                session_id: this.id,
                                values: {
                                    is_camera_on: this.isCameraOn,
                                    is_deaf: this.isDeaf,
                                    is_muted: this.isMuted,
                                    is_screen_sharing_on: this.isScreenSharingOn,
                                },
                            },
                        },
                        { shadow: true }
                    );
                });
            }, 3000);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            if (!this.channel) {
                return;
            }
            if (this.partner) {
                return `/mail/channel/${this.channel.id}/partner/${this.partner.id}/avatar_128`;
            }
            if (this.guest) {
                return `/mail/channel/${this.channel.id}/guest/${this.guest.id}/avatar_128?unique=${this.guest.name}`;
            }
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsOwnSession() {
            if (!this.messaging) {
                return;
            }
            return (this.partner && this.messaging.currentPartner === this.partner) ||
                (this.guest && this.messaging.currentGuest === this.guest);
        }

        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            if (this.partner) {
                return this.partner.name;
            }
            if (this.guest) {
                return this.guest.name;
            }
        }

        /**
         * @private
         * @returns {string}
         */
        _computePeerToken() {
            return String(this.id);
        }

        /**
         * @private
         * @returns {number} float
         */
        _computeVolume() {
            if (this.partner && this.partner.volumeSetting) {
                return this.partner.volumeSetting.volume;
            } else if (this.guest && this.guest.volumeSetting) {
                return this.guest.volumeSetting.volume;
            }
            if (this.audioElement) {
                return this.audioElement.volume;
            }
        }

        /**
         * @private
         */
        _debounce(f, delay) {
            this._timeoutId && browser.clearTimeout(this._timeoutId);
            this._timeoutId = browser.setTimeout(() => {
                if (!this.exists()) {
                    return;
                }
                f();
            }, delay);
        }

        /**
         * cleanly removes the audio stream of the session
         *
         * @private
         */
        _removeAudio() {
            if (this.audioStream) {
                for (const track of this.audioStream.getTracks() || []) {
                    track.stop();
                }
            }
            if (this.audioElement) {
                this.audioElement.pause();
                try {
                    this.audioElement.srcObject = undefined;
                } catch (error) {
                    // ignore error during remove, the value will be overwritten at next usage anyway
                }
            }
            this.update({
                audioStream: clear(),
                isAudioInError: false,
            });
        }

    }

    RtcSession.fields = {
        /**
         * HTMLAudioElement that plays and control the audioStream of the user,
         * it is not mounted on the DOM as it can operate from the JS.
         */
        audioElement: attr(),
        /**
         * MediaStream
         */
        audioStream: attr(),
        /**
         * The relative url of the image that represents the session.
         */
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
        }),
        /**
         * The mail.channel of the session, rtc sessions are part and managed by
         * mail.channel
         */
        channel: many2one('mail.thread', {
            inverse: 'rtcSessions',
        }),
        /**
         * State of the connection with this session, uses RTCPeerConnection.iceConnectionState
         * once a peerConnection has been initialized.
         */
        connectionState: attr({
            default: 'Waiting for the peer to send a RTC offer',
        }),
        guest: many2one('mail.guest', {
            inverse: 'rtcSessions',
        }),
        /**
         * Id of the record on the server.
         */
        id: attr({
            readonly: true,
            required: true,
        }),
        /**
         * Channels on which this session is inviting the current partner,
         * this serves as an explicit inverse as it seems to confuse it with
         * other session-channel relations otherwise.
         */
        calledChannels: one2many('mail.thread', {
            inverse: 'rtcInvitingSession',
        }),
        /**
         * States whether there is currently an error with the audio element.
         */
        isAudioInError: attr({
            default: false,
        }),
        /**
         * Determines if the user is broadcasting a video from a user device (camera).
         */
        isCameraOn: attr({
            default: false,
        }),
        /**
         * Determines if the user is deafened, which means that all incoming
         * audio tracks are disabled.
         */
        isDeaf: attr({
            default: false,
        }),
        /**
         * Determines if the user's microphone is in a muted state, which
         * means that they cannot send sound regardless of the push to talk or
         * voice activation (isTalking) state.
         */
        isMuted: attr({
            default: false,
        }),
        /**
         * Determines if the session is a session of the current partner.
         * This can be true for many sessions, as one user can have multiple
         * sessions active across several tabs, browsers and devices.
         * To determine if this session is the active session of this tab,
         * use this.rtc instead.
         */
        isOwnSession: attr({
            compute: '_computeIsOwnSession',
        }),
        /**
         * Determines if the user is sharing their screen.
         */
        isScreenSharingOn: attr({
            default: false,
        }),
        /**
         * Determines if the user is currently talking, which is based on
         * voice activation or push to talk.
         */
        isTalking: attr({
            default: false,
        }),
        /**
         * Name of the session, based on the partner name if set.
         */
        name: attr({
            compute: '_computeName',
        }),
        /**
         * If set, the partner who owns this rtc session,
         * there can be multiple rtc sessions per partner if the partner
         * has open sessions in multiple channels, but only one session per
         * channel is allowed.
         */
        partner: many2one('mail.partner', {
            inverse: 'rtcSessions',
        }),
        /**
         * Token to identify the session, it is currently just the toString
         * id of the record.
         */
        peerToken: attr({
            compute: '_computePeerToken',
        }),
        /**
         * If set, this session is the session of the current user and is in the active RTC call.
         * This information is distinct from this.isOwnSession as there can be other
         * sessions from other channels with the same partner (sessions opened from different
         * tabs or devices).
         */
        rtc: one2one('mail.rtc', {
            inverse: 'currentRtcSession',
        }),
        /**
         * MediaStream of the user's video.
         *
         * Should be divided into userVideoStream and displayStream,
         * once we allow both share and cam feeds simultaneously.
         */
        videoStream: attr(),
        /**
         * The volume of the audio played from this session.
         */
        volume: attr({
            default: 0.5,
            compute: '_computeVolume',
        }),
    };
    RtcSession.identifyingFields = ['id'];
    RtcSession.modelName = 'mail.rtc_session';

    return RtcSession;
}

registerNewModel('mail.rtc_session', factory);
