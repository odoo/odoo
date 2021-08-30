/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Fetch messaging data initially to populate the store specifically for
        the current users. This includes pinned channels for instance.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/start
        [Action/params]
            messagingNotificationHandler
                [type]
                    MessagingNotificationHandler
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                bus_service
            .{Dict/get}
                onNotification
            .{Function/call}
                [0]
                    null
                [1]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            notifs
                        [Function/out]
                            {MessagingNotificationHandler/_handleNotifications}
                                [0]
                                    @messagingNotificationHandler
                                [1]
                                    @notifs
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                bus_service
            .{Dict/get}
                startPolling
            .{Function/call}
`;
