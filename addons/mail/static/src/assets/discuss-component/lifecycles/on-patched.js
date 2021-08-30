/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Lifecyle}
        [Lifecycle/name]
            onPatched
        [Lifecycle/model]
            DiscussComponent
        [Lifecycle/behavior]
            {if}
                {Discuss/thread}
                .{&}
                    {Discuss/thread}
                    .{=}
                        {Env/inbox}
                .{&}
                    {Discuss/threadView}
                .{&}
                    @record
                    .{DiscussComponent/_lastThreadCache}
                    .{=}
                        {Discuss/threadView}
                        .{ThreadView/threadCache}
                        .{Record/id}
                .{&}
                    @record
                    .{DiscussComponent/_lastThreadCounter}
                    .{>}
                        0
                .{&}
                    {Discuss/thread}
                    .{Thread/counter}
                    .{=}
                        0
            .{then}
                {Component/trigger}
                    @record
                    o-show-rainbow-man
`;
