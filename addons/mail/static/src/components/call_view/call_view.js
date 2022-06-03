/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Dialog from 'web.OwlDialog';

const { Component, useState } = owl;

const components = {
    Dialog,
};

// TODO a nice-to-have would be a resize handle under the videos.

export class CallView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'tileContainerRef', refName: 'tileContainer', });
        this.state = useState({
            tileWidth: 0,
            tileHeight: 0,
            columnCount: 0,
        });
        useUpdate({ func: () => this._update() });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {CallView}
     */
    get callView() {
        return this.props.record;
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
        if (!this.root.el) {
            return;
        }
        if (!this.callView.tileContainerRef.el) {
            return;
        }
        const { width, height } = this.callView.tileContainerRef.el.getBoundingClientRect();

        const { tileWidth, tileHeight, columnCount } = this._computeTessellation({
            aspectRatio: this.callView.aspectRatio,
            containerHeight: height,
            containerWidth: width,
            tileCount: this.callView.tileContainerRef.el.children.length,
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

Object.assign(CallView, {
    components,
    props: { record: Object },
    template: 'mail.CallView',
});

registerMessagingComponent(CallView);
