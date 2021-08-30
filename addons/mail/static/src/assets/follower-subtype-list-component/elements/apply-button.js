/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            applyButton
        [Element/model]
            FollowerSubtypeListComponent
        [web.Element/tag]
            button
        [web.Element/class]
            o-apply
            btn
            btn-primary
        [Element/onClick]
            {Follower/updateSubtypes}
                @record
                .{FollowerSubtypeListComponent/record}
                .{FollowerSubtypeList/follower}
        [web.Element/textContent]
            {Locale/text}
                Apply
`;
