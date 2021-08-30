/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens (legacy) form view dialog to edit current activity and updates
        the activity when dialog is closed.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Activity/edit
        [Action/params]
            record
                [type]
                    Activity
        [Action/behavior]
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
                        [type]
                            ir.actions.act_window
                        [name]
                            {Locale/text}
                                Schedule Activity
                        [res_model]
                            mail.activity
                        [view_mode]
                            form
                        [views]
                            [0]
                                [0]
                                    false
                                [1]
                                    form
                        [target]
                            new
                        [context]
                            [default_res_id]
                                @record
                                .{Activity/thread}
                                .{Thread/id}
                            [default_res_model]
                                @record
                                .{Activity/thread}
                                .{Thread/model}
                        [res_id]
                            @record
                            .{Activity/id}
                    [options]
                        [on_close]
                            {Activity/fetchAndUpdate}
                                @record
`;
