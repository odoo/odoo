/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            needactionMessagesAsOriginThread
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Message
        [Field/compute]
            @record
            .{Thread/messagesAsOriginThread}
            .{Collection/filter}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        @item
                        .{Message/isNeedaction}
`;
