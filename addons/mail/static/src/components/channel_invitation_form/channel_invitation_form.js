/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelInvitationForm extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'searchInputRef', refName: 'searchInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    get channelInvitationForm() {
        return this.props.record;
    }

}

Object.assign(ChannelInvitationForm, {
    props: { record: Object },
    template: 'mail.ChannelInvitationForm',
});

registerMessagingComponent(ChannelInvitationForm);
