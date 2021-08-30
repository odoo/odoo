/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            text
        [Element/model]
            FollowerSubtypeComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            @record
            .{FollowerSubtypeComponent/followerSubtype}
            .{FollowerSubtype/name}
`;
