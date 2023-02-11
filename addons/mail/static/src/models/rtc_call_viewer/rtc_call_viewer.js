/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one, one2many } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';
import { clear, insert, insertAndReplace, link, unlink } from '@mail/model/model_field_command';

import { isEventHandled, markEventHandled } from '@mail/utils/utils';

function factory(dependencies) {

    class RtcCallViewer extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            this._timeoutId = undefined;
            this.onClick = this.onClick.bind(this);
            this.onLayoutSettingsDialogClosed = this.onLayoutSettingsDialogClosed.bind(this);
            this.onMouseMove = this.onMouseMove.bind(this);
            this.onMouseMoveOverlay = this.onMouseMoveOverlay.bind(this);
            this.onRtcSettingsDialogClosed = this.onRtcSettingsDialogClosed.bind(this);
            this._onFullScreenChange = this._onFullScreenChange.bind(this);
            browser.addEventListener('fullscreenchange', this._onFullScreenChange);
        }

        /**
         * @override
         */
        _willDelete() {
            browser.clearTimeout(this._timeoutId);
            browser.removeEventListener('fullscreenchange', this._onFullScreenChange);
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            this._showOverlay();
        }

        /**
         * @param {MouseEvent} ev
         */
        onLayoutSettingsDialogClosed(ev) {
            this.toggleLayoutMenu();
        }

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
        }

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
            browser.clearTimeout(this._timeoutId);
        }

        /**
         * @param {MouseEvent} ev
         */
        onRtcSettingsDialogClosed(ev) {
            this.messaging.userSetting.rtcConfigurationMenu.toggle();
        }

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
            } catch (e) {
                if (this.exists()) {
                    this.update({ isFullScreen: false });
                }
                this.env.services.notification.notify({
                    message: this.env._t("The FullScreen mode was denied by the browser"),
                    type: 'warning',
                });
            }
        }

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
        }

        toggleLayoutMenu() {
            if (!this.rtcLayoutMenu) {
                this.update({ rtcLayoutMenu: insertAndReplace() });
                return;
            }
            this.update({ rtcLayoutMenu: unlink() });
        }

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
        }

        /**
         * @private
         */
        _computeIsControllerFloating() {
            return (
                this.isFullScreen ||
                this.layout !== "tiled" && !this.threadView.compact
            );
        }

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
        }

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
        }

        /**
         * @private
         * @returns {string}
         */
         _computeLayoutSettingsTitle() {
            return this.env._t("Change Layout");
        }

        /**
         * @private
         */
        _computeMainParticipantCard() {
            if (!this.messaging || !this.threadView) {
                return unlink();
            }
            if (this.messaging.focusedRtcSession && this.messaging.focusedRtcSession.channel === this.threadView.thread) {
                return insert({
                    relationalId: `rtc_session_${this.messaging.focusedRtcSession.localId}_${this.threadView.thread.localId}`,
                    rtcSession: link(this.messaging.focusedRtcSession),
                    channel: link(this.threadView.thread),
                });
            }
            return unlink();
        }

        /**
         * @private
         * @returns {string}
         */
        _computeSettingsTitle() {
            return this.env._t("Settings");
        }

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
                    rtcSession: link(rtcSession),
                    channel: link(this.threadView.thread),
                });
            }
            for (const partner of this.threadView.thread.invitedPartners) {
                if (sessionPartners.has(partner.id)) {
                    continue;
                }
                tileCards.push({
                    relationalId: `invited_partner_${partner.localId}_${this.threadView.thread.localId}`,
                    invitedPartner: link(partner),
                    channel: link(this.threadView.thread),
                });
            }
            for (const guest of this.threadView.thread.invitedGuests) {
                if (sessionGuests.has(guest.id)) {
                    continue;
                }
                tileCards.push({
                    relationalId: `invited_guest_${guest.localId}_${this.threadView.thread.localId}`,
                    invitedGuest: link(guest),
                    channel: link(this.threadView.thread),
                });
            }
            return insertAndReplace(tileCards);
        }

        /**
         * @private
         */
        _debounce(f, { delay = 0 } = {}) {
            browser.clearTimeout(this._timeoutId);
            this._timeoutId = browser.setTimeout(() => {
                if (!this.exists()) {
                    return;
                }
                f();
            }, delay);
        }

        /**
         * @private
         */
        _onChangeRtcChannel() {
            this.deactivateFullScreen();
            this.update({ filterVideoGrid: false });
        }

        /**
         * @private
         */
        _onChangeVideoCount() {
            if (this.threadView.thread.videoCount === 0) {
                this.update({ filterVideoGrid: false });
            }
        }

        /**
         * Shows the overlay (buttons) for a set a mount of time.
         *
         * @private
         */
        _showOverlay() {
            this.update({
                showOverlay: true,
            });
            this._debounce(() => {
                if (!this.exists()) {
                    return;
                }
                this.update({ showOverlay: false });
            }, { delay: 3000 });
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

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
        }

    }

    RtcCallViewer.fields = {
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
        mainParticipantCard: one2one('mail.rtc_call_participant_card', {
            compute: '_computeMainParticipantCard',
            inverse: 'rtcCallViewerOfMainCard',
        }),
        /**
         * The model for the controller (buttons).
         */
        rtcController: one2one('mail.rtc_controller', {
            default: insertAndReplace(),
            readonly: true,
            required: true,
            inverse: 'callViewer',
            isCausal: true,
        }),
        /**
         * The model for the menu to control the layout of the viewer.
         */
        rtcLayoutMenu: one2one('mail.rtc_layout_menu', {
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
        /**
         * ThreadView on which the call viewer is attached.
         */
        threadView: one2one('mail.thread_view', {
            inverse: 'rtcCallViewer',
            readonly: true,
            required: true,
        }),
        /**
         * List of all participant cards (can either be invitations or rtcSessions).
         */
        tileParticipantCards: one2many('mail.rtc_call_participant_card', {
            compute: '_computeTileParticipantCards',
            inverse: 'rtcCallViewerOfTile',
        }),
    };
    RtcCallViewer.identifyingFields = ['threadView'];
    RtcCallViewer.onChanges = [
        new OnChange({
            dependencies: ['threadView.thread.rtc'],
            methodName: '_onChangeRtcChannel',
        }),
        new OnChange({
            dependencies: ['threadView.thread.videoCount'],
            methodName: '_onChangeVideoCount',
        }),
    ];
    RtcCallViewer.modelName = 'mail.rtc_call_viewer';

    return RtcCallViewer;
}

registerNewModel('mail.rtc_call_viewer', factory);
