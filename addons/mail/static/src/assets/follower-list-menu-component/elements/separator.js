/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separator
        [Element/model]
            FollowerListMenuComponent
        [web.Element/class]
            dropdown-divider
        [Element/isPresent]
            @record
            .{FollowerListMenuComponent/thread}
            .{Thread/followers}
            .{Collection/length}
            .{>}
                0
        [web.Element/role]
            separator
`;
