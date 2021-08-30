/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            unknownMemberText
        [Element/model]
            ChannelMemberListComponent
        [web.Element/tag]
            span
        [web.Element/class]
            mx-2
            mt-2
        [web.Element/textContent]
            {if}
                @record
                .{ChannelMemberListComponent/channel}
                .{Thread/unknownMemberCount}
                .{=}
                    1
            .{then}
                {Locale/text}
                    And 1 other member.
            {if}
                @record
                .{ChannelMemberListComponent/channel}
                .{Thread/unknownMemberCount}
                .{>}
                    1
            .{then}
                {String/sprintf}
                    [0]
                        {Locale/text}
                            And %s other members.
                    [1]
                        @record
                        .{ChannelMemberListComponent/channel}
                        .{Thread/unknownMemberCount}
`;
