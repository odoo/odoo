/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            unfollowIcon
        [Element/model]
            FollowButtonComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-times
        [Element/isPresent]
            @record
            .{FollowButtonComponent/isUnfollowButtonHighlighted}
`;
