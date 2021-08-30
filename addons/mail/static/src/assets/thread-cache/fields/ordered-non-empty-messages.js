/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        List of ordered non empty messages linked to this cache.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            orderedNonEmptyMessages
        [Field/model]
            ThreadCache
        [Field/type]
            many
        [Field/target]
            Message
        [Field/compute]
            @record
            .{ThreadCache/orderedMessages}
            .{Collection/filter}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        message
                    [Function/out]
                        @message
                        .{Message/isEmpty}
                        .{isFalsy}
`;
