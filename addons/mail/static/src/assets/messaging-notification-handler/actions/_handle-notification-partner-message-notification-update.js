/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationPartnerMessageNotificationUpdate
        [Action/params]
            notificationHandler
                [type]
                    MessagingNotificationHandler
            elements
                [type]
                    Collection<Object>
        [Action/behavior]
            {foreach}
                @elements
            .{as}
                messageData
            .{do}
                :message
                    {Record/insert}
                        [Record/models]
                            Message
                        {Message/convertData}
                            @messageData
                {Dev/comment}
                    implicit: failures are sent by the server as
                    notification only if the current partner is author
                    of the message
                {if}
                    @message
                    .{Message/author}
                    .{isFalsy}
                    .{&}
                        {Env/currentPartner}
                .{then}
                    {Record/update}
                        [0]
                            @message
                        [1]
                            [Message/author]
                                {Env/currentPartner}
`;
