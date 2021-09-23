/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { usePosition } from '@web/core/position/position_hook';

const { Component } = owl;

export class MessagingPopover extends Component {

    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'mail.popover', propNameAsRecordLocalId: 'popoverLocalId' });
        usePosition(this.popover.anchorRef.el, {
            margin: 16,
            position: this.popover.position,
        });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.popover|undefined}
     */
    get popover() {
        return this.messaging && this.messaging.models['mail.popover'].get(this.props.popoverLocalId);
    }

}

Object.assign(MessagingPopover, {
    props: {
        popoverLocalId: String,
    },
    template: 'mail.MessagingPopover',
});

registerMessagingComponent(MessagingPopover);
