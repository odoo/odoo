/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            closeButton
        [Element/model]
            FollowerSubtypeListComponent
        [web.Element/tag]
            i
        [web.Element/class]
            close
            fa
            fa-times
        [web.Element/aria-label]
            {Locale/text}
                Close
        [Element/onClick]
            {Follower/closeSubtypes}
                @record
                .{FollowerSubtypeListComponent/record}
                .{FollowerSubtypeList/follower}
`;
