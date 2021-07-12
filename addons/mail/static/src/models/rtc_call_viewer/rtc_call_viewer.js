/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class RtcCallViewer extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            const res = super._created(...arguments);
            this._timeoutId = undefined;
            return res;
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        onClick() {
            this._showOverlay();
        }

        onMouseMove() {
            this._showOverlay();
        }

        onMouseMoveOverlay() {
            this.update({
                showOverlay: true,
            });
            this._timeoutId && browser.clearTimeout(this._timeoutId);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _computeAspectRatio() {
            const rtcAspectRatio = this.messaging.mailRtc.videoConfig && this.messaging.mailRtc.videoConfig.ideal;
            const aspectRatio = rtcAspectRatio || 16 / 9;
            // if we are in minimized mode (round avatar frames), we treat the cards like squares.
            return this.isMinimized ? 1 : aspectRatio;
        }

        /**
         * @private
         */
        _computeFilterVideoGrid() {
            const setting = this.messaging && this.messaging.userSetting;
            const mailRtc = this.threadView && this.threadView.thread.mailRtc;
            return mailRtc && setting.rtcFilterVideoGrid;
        }


        /**
         * @private
         */
        _computeIsMinimized() {
            if (!this.threadView) {
                return true;
            }
            if (this.messaging.userSetting.isRtcCallViewerFullScreen || this.threadView.compact) {
                return false;
            }
            return !this.threadView.thread.mailRtc || this.threadView.thread.videoCount === 0;
        }

        /**
         * @private
         */
        _computeLayout() {
            if (!this.threadView) {
                return 'tiled';
            }
            if (!this.threadView.thread.mailRtc) {
                return 'tiled';
            }
            if (!this.threadView.thread.videoCount || !this.messaging.focusedRtcSession) {
                return 'tiled';
            }
            if (this.threadView.thread.rtcSessions.length < 2) {
                return 'tiled';
            }
            if (this.threadView.compact && this.messaging.userSetting.rtcLayout === 'sidebar') {
                return 'spotlight';
            }
            return this.messaging.userSetting.rtcLayout;
        }

        /**
         * @private
         */
        _debounce(f, { delay = 0 } = {}) {
            this._timeoutId && browser.clearTimeout(this._timeoutId);
            this._timeoutId = browser.setTimeout(() => {
                if (!this.exists()) {
                    return;
                }
                f();
            }, delay);
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
            if (this.threadView.compact && !this.messaging.userSetting.isRtcCallViewerFullScreen) {
                return;
            }
            this._debounce(() => {
                this.update({ showOverlay: false });
            }, { delay: 3000 });
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
            compute: '_computeFilterVideoGrid',
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
            required: true,
        }),
    };
    RtcCallViewer.modelName = 'mail.rtc_call_viewer';

    return RtcCallViewer;
}

registerNewModel('mail.rtc_call_viewer', factory);
