/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallParticipantVideo extends Component {

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

Object.assign(CallParticipantVideo, {
    props: { record: Object },
    template: 'mail.CallParticipantVideo',
});

registerMessagingComponent(CallParticipantVideo);
