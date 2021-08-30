/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            avatarContainer
        [Element/model]
            ChannelMemberListMemberListComponent:member
        [web.Element/class]
            position-relative
            flex-shrink-0
        [Element/onClick]
            {Thread/onClickMemberAvatar}
                [0]
                    @record
                    .{ChannelMemberListMemberListComponent/channel}
                [1]
                    @record
                    .{ChannelMemberListMemberListComponent:member/member}
        [web.Element/style]
            [web.scss/width]
                32
                px
            [web.scss/height]
                32
                px
            [web.scss/cursor]
                pointer
`;
