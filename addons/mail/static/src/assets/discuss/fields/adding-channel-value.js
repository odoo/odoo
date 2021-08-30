/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Value that is used to create a channel from the sidebar.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            addingChannelValue
        [Field/model]
            Discuss
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Discuss/discussView}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                @record
                .{Discuss/addingChannelValue}
`;
