/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Last message of the thread, could be a transient one.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastMessage
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            Message
        [Field/compute]
            {if}
                @record
                .{Thread/orderedMessages}
                .{Collection/last}
            .{then}
                @record
                .{Thread/orderedMessages}
                .{Collection/last}
            .{else}
                {Record/empty}
`;
