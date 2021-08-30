/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the view that allows to cancel all notifications of the group.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            NotificationGroup/openCancelAction
        [Action/params]
            notificationGroup
                [type]
                    NotificationGroup
        [Action/behavior]
            {if}
                @notificationGroup
                .{NotificationGroup/type}
                .{!=}
                    email
            .{then}
                {break}
            @env
            .{Env/owlEnv}
            .{Dict/get}
                bus
            .{Dict/get}
                trigger
            .{Function/call}
                [0]
                    do-action
                [1]
                    [action]
                        mail.mail_resend_cancel_action
                    [options]
                        [additional_context]
                            [default_model]
                                @notificationGroup
                                .{NotificationGroup/resModel}
                            [unread_counter]
                                @notificationGroup
                                .{NotificationGroup/notifications}
                                .{Collection/length}
`;
