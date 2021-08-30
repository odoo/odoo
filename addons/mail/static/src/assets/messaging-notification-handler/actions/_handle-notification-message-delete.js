/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationPartnerDeletion
        [Action/params]
            notificationHandler
                [type]
                    MessagingNotificationHandler
            message_ids
                [type]
                    Collection<Integer>
        [Action/behavior]
            {foreach}
                @message_ids
            .{as}
                id
            .{do}
                :message
                    {Record/findById}
                        [Message/id]
                            @id
                {if}
                    @message
                .{then}
                    {Record/delete}
                        @message
`;
