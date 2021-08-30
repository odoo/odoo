/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the buttons to start a RTC call should be displayed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            componentStyle
        [Field/model]
            ChatWindow
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            :textDirection
                {Locale/textDirection}
            :offsetFrom
                {if}
                    @textDirection
                    .{=}
                        rtl
                .{then}
                    left
                .{else}
                    right
            :oppositeFrom
                {if}
                    @offsetFrom
                    .{=}
                        right
                .{then}
                    left
                .{else}
                    right
            @offsetFrom
            .{+}
                : 
            .{+}
                @record
                .{ChatWindow/visibleOffset}
            .{+}
                px; 
            .{+}
                @oppositeFrom
            .{+}
                : auto
`;
