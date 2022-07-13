/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';
import { clear, insert, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'CallView',
    identifyingFields: ['threadView'],
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
        _computeAspectRatio() {
            const rtcAspectRatio = this.messaging.rtc.videoConfig && this.messaging.rtc.videoConfig.aspectRatio;
            const aspectRatio = rtcAspectRatio || 16 / 9;
            // if we are in minimized mode (round avatar frames), we treat the cards like squares.
            return this.isMinimized ? 1 : aspectRatio;
        },
        /**
         * @private
         */
        _computeCallSideBarView() {
            if (this.mainParticipantCard && this.hasSidebar && !this.threadView.compact) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         */
        _computeIsMinimized() {
            if (!this.threadView) {
                return true;
            }
            if (this.isFullScreen || this.threadView.compact) {
                return false;
            }
            if (this.mainParticipantCard) {
                return false;
            }
            return !this.channel.rtc || this.channel.videoCount === 0;
        },
        /**
         * @private
         * @returns {string}
         */
         _computeLayoutSettingsTitle() {
            return this.env._t("Change Layout");
        },
        /**
         * @private
         */
        _computeMainParticipantCard() {
            if (!this.messaging || !this.activeRtcSession || !this.threadView || !this.activeRtcSession) {
                return clear();
            }
            return insert({
                rtcSession: replace(this.activeRtcSession),
                channel: replace(this.channel),
            });
        },
        /**
         * @private
         * @returns {string}
         */
        _computeSettingsTitle() {
            return this.env._t("Settings");
        },
        /**
         * @private
         */
        _computeTileParticipantCards() {
            if (!this.threadView) {
                return clear();
            }
            if (this.activeRtcSession && !this.hasSidebar) {
                return clear();
            }
            const tileCards = [];
            for (const rtcSession of this.channel.rtcSessions) {
                if (this.filterVideoGrid && !rtcSession.videoStream) {
                    continue;
                }
                tileCards.push({
                    rtcSession: replace(rtcSession),
                    channel: replace(this.channel),
                });
            }
            for (const member of this.channel.invitedMembers) {
                tileCards.push({
                    invitedMember: replace(member),
                    channel: replace(this.channel),
                });
            }
            return insertAndReplace(tileCards);
        },
        /**
         * @private
         */
        _onChangeRtcChannel() {
            this.deactivateFullScreen();
            this.update({ filterVideoGrid: false });
        },
        /**
         * @private
         */
        _onChangeVideoCount() {
            if (this.channel.videoCount === 0) {
                this.update({ filterVideoGrid: false });
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
        activeRtcSession: one('RtcSession'),
        /**
         * The aspect ratio of the tiles.
         */
        aspectRatio: attr({
            default: 16 / 9,
            compute: '_computeAspectRatio',
        }),
        callMainView: one('CallMainView', {
            default: insertAndReplace(),
            inverse: 'callView',
            isCausal: true,
            readonly: true,
        }),
        callSidebarView: one('CallSidebarView', {
            compute: '_computeCallSideBarView',
            inverse: 'callView',
            isCausal: true,
            readonly: true,
        }),
        channel: one('Thread', {
            related: 'threadView.thread',
            required: true,
        }),
        /**
         * Determines whether we only display the videos or all the participants
         */
        filterVideoGrid: attr({
            default: false,
        }),
        /**
         * Determines if the viewer should have a sidebar.
         */
        hasSidebar: attr({
            default: true,
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
            default: false,
            compute: '_computeIsMinimized',
        }),
        /**
         * Text content that is displayed on title of the layout settings dialog.
         */
        layoutSettingsTitle: attr({
            compute: '_computeLayoutSettingsTitle',
        }),
        /**
         * If set, the card to be displayed as the main card.
         */
        mainParticipantCard: one('CallParticipantCard', {
            compute: '_computeMainParticipantCard',
            inverse: 'callViewAsMainCard',
            isCausal: true,
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
            compute: '_computeSettingsTitle',
        }),
        /**
         * ThreadView on which the call view is attached.
         */
        threadView: one('ThreadView', {
            inverse: 'callView',
            readonly: true,
            required: true,
        }),
        /**
         * List of all participant cards (can either be invitations or rtcSessions).
         */
        tileParticipantCards: many('CallParticipantCard', {
            compute: '_computeTileParticipantCards',
            inverse: 'callViewAsTile',
            isCausal: true,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['channel.rtc'],
            methodName: '_onChangeRtcChannel',
        }),
        new OnChange({
            dependencies: ['channel.videoCount'],
            methodName: '_onChangeVideoCount',
        }),
    ],
});
