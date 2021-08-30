/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            name
        [Element/model]
            ChannelMemberListMemberListComponent:member
        [web.Element/tag]
            span
        [web.Element/class]
            ml-2
            flex-column-1
            text-truncate
        [Element/onClick]
            {Thread/onClickMemberName}
                [0]
                    @record
                    .{ChannelMemberListMemberListComponent/channel}
                [1]
                    @record
                    .{ChannelMemberListMemberListComponent:member/member}
        [web.Element/textContent]
            @record
            .{ChannelMemberListMemberListComponent:member/member}
            .{Partner/nameOrDisplayName}
        [web.Element/style]
            [web.scss/min-width]
                0
            [web.scss/cursor]
                pointer
`;
