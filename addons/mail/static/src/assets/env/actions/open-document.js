/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the form view of the record with provided id and model.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Env/openDocument
        [Action/params]
            id
                [type]
                    Integer
            model
                [type]
                    String
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
                        [res_model]
                            @model
                        [views]
                            [0]
                                [0]
                                    false
                                [1]
                                    form
                        [res_id]
                            @id
            {if}
                {Device/isMobile}
            .{then}
                {Dev/comment}
                    messaging menu has a higher z-index than views so it
                    must be closed to ensure the visibility of the view
                {MessagingMenu/close}
`;
