/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';
import { clear, insert, insertAndReplace, replace } from '@mail/model/model_field_command';

import { isEventHandled, markEventHandled } from '@mail/utils/utils';

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
         * Finds a tile layout and dimensions that respects param0.aspectRatio while maximizing
         * the total area covered by the tiles within the specified container dimensions.
         *
         * @param {Object} param0
         * @param {number} [param0.aspectRatio]
         * @param {number} param0.containerHeight
         * @param {number} param0.containerWidth
         * @param {number} param0.tileCount
         */
        calculateTessellation({ aspectRatio = 1, containerHeight, containerWidth, tileCount }) {
            let optimalLayout = {
                area: 0,
                cols: 0,
                tileHeight: 0,
                tileWidth: 0,
            };

            for (let columnCount = 1; columnCount <= tileCount; columnCount++) {
                const rowCount = Math.ceil(tileCount / columnCount);
                const potentialHeight = containerWidth / (columnCount * aspectRatio);
                const potentialWidth = containerHeight / rowCount;
                let tileHeight;
                let tileWidth;
                if (potentialHeight > potentialWidth) {
                    tileHeight = Math.floor(potentialWidth);
                    tileWidth = Math.floor(tileHeight * aspectRatio);
                } else {
                    tileWidth = Math.floor(containerWidth / columnCount);
                    tileHeight = Math.floor(tileWidth / aspectRatio);
                }
                const area = tileHeight * tileWidth;
                if (area <= optimalLayout.area) {
                    continue;
                }
                optimalLayout = {
                    area,
                    tileHeight,
                    tileWidth,
                };
            }
            return optimalLayout;
        },
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            this._showOverlay();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickHideSidebar(ev) {
            this.update({ hasSidebar: false });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickShowSidebar(ev) {
            this.update({ hasSidebar: true });
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
            if (isEventHandled(ev, 'CallView.MouseMoveOverlay')) {
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
            markEventHandled(ev, 'CallView.MouseMoveOverlay');
            this.update({
                showOverlay: true,
                showOverlayTimer: clear(),
            });
        },
        /**
         * @param {MouseEvent} ev
         */
        onRtcSettingsDialogClosed(ev) {
            this.messaging.userSetting.callSettingsMenu.toggle();
        },
        onShowOverlayTimeout() {
            this.update({ showOverlay: false });
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
        _computeIsControllerFloating() {
            return Boolean(this.isFullScreen || this.activeRtcSession && !this.threadView.compact);
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
            return !this.threadView.thread.rtc || this.threadView.thread.videoCount === 0;
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
                channel: replace(this.threadView.thread),
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
            const sessionPartners = new Set();
            const sessionGuests = new Set();
            for (const rtcSession of this.threadView.thread.rtcSessions) {
                if (this.filterVideoGrid && !rtcSession.videoStream) {
                    continue;
                }
                rtcSession.partner && sessionPartners.add(rtcSession.partner.id);
                rtcSession.guest && sessionPartners.add(rtcSession.guest.id);
                tileCards.push({
                    rtcSession: replace(rtcSession),
                    channel: replace(this.threadView.thread),
                });
            }
            for (const partner of this.threadView.thread.invitedPartners) {
                if (sessionPartners.has(partner.id)) {
                    continue;
                }
                tileCards.push({
                    invitedPartner: replace(partner),
                    channel: replace(this.threadView.thread),
                });
            }
            for (const guest of this.threadView.thread.invitedGuests) {
                if (sessionGuests.has(guest.id)) {
                    continue;
                }
                tileCards.push({
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
                showOverlayTimer: [clear(), insertAndReplace()],
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
    },
    fields: {
        /**
         * The rtc session that is the focus/spotlight of the viewer.
         */
        activeRtcSession: one('RtcSession'),
        /**
         * The aspect ratio of the tiles.
         */
        aspectRatio: attr({
            default: 16 / 9,
            compute: '_computeAspectRatio',
        }),
        tileContainerRef: attr(),
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
         * Text content that is displayed on title of the layout settings dialog.
         */
        layoutSettingsTitle: attr({
            compute: '_computeLayoutSettingsTitle',
        }),
        /**
         * If set, the card to be displayed as the "main/spotlight" card.
         */
        mainParticipantCard: one('CallParticipantCard', {
            compute: '_computeMainParticipantCard',
            inverse: 'callViewOfMainCard',
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
         * The model for the controller (buttons).
         */
        callActionListView: one('CallActionListView', {
            default: insertAndReplace(),
            readonly: true,
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
         * Determines if we show the overlay with the control buttons.
         */
        showOverlay: attr({
            default: true,
        }),
        showOverlayTimer: one('Timer', {
            inverse: 'callViewAsShowOverlay',
            isCausal: true,
        }),
        /**
         * ThreadView on which the call view is attached.
         */
        threadView: one('ThreadView', {
            inverse: 'callView',
            readonly: true,
            required: true,
        }),
        tileHeight: attr({
            default: 0,
        }),
        /**
         * List of all participant cards (can either be invitations or rtcSessions).
         */
        tileParticipantCards: many('CallParticipantCard', {
            compute: '_computeTileParticipantCards',
            inverse: 'callViewOfTile',
            isCausal: true,
        }),
        tileWidth: attr({
            default: 0,
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
