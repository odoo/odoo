/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Chatter/onClickScheduleActivity
        [Action/params]
            ev
                [type]
                    MouseEvent
            chatter
                [type]
                    Chatter
        [Action/behavior]
                :action
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
                            @chatter
                            .{Chatter/thread}
                            .{Thread/id}
                        [default_res_model]
                            @chatter
                            .{Chatter/thread}
                            .{Thread/model}
                    [res_id]
                        false
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
                            @action
                        [options]
                            [on_close]
                                {Chatter/reloadParentView}
                                    @record
`;
