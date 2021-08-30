/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles the click on a link inside the activity.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityView/onClickActivity
        [Action/params]
            record
                [type]
                    ActivityView
            ev
                [type]
                    web.MouseEvent
        [Action/behavior]
            {if}
                @ev
                .{web.Event/target}
                .{web.Element/tagName}
                .{=}
                    A
                .{&}
                    @ev
                    .{web.Event/target}
                    .{web.Element/dataset}
                    .{Dict/get}
                        oeId
                .{&}
                    @ev
                    .{web.Event/target}
                    .{web.Element/dataset}
                    .{Dict/get}
                        oeModel
            .{then}
                {Env/openProfile}
                    [id]
                        @ev
                        .{web.Event/target}
                        .{web.Element/dataset}
                        .{Dict/get}
                            oeId
                    [model]
                        @ev
                        .{web.Event/target}
                        .{web.Element/dataset}
                        .{Dict/get}
                            oeModel
                {Dev/comment}
                    avoid following dummy href
                {web.Event/preventDefault}
                    @ev
`;
