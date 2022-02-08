/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';

const { Component } = owl;

export class ChannelInvitationForm extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'ChannelInvitationForm' });
        useRefToModel({ fieldName: 'searchInputRef', modelName: 'ChannelInvitationForm', refName: 'searchInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'ChannelInvitationForm' });
    }

    get channelInvitationForm() {
        return this.messaging && this.messaging.models['ChannelInvitationForm'].get(this.props.localId);
    }

}

Object.assign(ChannelInvitationForm, {
    props: { localId: String },
    template: 'mail.ChannelInvitationForm',
});

registerMessagingComponent(ChannelInvitationForm);
