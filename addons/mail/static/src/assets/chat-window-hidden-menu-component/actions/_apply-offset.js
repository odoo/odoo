/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindowHiddenMenuComponent/_applyOffset
        [Action/params]
            record
        [Action/behavior]
            :offsetFrom
                {if}
                    {Locale/textDirection}
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
            :offset
                {ChatWindowManager/visual}
                .{Visual/hidden}
                .{Hidden/offset}
            {Record/update}
                [0]
                    @record
                    .{ChatWindowHiddenMenuComponent/root}
                    .{web.Element/style}
                [1]
                    {entry}
                        [key]
                            web.scss/
                            .{+}
                                @offset
                        [value]
                            @offset
                            .{+}
                                px
                    {entry}
                        [key]
                            web.scss/
                            .{+}
                                @oppositeFrom
                        [value]
                            auto
`;
