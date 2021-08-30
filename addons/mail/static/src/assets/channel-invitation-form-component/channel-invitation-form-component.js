/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ChannelInvitationFormComponent
        [Model/fields]
            channelInvitationForm
        [Model/template]
            root
                title
                searchInputContainer
                    searchInput
                selectablePartnersSection
                    selectablePartnerForeach
                    noSelectablePartner
                    exceedingSelectableSearchResult
                selectedPartnersSection
                    selectedPartnersTitle
                    selectedPartners
                        selectedPartnerForeach
                inviteButtonContainer
                    inviteButton
                invitationLinkTitle
                invitationLinkInputContainer
                    invitationLinkInput
        [Model/lifecycle]
            onUpdate
`;
