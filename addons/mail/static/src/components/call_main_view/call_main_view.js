/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallMainView extends Component {

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
     * @returns {CallMainView}
     */
    get callMainView() {
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
        if (!this.callMainView.tileContainerRef.el) {
            return;
        }
        const { width, height } = this.callMainView.tileContainerRef.el.getBoundingClientRect();

        const { tileWidth, tileHeight } = this.callMainView.calculateTessellation({
            aspectRatio: this.callMainView.callView.aspectRatio,
            containerHeight: height,
            containerWidth: width,
            tileCount: this.callMainView.tileContainerRef.el.children.length,
        });

        this.callMainView.update({
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

Object.assign(CallMainView, {
    props: { record: Object },
    template: 'mail.CallMainView',
});

registerMessagingComponent(CallMainView);
