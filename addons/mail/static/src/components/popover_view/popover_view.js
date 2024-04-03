/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { usePosition } from '@web/core/position_hook';

const { Component } = owl;

export class PopoverView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        usePosition(
            () => this.popoverView.anchorRef && this.popoverView.anchorRef.el,
            {
                popper: "root",
                margin: 16,
                position: this.popoverView.position,
            }
        );
    }

    /**
     * @returns {PopoverView|undefined}
     */
    get popoverView() {
        return this.props.record;
    }

}

Object.assign(PopoverView, {
    props: { record: Object },
    template: 'mail.PopoverView',
});

registerMessagingComponent(PopoverView);
