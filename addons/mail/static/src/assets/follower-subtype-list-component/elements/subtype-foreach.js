/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            subtype
        [Element/model]
            FollowerSubtypeListComponent
        [Record/models]
            Foreach
        [Field/target]
            FollowerSubtypeListComponent:subtype
        [FollowerSubtypeListComponent:subtype/subtype]
            @field
            .{Foreach/get}
                subtype
        [Foreach/collection]
            @record
            .{FollowerSubtypeListComponent/record}
            .{FollowerSubtypeList/follower}
            .{Follower/subtypes}
        [Foreach/as]
            subtype
        [Element/key]
            @field
            .{Foreach/get}
                subtype
            .{FollowerSubtype/id}
`;
