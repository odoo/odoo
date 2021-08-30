/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastMessage
        [Field/model]
            ThreadCache
        [Field/type]
            one
        [Field/target]
            Message
        [Field/compute]
            {if}
                @record
                .{ThreadCache/orderedMessages}
                .{Collection/length}
                .{=}
                    0
            .{then}
                {Record/empty}
            .{else}
                @record
                .{ThreadCache/orderedMessages}
                .{Collection/last}
`;
