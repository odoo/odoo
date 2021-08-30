/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Tell whether the bottom of this message is visible or not.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageViewComponent/isBottomVisible
        [Action/params]
            offset
                [type]
                    Integer
                [default]
                    0
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
                    bottom with (double) 10px offset
                @elRect
                .{web.Element/bottom}
                .{<}
                    @parentRect
                    .{web.Element/bottom}
                    .{+}
                        @offset
                .{&}
                    @parentRect
                    .{web.Element/top}
                    .{<}
                        @elRect
                        .{web.Element/bottom}
                        .{+}
                            @offset
`;
