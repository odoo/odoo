/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            follower
        [Element/model]
            FollowerListMenuComponent:follower
        [Field/target]
            FollowerComponent
        [web.Element/class]
            dropdown-item
        [FollowerComponent/follower]
            @record
            .{FollowerListMenuComponent:follower/follower}
        [Element/onClick]
            {FollowerListMenuComponent/_hide}
                @record
`;
