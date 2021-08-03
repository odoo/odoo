/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';
import { PartnerImStatusIcon } from '@mail/components/partner_im_status_icon/partner_im_status_icon';

const { Component } = owl;

const components = { PartnerImStatusIcon };

export class ChannelInvitationForm extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useShouldUpdateBasedOnProps();
        useModels();
        useComponentToModel({ fieldName: 'component', modelName: 'mail.channel_invitation_form', propNameAsRecordLocalId: 'localId' });
        useRefToModel({ fieldName: 'searchInputRef', modelName: 'mail.channel_invitation_form', propNameAsRecordLocalId: 'localId', refName: 'searchInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'mail.channel_invitation_form', propNameAsRecordLocalId: 'localId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get channelInvitationForm() {
        return this.env.models['mail.channel_invitation_form'].get(this.props.localId);
    }

}

Object.assign(ChannelInvitationForm, {
    components,
    props: {
        localId: {
            type: String,
        },
    },
    template: 'mail.ChannelInvitationForm',
});
