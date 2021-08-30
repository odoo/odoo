/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            NotificationGroup/openCancelAction
        [ActionAddon/feature]
            snailmail
        [ActionAddon/params]
            notificationGroup
        [ActionAddon/behavior]
            {if}
                @notificationGroup
                .{NotificationGroup/type}
                .{!=}
                    snail
            .{then}
                @original
            .{else}
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
                            snailmail.snailmail_letter_cancel_action
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
