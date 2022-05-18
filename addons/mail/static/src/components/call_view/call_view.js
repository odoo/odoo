/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Dialog from 'web.OwlDialog';

const { Component } = owl;

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
        if (!this.callView.tileContainerRef.el) {
            return;
        }
        const { width, height } = this.callView.tileContainerRef.el.getBoundingClientRect();

        const { tileWidth, tileHeight } = this.callView.calculateTessellation({
            aspectRatio: this.callView.aspectRatio,
            containerHeight: height,
            containerWidth: width,
            tileCount: this.callView.tileContainerRef.el.children.length,
        });

        this.callView.update({
            tileHeight,
            tileWidth,
        });
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
