/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

import { isEventHandled, markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'CallMainView',
    identifyingFields: ['callView'],
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
            this.callView.update({ hasSidebar: false });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickShowSidebar(ev) {
            this.callView.update({ hasSidebar: true });
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
            if (isEventHandled(ev, 'CallMainView.MouseMoveOverlay')) {
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
            markEventHandled(ev, 'CallMainView.MouseMoveOverlay');
            this.update({
                showOverlay: true,
                showOverlayTimer: clear(),
            });
        },
        onShowOverlayTimeout() {
            this.update({ showOverlay: false });
        },

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _computeIsControllerFloating() {
            return Boolean(this.callView.isFullScreen || this.callView.activeRtcSession && !this.callView.threadView.compact);
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
    },
    fields: {
        /**
         * The model for the controller (buttons).
         */
        callActionListView: one('CallActionListView', {
            default: insertAndReplace(),
            inverse: 'callMainView',
            isCausal: true,
            readonly: true,
        }),
        callView: one('CallView', {
            inverse: 'callMainView',
            required: true,
            readonly: true,
        }),
        channel: one('Thread', {
            related: 'callView.channel',
            required: true,
        }),
        /**
         * Determines if the controller is an overlay or a bottom bar.
         */
        isControllerFloating: attr({
            default: false,
            compute: '_computeIsControllerFloating',
        }),
        /**
         * Determines if we show the overlay with the control buttons.
         */
        showOverlay: attr({
            default: true,
        }),
        showOverlayTimer: one('Timer', {
            inverse: 'callMainViewAsShowOverlay',
            isCausal: true,
        }),
        tileContainerRef: attr(),
        tileHeight: attr({
            default: 0,
        }),
        tileWidth: attr({
            default: 0,
        }),
    },
});
