/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            cancelButton
        [Element/model]
            FollowerSubtypeListComponent
        [web.Element/tag]
            button
        [web.Element/class]
            o-cancel
            btn
            btn-secondary
        [Element/onClick]
            {Follower/closeSubtypes}
                @record
                .{FollowerSubtypeListComponent/record}
                .{FollowerSubtypeList/follower}
        [web.Element/textContent]
            {Locale/text}
                Cancel
`;
