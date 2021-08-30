/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            orderedOfflineMembers
        [Element/model]
            ChannelMemberListComponent
        [Element/isPresent]
            @record
            .{ChannelMemberListComponent/channel}
            .{Thread/orderedOfflineMembers}
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
            .{Thread/orderedOfflineMembers}
        [ChannelMemberListMemberListComponent/title]
            {Locale/text}
                Offline
`;
