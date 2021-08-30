/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ThreadViewComponent
        [web.Element/class]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/extraClass}
        [web.Element/data-correspondent-id]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/thread}
            .{Thread/correspondent}
            .{&}
                @record
                .{ThreadViewComponent/threadView}
                .{ThreadView/thread}
                .{Thread/correspond}
                .{Partner/id}
        [web.Element/data-thread-local-id]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/thread}
            .{Record/id}
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/position]
                relative
            [web.scss/flex-flow]
                column
            [web.scss/min-height]
                0
            [web.scss/background-color]
                {scss/gray}
                    100
`;
