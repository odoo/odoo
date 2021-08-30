/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Redirects to the public channels window when view command is clicked.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategory/onClickCommandView
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    DiscussSidebarCategory
        [Action/behavior]
            {web.Event/stopPropagation}
                @ev
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
                        [name]
                            {Locale/text}
                                Public Channels
                        [type]
                            ir.actions.act_window
                        [res_model]
                            mail.channel
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
                                    form
                        [domain]
                            public
                            .{!=}
                                private
`;
