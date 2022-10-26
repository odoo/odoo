/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'CallView',
    lifecycleHooks: {
        _created() {
            browser.addEventListener('fullscreenchange', this._onFullScreenChange);
        },
        _willDelete() {
            browser.removeEventListener('fullscreenchange', this._onFullScreenChange);
        },
    },
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onRtcSettingsDialogClosed(ev) {
            this.messaging.userSetting.callSettingsMenu.toggle();
        },
        async activateFullScreen() {
            const el = document.body;
            try {
                if (el.requestFullscreen) {
                    await el.requestFullscreen();
                } else if (el.mozRequestFullScreen) {
                    await el.mozRequestFullScreen();
                } else if (el.webkitRequestFullscreen) {
                    await el.webkitRequestFullscreen();
                }
                if (this.exists()) {
                    this.update({ isFullScreen: true });
                }
            } catch (_e) {
                if (this.exists()) {
                    this.update({ isFullScreen: false });
                }
                this.messaging.notify({
                    message: this.env._t("The FullScreen mode was denied by the browser"),
                    type: 'warning',
                });
            }
        },
        async deactivateFullScreen() {
            const fullScreenElement = document.webkitFullscreenElement || document.fullscreenElement;
            if (fullScreenElement) {
                if (document.exitFullscreen) {
                    await document.exitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    await document.mozCancelFullScreen();
                } else if (document.webkitCancelFullScreen) {
                    await document.webkitCancelFullScreen();
                }
            }
            if (this.exists()) {
                this.update({ isFullScreen: false });
            }
        },
        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _onChangeRtcChannel() {
            this.deactivateFullScreen();
            if (!this.thread && !this.thread.rtc) {
                this.channel.update({ showOnlyVideo: false });
            }
        },
        /**
         * @private
         */
        _onChangeVideoCount() {
            if (this.thread.videoCount === 0) {
                this.channel.update({ showOnlyVideo: false });
            }
        },
        /**
         * @private
         */
        _onFullScreenChange() {
            const fullScreenElement = document.webkitFullscreenElement || document.fullscreenElement;
            if (fullScreenElement) {
                this.update({ isFullScreen: true });
                return;
            }
            this.update({ isFullScreen: false });
        },
    },
    fields: {
        /**
         * The rtc session that is the main card of the view.
         */
        activeRtcSession: one('RtcSession', {
            related: 'channel.activeRtcSession',
        }),
        /**
         * The aspect ratio of the tiles.
         */
        aspectRatio: attr({
            compute() {
                const rtcAspectRatio = this.messaging.rtc.videoConfig && this.messaging.rtc.videoConfig.aspectRatio;
                const aspectRatio = rtcAspectRatio || 16 / 9;
                // if we are in minimized mode (round avatar frames), we treat the cards like squares.
                return this.isMinimized ? 1 : aspectRatio;
            },
            default: 16 / 9,
        }),
        callMainView: one('CallMainView', {
            default: {},
            inverse: 'callView',
            readonly: true,
        }),
        callSidebarView: one('CallSidebarView', {
            compute() {
                if (this.activeRtcSession && this.isSidebarOpen && !this.threadView.compact) {
                    return {};
                }
                return clear();
            },
            inverse: 'callView',
        }),
        channel: one('Channel', {
            related: 'thread.channel',
        }),
        filteredChannelMembers: many('ChannelMember', {
            compute() {
                if (!this.channel) {
                    return clear();
                }
                const channelMembers = [];
                for (const channelMember of this.channel.callParticipants) {
                    if (this.channel.showOnlyVideo && this.thread.videoCount > 0 && !channelMember.isStreaming) {
                        continue;
                    }
                    channelMembers.push(channelMember);
                }
                return channelMembers;
            },
        }),
        /**
         * Determines if the viewer should be displayed fullScreen.
         */
        isFullScreen: attr({
            default: false,
        }),
        /**
         * Determines if the tiles are in a minimized format:
         * small circles instead of cards, smaller display area.
         */
        isMinimized: attr({
            compute() {
                if (!this.threadView || !this.thread) {
                    return true;
                }
                if (this.isFullScreen || this.threadView.compact) {
                    return false;
                }
                if (this.activeRtcSession) {
                    return false;
                }
                return !this.thread.rtc || this.thread.videoCount === 0;
            },
            default: false,
        }),
        isSidebarOpen: attr({
            default: true,
        }),
        /**
         * Text content that is displayed on title of the layout settings dialog.
         */
        layoutSettingsTitle: attr({
            compute() {
                return this.env._t("Change Layout");
            },
        }),
        /**
         * All the participant cards of the call viewer (main card and tile cards).
         * this is a technical inverse to distinguish from the other relation 'tileParticipantCards'.
         */
        participantCards: many('CallParticipantCard', {
            inverse: 'callView',
            isCausal: true,
        }),
        /**
         * Text content that is displayed on title of the settings dialog.
         */
        settingsTitle: attr({
            compute() {
                return this.env._t("Settings");
            },
        }),
        thread: one('Thread', {
            related: 'threadView.thread',
            required: true,
        }),
        /**
         * ThreadView on which the call view is attached.
         */
        threadView: one('ThreadView', {
            identifying: true,
            inverse: 'callView',
        }),
    },
    onChanges: [
        {
            dependencies: ['thread.rtc'],
            methodName: '_onChangeRtcChannel',
        },
        {
            dependencies: ['thread.videoCount'],
            methodName: '_onChangeVideoCount',
        },
    ],
});
