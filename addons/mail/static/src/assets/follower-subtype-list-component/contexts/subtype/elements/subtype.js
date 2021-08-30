/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            subtype
        [Element/model]
            FollowerSubtypeListComponent:subtype
        [Field/target]
            FollowerSubtypeComponent
        [FollowerSubtypeComponent/follower]
            @record
            .{FollowerSubtypeListComponent/record}
            .{FollowerSubtypeList/follower}
        [FollowerSubtypeComponent/followerSubtype]
            @record
            .{FollowerSubtypeListComponent:subtype/subtype}
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                column
`;
