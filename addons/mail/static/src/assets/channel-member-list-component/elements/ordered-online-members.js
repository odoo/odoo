/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            orderedOnlineMembers
        [Element/model]
            ChannelMemberListComponent
        [Element/isPresent]
            @record
            .{ChannelMemberListComponent/channel}
            .{Thread/orderedOnlineMembers}
            .{Collection/length}
            .{>}
                0
        [Field/target]
            ChannelMemberListMemberListComponent
        [ChannelMemberListMemberListComponent/channel]
            @record
            .{ChannelMemberListComponent/channel}
        [ChannelMemberListMemberListComponent/members]
            @record
            .{ChannelMemberListComponent/channel}
            .{Thread/orderedOnlineMembers}
        [ChannelMemberListMemberListComponent/title]
            {Locale/text}
                Online
`;
