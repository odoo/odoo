/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States how many members are currently unknown on the client side.
        This is the difference between the total number of members of the
        channel as reported in memberCount and those actually in members.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            unknownMemberCount
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/compute]
            @record
            .{Thread/memberCount}
            .{-}
                @record
                .{Thread/members}
                .{Collection/length}
`;
