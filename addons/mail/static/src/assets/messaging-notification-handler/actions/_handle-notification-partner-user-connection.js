/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationPartnerUserConnection
        [Action/params]
            notificationHandler
                [type]
                    MessagingNotificationHandler
            partnerId
                [type]
                    Integer
            userName
                [type]
                    String
        [Action/behavior]
            {Dev/comment}
                If the current user invited a new user, and the new user
                is connecting for the first time while the current user
                is present then open a chat for the current user with the
                new user.
            :message
                {String/sprintf}
                    [0]
                        {Locale/text}
                            %s connected
                    [1]
                        @username
            :title
                {Locale/text}
                    This is their first connection. Wish them luck.
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                bus_service
            .{Dict/get}
                sendNotification
            .{Function/call}
                [message]
                    @message
                [title]
                    @title
                [type]
                    info
            :chat
                {Record/doAsync}
                    [0]
                        @notificationHandler
                    [1]
                        {Env/getChat}
                            [partnerId]
                                @partnerId
            {if}
                @chat
                .{isFalsy}
                .{|}
                    {Device/isMobile}
            .{then}
                {break}
            {ChatWindowManager/openThread}
                @chat
`;
