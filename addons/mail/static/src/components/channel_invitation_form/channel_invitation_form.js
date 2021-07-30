/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useStore } from '@mail/component_hooks/use_store/use_store';
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
        useStore(props => {
            const channelInvitationForm = this.env.models['mail.channel_invitation_form'].get(this.props.localId);
            const selectablePartners = channelInvitationForm ? channelInvitationForm.selectablePartners : [];
            const selectedPartners = channelInvitationForm ? channelInvitationForm.selectedPartners : [];
            return {
                channelInvitationForm,
                channelInvitationFormInviteButtonText: channelInvitationForm && channelInvitationForm.inviteButtonText,
                channelInvitationFormSearchResultCount: channelInvitationForm && channelInvitationForm.searchResultCount,
                channelInvitationFormSearchTerm: channelInvitationForm && channelInvitationForm.searchTerm,
                selectablePartners: selectablePartners.map(selectablePartner => {
                    return {
                        avatarUrl: selectablePartner.avatarUrl,
                        im_status: selectablePartner.im_status,
                        nameOrDisplayName: selectablePartner.nameOrDisplayName,
                        selectablePartner,
                    };
                }),
                selectedPartners: selectedPartners.map(selectedPartner => {
                    return {
                        im_status: selectedPartner.im_status,
                        selectedPartner,
                    };
                }),
            };
        }, {
            compareDepth: {
                selectablePartners: 2, // array + data object
                selectedPartners: 2, // array + data object
            },
        });
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
