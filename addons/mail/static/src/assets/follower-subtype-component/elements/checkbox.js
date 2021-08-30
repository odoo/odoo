/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            checkbox
        [Element/model]
            FollowerSubtypeComponent
        [web.Element/tag]
            input
        [web.Element/type]
            checkbox
        [web.Element/isChecked]
            @record
            .{FollowerSubtypeComponent/follower}
            .{Follower/selectedSubtypes}
            .{Collection/includes}
                @record
                .{FollowerSubtypeComponent/followerSubtype}
        [Element/onChange]
            {if}
                @ev
                .{web.ChangeEvent/target}
                .{web.Element/isChecked}
            .{then}
                {Follower/selectSubtype}
                    @record
                    .{FollowerSubtypeComponent/follower}
                    @record
                    .{FollowerSubtypeComponent/followerSubtype}
            .{else}
                {Follower/unselectSubtype}
                    @record
                    .{FollowerSubtypeComponent/follower}
                    @record
                    .{FollowerSubtypeComponent/followerSubtype}
        [web.Element/style]
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    2
`;
