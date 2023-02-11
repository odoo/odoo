/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Dialog from 'web.OwlDialog';

const { Component, useState } = owl;
const { useRef } = owl.hooks;

const components = {
    Dialog,
};

// TODO a nice-to-have would be a resize handle under the videos.

export class RtcCallViewer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.state = useState({
            tileWidth: 0,
            tileHeight: 0,
            columnCount: 0,
        });
        this.tileContainerRef = useRef('tileContainer');
        useUpdate({ func: () => this._update() });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.rtc_call_viewer}
     */
    get rtcCallViewer() {
        return this.messaging.models['mail.rtc_call_viewer'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Finds a tile layout and dimensions that respects param0.aspectRatio while maximizing
     * the total area covered by the tiles within the specified container dimensions.
     *
     * @private
     * @param {Object} param0
     * @param {number} [param0.aspectRatio]
     * @param {number} param0.containerHeight
     * @param {number} param0.containerWidth
     * @param {number} param0.tileCount
     */
    _computeTessellation({ aspectRatio = 1, containerHeight, containerWidth, tileCount }) {
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
                columnCount,
                tileHeight,
                tileWidth,
            };
        }
        return optimalLayout;
    }

    /**
     * @private
     */
    _setTileLayout() {
        if (!this.rtcCallViewer) {
            return;
        }
        if (!this.el) {
            return;
        }
        if (!this.tileContainerRef.el) {
            return;
        }
        const { width, height } = this.tileContainerRef.el.getBoundingClientRect();

        const { tileWidth, tileHeight, columnCount } = this._computeTessellation({
            aspectRatio: this.rtcCallViewer.aspectRatio,
            containerHeight: height,
            containerWidth: width,
            tileCount: this.tileContainerRef.el.children.length,
        });

        this.state.tileWidth = tileWidth;
        this.state.tileHeight = tileHeight;
        this.state.columnCount = columnCount;
    }

    /**
     * @private
     */
    _update() {
        this._setTileLayout();
    }

}

Object.assign(RtcCallViewer, {
    components,
    props: {
        localId: String,
    },
    template: 'mail.RtcCallViewer',
});

registerMessagingComponent(RtcCallViewer);
