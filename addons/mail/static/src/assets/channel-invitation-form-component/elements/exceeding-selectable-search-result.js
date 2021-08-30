/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            exceedingSelectableSearchResult
        [Element/model]
            ChannelInvitationFormComponent
        [Element/isPresent]
            @record
            .{ChannelInvitationFormComponent/channelInvitationForm}
            .{ChannelInvitationForm/searchResultCount}
            .{>}
                @record
                .{ChannelInvitationFormComponent/channelInvitationForm}
                .{ChannelInvitationForm/selectablePartners}
                .{Collection/length}
        [web.Element/class]
            mx-3
        [web.Element/textContent]
            {String/sprintf}
                [0]
                    {Locale/text}
                        Showing %s results out of $s. Narrow your search to see more choices.
                [1]
                    @record
                    .{ChannelInvitationFormComponent/channelInvitationForm}
                    .{ChannelInvitationForm/selectablePartners}
                    .{Collection/length}
                [2]
                    @record
                    .{ChannelInvitationFormComponent/channelInvitationForm}
                    .{ChannelInvitationForm/searchResultCount}
`;
