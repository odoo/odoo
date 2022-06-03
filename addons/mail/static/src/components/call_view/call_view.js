/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Dialog from 'web.OwlDialog';

const { Component, useRef, useState } = owl;

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
        this.state = useState({
            tileWidth: 0,
            tileHeight: 0,
        });
        this.tileContainerRef = useRef('tileContainer');
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
     * @private
     */
    _setTileLayout() {
        if (!this.root.el) {
            return;
        }
        if (!this.tileContainerRef.el) {
            return;
        }
        const { width, height } = this.tileContainerRef.el.getBoundingClientRect();

        const { tileWidth, tileHeight } = this.callView.calculateTessellation({
            aspectRatio: this.callView.aspectRatio,
            containerHeight: height,
            containerWidth: width,
            tileCount: this.tileContainerRef.el.children.length,
        });

        this.state.tileWidth = tileWidth;
        this.state.tileHeight = tileHeight;
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
