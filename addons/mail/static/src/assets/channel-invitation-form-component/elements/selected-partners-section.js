/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectedPartnersSection
        [Element/model]
            ChannelInvitationFormComponent
        [Element/isPresent]
            @record
            .{ChannelInvitationFormComponent/channelInvitationForm}
            .{ChannelInvitationForm/selectedPartners}
            .{Collection/length}
            .{>}
                0
            .{&}
                {Env/isCurrentUserGuest}
                .{isFalsy}
        [web.Element/class]
            mx-3
            mt-3
`;
