/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadMoreMembersContainer
        [Element/model]
            ChannelMemberListComponent
        [Element/isPresent]
            @record
            .{ChannelMemberListComponent/channel}
            .{Thread/unknownMemberCount}
            .{>}
                0
        [web.Element/class]
            mx-2
            my-1
`;
