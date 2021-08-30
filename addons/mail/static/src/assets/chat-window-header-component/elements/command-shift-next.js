/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commandShiftNext
        [Element/model]
            ChatWindowHeaderComponent
        [Record/models]
            ChatWindowHeaderComponent/command
        [Element/isPresent]
            @record
            .{ChatWindowHeaderComponent/chatWindow}
            .{ChatWindow/hasShiftNext}
        [Element/onClick]
            {Event/markHandled}
                @ev
                ChatWindowHeaderComponent.ClickShiftNext
            {ChatWindow/shiftNext}
                @record
                .{ChatWindowHeaderComponent/chatWindow}
        [web.Element/title]
            {if}
                {Locale/textDirection}
                .{=}
                    rtl
            .{then}
                {Locale/text}
                    Shift left
            .{else}
                {Locale/text}
                    Shift right
`;
