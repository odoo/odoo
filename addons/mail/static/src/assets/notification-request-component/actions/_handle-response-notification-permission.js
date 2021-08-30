/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handle the response of the user when prompted whether push notifications
        are granted or denied.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            NotificationRequestComponent/_handleResponseNotificationPermission
        [Action/params]
            record
                [type]
                    NotificationRequestComponent
            value
                [type]
                    String
        [Action/behavior]
            {Env/refreshIsNotificationPermissionDefault}
            {if}
                @value
                .{!=}
                    granted
            .{then}
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
                        {Locale/text}
                            Odoo will not have the permission to send native notifications on this device.
                    [title]
                        {Locale/text}
                            Permission denied
`;
