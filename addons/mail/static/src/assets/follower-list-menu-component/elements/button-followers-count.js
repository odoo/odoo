/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonFollowersCount
        [Element/model]
            FollowerListMenuComponent
        [web.Element/tag]
            span
        [web.Element/class]
            pl-1
        [web.Element/textContent]
            @record
            .{FollowerListMenuComponent/thread}
            .{Thread/followers}
            .{Collection/length}
`;
