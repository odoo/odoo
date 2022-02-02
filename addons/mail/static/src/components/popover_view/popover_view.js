/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { usePosition } from '@web/core/position/position_hook';

const { Component } = owl;

export class PopoverView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'PopoverView' });
        usePosition(
            () => this.popoverView && this.popoverView.anchorRef && this.popoverView.anchorRef.el,
            {
                margin: 16,
                position: this.popoverView.position,
            }
        );
    }

    /**
     * @returns {PopoverView|undefined}
     */
    get popoverView() {
        return this.messaging && this.messaging.models['PopoverView'].get(this.props.localId);
    }

}

Object.assign(PopoverView, {
    props: { localId: String },
    template: 'mail.PopoverView',
});

registerMessagingComponent(PopoverView);
