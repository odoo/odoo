/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';
import { clear, insert, insertAndReplace, replace } from '@mail/model/model_field_command';

import { isEventHandled, markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'RtcCallViewer',
    identifyingFields: ['threadView'],
    lifecycleHooks: {
        _created() {
            browser.addEventListener('fullscreenchange', this._onFullScreenChange);
        },
        _willDelete() {
            browser.clearTimeout(this.showOverlayTimeout);
            browser.removeEventListener('fullscreenchange', this._onFullScreenChange);
        },
    },
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            this._showOverlay();
        },
        /**
         * @param {MouseEvent} ev
         */
        onLayoutSettingsDialogClosed(ev) {
            this.toggleLayoutMenu();
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseleave(ev) {
            if (ev.relatedTarget && ev.relatedTarget.closest('.o_CallActionList_popover')) {
                // the overlay should not be hidden when the cursor leaves to enter the controller popover
                return;
            }
            if (!this.exists()) {
                return;
            }
            this.update({ showOverlay: false });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseMove(ev) {
            if (!this.exists()) {
                return;
            }
            if (isEventHandled(ev, 'RtcCallViewer.MouseMoveOverlay')) {
                return;
            }
            this._showOverlay();
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseMoveOverlay(ev) {
            if (!this.exists()) {
                return;
            }
            markEventHandled(ev, 'RtcCallViewer.MouseMoveOverlay');
            this.update({
                showOverlay: true,
            });
            browser.clearTimeout(this.showOverlayTimeout);
        },
        /**
         * @param {MouseEvent} ev
         */
        onRtcSettingsDialogClosed(ev) {
            this.messaging.userSetting.rtcConfigurationMenu.toggle();
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
        toggleLayoutMenu() {
            if (!this.rtcLayoutMenu) {
                this.update({ rtcLayoutMenu: insertAndReplace() });
                return;
            }
            this.update({ rtcLayoutMenu: clear() });
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
        _computeIsControllerFloating() {
            return (
                this.isFullScreen ||
                this.layout !== "tiled" && !this.threadView.compact
            );
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
            return !this.threadView.thread.rtc || this.threadView.thread.videoCount === 0;
        },
        /**
         * @private
         */
        _computeLayout() {
            if (!this.threadView) {
                return 'tiled';
            }
            if (this.isMinimized) {
                return 'tiled';
            }
            if (!this.threadView.thread.rtc) {
                return 'tiled';
            }
            if (!this.mainParticipantCard) {
                return 'tiled';
            }
            if (
                this.threadView.thread.rtcSessions.length +
                this.threadView.thread.invitedPartners.length +
                this.threadView.thread.invitedGuests.length < 2
            ) {
                return "tiled";
            }
            if (this.threadView.compact && this.messaging.userSetting.rtcLayout === 'sidebar') {
                return 'spotlight';
            }
            return this.messaging.userSetting.rtcLayout;
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
            if (!this.messaging || !this.threadView) {
                return clear();
            }
            if (this.messaging.focusedRtcSession && this.messaging.focusedRtcSession.channel === this.threadView.thread) {
                return insert({
                    relationalId: `rtc_session_${this.messaging.focusedRtcSession.localId}_${this.threadView.thread.localId}`,
                    rtcSession: replace(this.messaging.focusedRtcSession),
                    channel: replace(this.threadView.thread),
                });
            }
            return clear();
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
            const tileCards = [];
            const sessionPartners = new Set();
            const sessionGuests = new Set();
            for (const rtcSession of this.threadView.thread.rtcSessions) {
                rtcSession.partner && sessionPartners.add(rtcSession.partner.id);
                rtcSession.guest && sessionPartners.add(rtcSession.guest.id);
                tileCards.push({
                    relationalId: `rtc_session_${rtcSession.localId}_${this.threadView.thread.localId}`,
                    rtcSession: replace(rtcSession),
                    channel: replace(this.threadView.thread),
                });
            }
            for (const partner of this.threadView.thread.invitedPartners) {
                if (sessionPartners.has(partner.id)) {
                    continue;
                }
                tileCards.push({
                    relationalId: `invited_partner_${partner.localId}_${this.threadView.thread.localId}`,
                    invitedPartner: replace(partner),
                    channel: replace(this.threadView.thread),
                });
            }
            for (const guest of this.threadView.thread.invitedGuests) {
                if (sessionGuests.has(guest.id)) {
                    continue;
                }
                tileCards.push({
                    relationalId: `invited_guest_${guest.localId}_${this.threadView.thread.localId}`,
                    invitedGuest: replace(guest),
                    channel: replace(this.threadView.thread),
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
            if (this.threadView.thread.videoCount === 0) {
                this.update({ filterVideoGrid: false });
            }
        },
        /**
         * Shows the overlay (buttons) for a set a mount of time.
         *
         * @private
         */
        _showOverlay() {
            this.update({
                showOverlay: true,
            });
            browser.clearTimeout(this.showOverlayTimeout);
            this.update({
                showOverlayTimeout: browser.setTimeout(this._onShowOverlayTimeout, 3000),
            });
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
        /**
         * @private
         */
        _onShowOverlayTimeout() {
            if (!this.exists()) {
                return;
            }
            this.update({ showOverlay: false });
        },
    },
    fields: {
        /**
         * The aspect ratio of the tiles.
         */
        aspectRatio: attr({
            default: 16 / 9,
            compute: '_computeAspectRatio',
        }),
        /**
         * Determines whether we only display the videos or all the participants
         */
        filterVideoGrid: attr({
            default: false,
        }),
        /**
         * Determines if the controller is an overlay or a bottom bar.
         */
        isControllerFloating: attr({
            default: false,
            compute: '_computeIsControllerFloating',
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
         * Determines the layout use for the tiling of the participant cards.
         */
        layout: attr({
            default: 'tiled',
            compute: '_computeLayout',
        }),
        /**
         * Text content that is displayed on title of the layout settings dialog.
         */
        layoutSettingsTitle: attr({
            compute: '_computeLayoutSettingsTitle',
        }),
        /**
         * If set, the card to be displayed as the "main/spotlight" card.
         */
        mainParticipantCard: one('RtcCallParticipantCard', {
            compute: '_computeMainParticipantCard',
            inverse: 'rtcCallViewerOfMainCard',
        }),
        /**
         * The model for the controller (buttons).
         */
        callActionListView: one('CallActionListView', {
            default: insertAndReplace(),
            readonly: true,
            inverse: 'callViewer',
            isCausal: true,
        }),
        /**
         * The model for the menu to control the layout of the viewer.
         */
        rtcLayoutMenu: one('RtcLayoutMenu', {
            inverse: 'callViewer',
            isCausal: true,
        }),
        /**
         * Text content that is displayed on title of the settings dialog.
         */
        settingsTitle: attr({
            compute: '_computeSettingsTitle',
        }),
        /**
         * Determines if we show the overlay with the control buttons.
         */
        showOverlay: attr({
            default: true,
        }),
        showOverlayTimeout: attr(),
        /**
         * ThreadView on which the call viewer is attached.
         */
        threadView: one('ThreadView', {
            inverse: 'rtcCallViewer',
            readonly: true,
            required: true,
        }),
        /**
         * List of all participant cards (can either be invitations or rtcSessions).
         */
        tileParticipantCards: many('RtcCallParticipantCard', {
            compute: '_computeTileParticipantCards',
            inverse: 'rtcCallViewerOfTile',
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['threadView.thread.rtc'],
            methodName: '_onChangeRtcChannel',
        }),
        new OnChange({
            dependencies: ['threadView.thread.videoCount'],
            methodName: '_onChangeVideoCount',
        }),
    ],
});
