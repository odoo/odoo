/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Tell whether the message is partially visible on browser window or not.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageViewComponent/isPartiallyVisible
        [Action/params]
            record
                [type]
                    MessageViewComponent
        [Action/returns]
            Boolean
        [Action/behavior]
            :elRect
                @record
                .{MessageViewComponent/root}
                .{web.Element/getBoundingClientRect}
            {if}
                @record
                .{MessageViewComponent/root}
                .{web.Element/parentNode}
                .{isFalsy}
            .{then}
                false
            .{else}
                :parentRect
                    @record
                    .{MessageViewComponent/root}
                    .{web.Element/parentNode}
                    .{web.Element/getBoundingClientRect}
                {Dev/comment}
                    intersection with 5px offset
                @elRect
                .{web.Element/top}
                .{<}
                    @parentRect
                    .{web.Element/bottom}
                    .{+}
                        5
                .{&}
                    @parentRect
                    .{web.Element/top}
                    .{<}
                        @elRect
                        .{web.Element/bottom}
                        .{+}
                            5
`;
