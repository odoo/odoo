/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ChannelInvitationForm
        [Model/fields]
            channelInvitationFormComponents
            chatWindow
            doFocusOnSearchInput
            hasPendingSearchRpc
            hasSearchRpcInProgress
            inviteButtonText
            popoverViewOwner
            searchResultCount
            searchTerm
            selectablePartners
            selectedPartners
            thread
        [Model/id]
            ChannelInvitationForm/chatWindow
            .{|}
                ChannelInvitationForm/popoverViewOwner
        [Model/actions]
            ChannelInvitationForm/onClickInvite
            ChannelInvitationForm/onClickSelectablePartner
            ChannelInvitationForm/onClickSelectedPartner
            ChannelInvitationForm/onComponentUpdate
            ChannelInvitationForm/onInputPartnerCheckbox
            ChannelInvitationForm/onInputSearch
            ChannelInvitationForm/searchPartnersToInvite
`;
