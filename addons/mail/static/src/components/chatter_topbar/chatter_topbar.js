/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;

export class ChatterTopbar extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'componentChatterTopbar', modelName: 'Chatter', propNameAsRecordLocalId: 'chatterLocalId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Chatter}
     */
    get chatter() {
        return this.messaging && this.messaging.models['Chatter'].get(this.props.chatterLocalId);
    }

}

Object.assign(ChatterTopbar, {
    props: {
        chatterLocalId: String,
    },
    template: 'mail.ChatterTopbar',
});

registerMessagingComponent(ChatterTopbar);
