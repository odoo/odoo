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
        useComponentToModel({ fieldName: 'component', modelName: 'mail.channel_invitation_form', propNameAsRecordLocalId: 'localId' });
        useRefToModel({ fieldName: 'searchInputRef', modelName: 'mail.channel_invitation_form', propNameAsRecordLocalId: 'localId', refName: 'searchInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'mail.channel_invitation_form', propNameAsRecordLocalId: 'localId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get channelInvitationForm() {
        return this.messaging && this.messaging.models['mail.channel_invitation_form'].get(this.props.localId);
    }

}

Object.assign(ChannelInvitationForm, {
    props: {
        localId: {
            type: String,
        },
    },
    template: 'mail.ChannelInvitationForm',
});

registerMessagingComponent(ChannelInvitationForm);
