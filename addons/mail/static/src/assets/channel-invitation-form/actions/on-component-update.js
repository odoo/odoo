/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChannelInvitationForm/onComponentUpdate
        [Action/params]
            record
                [type]
                    ChannelInvitationForm
        [Action/behavior]
            {if}
                @record
                .{ChannelInvitationForm/doFocusOnSearchInput}
                .{&}
                    @record
                    .{ChannelInvitationForm/channelInvitationFormComponents}
                    .{Collection/first}
                    .{ChannelInvitationFormComponent/searchInput}
            .{then}
                {foreach}
                    @record
                    .{ChannelInvitationForm/channelInvitationFormComponents}
                .{as}
                    channelInvitationFormComponent
                .{do}
                    {web.Element/focus}
                        @channelInvitationFormComponent
                        .{ChannelInvitationFormComponent/searchInput}
                    {web.Element/setSelectionRange}
                        [0]
                            @channelInvitationFormComponent
                            .{ChannelInvitationFormComponent/searchInput}
                        [1]
                            @record
                            .{ChannelInvitationForm/searchTerm}
                            .{String/length}
                        [2]
                            @record
                            .{ChannelInvitationForm/searchTerm}
                            .{String/length}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ChannelInvitationForm/doFocusOnSearchInput]
                            {Record/empty}
`;
