/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns whether the given html element is inside this follower subtype list.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            FollowerSubtypeList/containsElement
        [Action/params]
            element
                [type]
                    web.Element
            record
                [type]
                    FollowerSubtypeList
        [Action/returns]
            Boolean
        [Action/behavior]
            @record
            .{FollowerSubtypeList/component}
            .{&}
                @record
                .{FollowerSubtypeList/component}
                .{FollowerSubtypeListComponent/root}
                .{web.Element/contains}
                    @element
`;
