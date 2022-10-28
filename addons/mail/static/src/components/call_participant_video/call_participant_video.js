/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class CallParticipantVideoView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {CallParticipantVideoView}
     */
     get callParticipantVideoView() {
        return this.props.record;
    }

}

Object.assign(CallParticipantVideoView, {
    props: { record: Object },
    template: 'mail.CallParticipantVideoView',
});

registerMessagingComponent(CallParticipantVideoView);
