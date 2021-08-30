/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/getMostRecentMessageViewComponent
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/returns]
            MessageViewComponent
        [Action/behavior]
            {if}
                @record
                .{MessageListComponent/order}
                .{=}
                    desc
            .{then}
                {MessageListComponent/getOrderedMessageViewComponents}
                    @record
                .{Collection/first}
            .{else}
                {MessageListComponent/getOrderedMessageViewComponents}
                    @record
                .{Collection/last}
`;
