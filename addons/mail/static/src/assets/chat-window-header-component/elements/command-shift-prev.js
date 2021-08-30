/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commandShiftPrev
        [Element/model]
            ChatWindowHeaderComponent
        [Record/models]
            ChatWindowHeaderComponent/command
        [Element/isPresent]
            @record
            .{ChatWindowHeaderComponent/chatWindow}
            .{ChatWindow/hasShiftPrev}
        [web.Element/onClick]
            {web.Event/stopPropagation}
                @ev
            {ChatWindow/shiftPrev}
                @record
                .{ChatWindowHeaderComponent/chatWindow}
        [web.Element/title]
            {if}
                {Locale/textDirection}
                .{=}
                    rtl
            .{then}
                {Locale/text}
                    Shift right
            .{else}
                {Locale/text}
                    Shift left
`;
