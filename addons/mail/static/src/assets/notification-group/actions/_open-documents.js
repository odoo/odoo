/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the view that displays all the records of the group.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            NotificationGroup/_openDocuments
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
                        [context]
                            [create]
                                false
                        [domain]
                            message_has_error
                            .{=}
                                true
                        [name]
                            {Locale/text}
                                Mail Failures
                        [res_model]
                            @notificationGroup
                            .{NotificationGroup/resModel}
                        [target]
                            current
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
            {if}
                {Device/isMobile}
            .{then}
                {Dev/comment}
                    messaging menu has a higher z-index than views so it
                    must be closed to ensure the visibility of the view
                {MessagingMenu/close}
`;
