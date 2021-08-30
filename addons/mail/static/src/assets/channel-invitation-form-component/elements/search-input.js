/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            searchInput
        [Element/model]
            ChannelInvitationFormComponent
        [web.Element/tag]
            input
        [web.Element/type]
            text
        [web.Element/value]
            @record
            .{ChannelInvitationFormComponent/channelInvitationForm}
            .{ChannelInvitationForm/searchTerm}
        [web.Element/placeholder]
            {Locale/text}
                Type the name of a person
        [Element/onInput]
            {ChannelInvitationForm/onInputSearch}
                @record
                .{ChannelInvitationFormComponent/channelInvitationForm}
                @ev
`;
