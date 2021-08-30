/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            name
        [Element/model]
            FollowerComponent
        [web.Element/tag]
            span
        [web.Element/class]
            flex-shrink
            text-truncate
        [web.Element/textContent]
            @record
            .{FollowerComponent/follower}
            .{Follower/nameOrDisplayName}
`;
