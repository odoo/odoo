/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadMoreMembers
        [Element/model]
            ChannelMemberListComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-secondary
        [Element/onClick]
            {Thread/onClickLoadMoreMembers}
                [0]
                    @record
                    .{ChannelMemberListComponent/channel}
                [1]
                    @ev
        [web.Element/textContent]
            {Locale/text}
                Load more
`;
