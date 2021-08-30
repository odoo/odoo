/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationNeedaction
        [Action/params]
            notificationHandler
                [type]
                    MessagingNotificationHandler
            data
                [type]
                    Object
        [Action/behavior]
            :message
                {Record/insert}
                    [Record/models]
                        Message
                    {Message/convertData}
                        @data
            {Record/update}
                [0]
                    {Env/inbox}
                [1]
                    [Thread/counter]
                        {Field/add}
                            1
            {if}
                @message
                .{Message/originThread}
                .{&}
                    @message
                    .{Message/isNeedaction}
            .{then}
                {Record/update}
                    [0]
                        @message
                        .{Message/originThread}
                    [1]
                        [Thread/messageNeedactionCounter]
                            {Field/add}
                                1
`;
