/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        All messages ordered like they are displayed. This field does not
        contain transient messages which are not "real" records.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            orderedNonTransientMessages
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Message
        [Field/compute]
            @record
            .{Thread/orderedMessages}
            .{Collection/filter}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        @item
                        .{Message/isTransient}
                        .{isFalsy}
`;
