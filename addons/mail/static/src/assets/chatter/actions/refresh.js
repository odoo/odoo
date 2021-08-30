/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Chatter/refresh
        [Action/params]
            record
                [type]
                    Chatter
        [Action/behavior]
            :requestData
                activities
                followers
                suggestedRecipients
            {if}
                @record
                .{Chatter/hasMessageList}
            .{then}
                {Collection/push}
                    [0]
                        @requestData
                    [1]
                        messages
            {Thread/fetchData}
                [0]
                    @record
                    .{Chatter/thread}
                [1]
                    requestData
`;
