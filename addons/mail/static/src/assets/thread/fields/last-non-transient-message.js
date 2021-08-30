/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Last non-transient message.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastNonTransientMessage
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            Message
        [Field/compute]
            {if}
                @record
                .{Thread/orderedNonTransientMessages}
                .{Collection/last}
            .{then}
                @record
                .{Thread/orderedNonTransientMessages}
                .{Collection/last}
            .{else}
                {Record/empty}
`;
