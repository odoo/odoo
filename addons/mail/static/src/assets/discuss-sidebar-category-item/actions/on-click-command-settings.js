/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Redirects to channel form page when 'settings' command is clicked.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategoryItem/onClickCommandSettings
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    DiscussSidebarCategoryItem
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
                        [type]
                            ir.actions.act_window
                        [res_model]
                            @record
                            .{DiscussSidebarCategoryItem/channel}
                            .{Thread/model}
                        [res_id]
                            @record
                            .{DiscussSidebarCategoryItem/channel}
                            .{Thread/id}
                        [views]
                            [0]
                                [0]
                                    false
                                [1]
                                    form
                        [target]
                            current
`;
