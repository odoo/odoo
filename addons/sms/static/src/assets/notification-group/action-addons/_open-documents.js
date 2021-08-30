/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            NotificationGroup/_openDocuments
        [ActionAddon/feature]
            sms
        [ActionAddon/params]
            notificationGroup
        [ActionAddon/behavior]
            {if}
                @notificationGroup
                .{NotifcationGroup/type}
                .{!=}
                    sms
            .{then}
                @original
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
                        [context]
                            [create]
                                false
                        [domain]
                            message_has_sms_error
                            .{=}
                                true
                        [name]
                            {Locale/text}
                                SMS Failures
                        [type]
                            ir.actions.act_window
                        [view_mode]
                            kanban,list,form
                        [views]
                            [0]
                                [0]
                                    false
                                [1]
                                    kanban
                            [1]
                                [0]
                                    false
                                [1]
                                    list
                            [2]
                                [0]
                                    false
                                [1]
                                    form
                        [target]
                            current
                        [res_model]
                            @notificationGroup
                            .{NotificationGroup/resModel}
            {if}
                {Device/isMobile}
            .{then}
                {Dev/comment}
                    messaging menu has a higher z-index than views so it
                    must be closed to ensure the visibility of the view
                {MessagingMenu/close}
`;
