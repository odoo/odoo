/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            followerForeach
        [Element/model]
            FollowerListMenuComponent
        [Record/models]
            Foreach
        [Field/target]
            FollowerListMenuComponent:follower
        [Element/isPresent]
            @record
            .{FollowerListMenuComponent/thread}
            .{Thread/followers}
            .{Collection/length}
            .{>}
                0
        [FollowerListMenuComponent:follower/follower]
            @field
            .{Foreach/get}
                follower
        [Foreach/collection]
            @record
            .{FollowerListMenuComponent/thread}
            .{Thread/followers}
        [Foreach/as]
            follower
        [Element/key]
            @field
            .{Foreach/get}
                follower
            .{Record/id}
`;
