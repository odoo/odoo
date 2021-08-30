/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            avatar
        [Element/model]
            ChannelMemberListMemberListComponent:member
        [web.Element/tag]
            img
        [web.Element/class]
            rounded-circle
            w-100
            h-100
        [web.Element/src]
            /mail/channel/
            .{+}
                @record
                .{ChannelMemberListMemberListComponent/channel}
                .{Thread/id}
            .{+}
                /partner/
            .{+}
                @record
                .{ChannelMemberListMemberListComponent:member/member}
                .{Partner/id}
            .{+}
                /avatar_128
        [web.Element/alt]
            {Locale/text}
                Avatar
        [web.Element/style]
            [web.scss/object-fit]
                cover
`;
