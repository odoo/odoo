/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Mark provided messages as read. Messages that have been marked as
        read are acknowledged by server with response as longpolling
        notification of following format:

        [[dbname, 'res.partner', partnerId], { type: 'mark_as_read' }]

        @see 'MessagingNotificationHandler/_handleNotificationPartnerMarkAsRead()'
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/markMessagesAsRead
        [Action/params]
            messages
                [type]
                    Collection<Message>
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [model]
                    mail.message
                [method]
                    set_message_done
                [args]
                    {Record/insert}
                        [Record/models]
                            Collection
                        @messages
                        .{Collection/map}
                            {Record/insert}
                                [Record/models]
                                    Function
                                [Function/in]
                                    item
                                [Function/out]
                                    @item
                                    .{Message/id}
`;
