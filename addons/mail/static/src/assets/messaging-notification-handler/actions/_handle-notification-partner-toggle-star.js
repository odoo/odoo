/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationPartnerToggleStar
        [Action/params]
            notificationHandler
                [type]
                    MessagingNotificationHandler
            message_ids
                [type]
                    Collection<Integer>
            starred
                [type]
                    Boolean
        [Action/behavior]
            {foreach}
                @message_ids
            .{as}
                messageId
            .{do}
                :message
                    {Record/findById}
                        [Message/id]
                            @messageId
                {if}
                    @message
                    .{isFalsy}
                .{then}
                    {continue}
                {Record/update}
                    [0]
                        @message
                    [1]
                        [Message/isStarred]
                            @starred
                {Record/update}
                    [0]
                        {Env/starred}
                    [1]
                        [Thread/counter]
                            {if}
                                @starred
                            .{then}
                                {Field/add}
                                    1
                            .{else}
                                {Field/remove}
                                    1
`;
