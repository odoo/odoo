/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            titlePart
        [Element/model]
            ChannelMemberListMemberListComponent
        [web.Element/tag]
            h6
        [web.Element/class]
            m-2
        [web.Element/textContent]
            {String/sprintf}
                [0]
                    %s - %s
                [1]
                    @record
                    .{ChannelMemberListMemberListComponent/title}
                [2]
                    @record
                    .{ChannelMemberListMemberListComponent/members}
                    .{Collection/length}
`;
